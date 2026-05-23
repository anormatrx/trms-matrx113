import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            specialty TEXT DEFAULT '',
            status TEXT DEFAULT 'idle' CHECK(status IN ('idle','busy','error')),
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL,
            request TEXT NOT NULL,
            task_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','in_progress','done','cancelled','failed')),
            priority TEXT DEFAULT 'medium' CHECK(priority IN ('low','medium','high','urgent')),
            result TEXT DEFAULT '',
            error TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            completed_at TEXT,
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()

    # Register default agents
    default_agents = [
        ("Design Agent", "design", "تصميم واجهات UI/UX - HTML, CSS, JS, أنماط, مكتبات CDN"),
        ("Build Agent", "build", "بناء مشاريع، تشغيل سيرفرات، تثبيت مكتبات، حل مشاكل"),
        ("Consulting Agent", "consulting", "استشارات، تحليل أكواد، مراجعة أمان وأداء"),
        ("Prompt Engineer", "prompt", "هندسة برومتات، تحسين صيغ، System prompts")
    ]
    for name, role, specialty in default_agents:
        conn.execute(
            "INSERT OR IGNORE INTO agents (name, role, specialty) VALUES (?,?,?)",
            (name, role, specialty)
        )
    conn.commit()
    conn.close()

# ================= Intent Classification =================

INTENT_PATTERNS = {
    "design": [
        "صمم", "تصميم", "واجهة", "قالب", "html", "css", "js",
        "جمّل", "حسّن الواجهة", "figma", "ui", "ux", "templates",
        "glassmorphism", "neon", "minimal"
    ],
    "build": [
        "ابني", "بناء", "شغل", "سيرفر", "نصب", "انشاء",
        "run", "server", "install", "deploy", "flask", "fastapi",
        "api", "backend", "database"
    ],
    "consulting": [
        "راجع", "استشر", "حلل", "هل في أخطاء", "رأيك", "مراجعة",
        "review", "analyze", "check", "audit", "quality",
        "اقتراح", "نصيحة", "شلون"
    ],
    "prompt": [
        "برومت", "prompt", "system prompt", "صيغة", "هندسة",
        "حسّن هال", "اكتب برومت", "optimize prompt",
        "chain of thought", "few-shot", "role"
    ]
}

def classify(text):
    text = text.lower()
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        scores[intent] = sum(1 for p in patterns if p.lower() in text)
    if max(scores.values()) == 0:
        return "consulting"
    return max(scores, key=scores.get)

def classify_all(text):
    """رجع كل التصنيفات مع نسب الثقة"""
    text = text.lower()
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        scores[intent] = sum(1 for p in patterns if p.lower() in text)
    return scores

# ================= Task Assignment =================

def assign_task(text, priority="medium"):
    conn = get_conn()
    scores = classify_all(text)
    top_score = max(scores.values())
    # إذا المهمة فيها أكثر من تصنيف بنفس القوة → شطر المهمة
    multiple_intents = [k for k, v in scores.items() if v > 0 and v >= top_score * 0.6]
    assignments = []

    if len(multiple_intents) > 1:
        # شطر المهمة على أكثر من وكيل
        intent_labels = {
            "design": "تصميم",
            "build": "بناء وتشغيل",
            "consulting": "استشارة وتحليل",
            "prompt": "هندسة برومت"
        }
        for intent in multiple_intents:
            agent = conn.execute(
                "SELECT id, name FROM agents WHERE role=? LIMIT 1",
                (intent,)
            ).fetchone()
            if agent:
                label = intent_labels.get(intent, intent)
                sub_task = f"[{label}] {text}"
                conn.execute(
                    """INSERT INTO tasks (agent_id, request, task_type, status, priority)
                       VALUES (?,?,?,'pending',?)""",
                    (agent["id"], sub_task, intent, priority)
                )
                conn.execute("UPDATE agents SET status='busy' WHERE id=?", (agent["id"],))
                assignments.append((agent["name"], intent))
    else:
        # مهمة واحدة لوكيل واحد
        task_type = max(scores, key=scores.get)
        agent = conn.execute(
            "SELECT id, name FROM agents WHERE role=? LIMIT 1",
            (task_type,)
        ).fetchone()
        if not agent:
            agent = conn.execute(
                "SELECT id, name FROM agents WHERE role='consulting' LIMIT 1"
            ).fetchone()
        conn.execute(
            """INSERT INTO tasks (agent_id, request, task_type, status, priority)
               VALUES (?,?,?,'pending',?)""",
            (agent["id"], text, task_type, priority)
        )
        conn.execute("UPDATE agents SET status='busy' WHERE id=?", (agent["id"],))
        assignments.append((agent["name"], task_type))

    conn.commit()
    conn.close()
    return assignments

def complete_task(task_id, result=""):
    conn = get_conn()
    task = conn.execute("SELECT agent_id FROM tasks WHERE id=?", (task_id,)).fetchone()
    if task:
        conn.execute(
            "UPDATE tasks SET status='done', result=?, completed_at=datetime('now','localtime') WHERE id=?",
            (result, task_id)
        )
        remaining = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE agent_id=? AND status='pending'",
            (task["agent_id"],)
        ).fetchone()[0]
        if remaining == 0:
            conn.execute("UPDATE agents SET status='idle' WHERE id=?", (task["agent_id"],))
    conn.commit()
    conn.close()

def fail_task(task_id, error=""):
    conn = get_conn()
    task = conn.execute("SELECT agent_id FROM tasks WHERE id=?", (task_id,)).fetchone()
    if task:
        conn.execute(
            "UPDATE tasks SET status='failed', error=? WHERE id=?",
            (error, task_id)
        )
        conn.execute("UPDATE agents SET status='error' WHERE id=?", (task["agent_id"],))
    conn.commit()
    conn.close()

# ================= Queries =================

def list_tasks(status="", agent=""):
    conn = get_conn()
    query = """SELECT t.id, a.name as agent, a.role, t.request, t.task_type, t.status, t.priority, t.created_at, t.result
               FROM tasks t JOIN agents a ON t.agent_id = a.id"""
    filters = []
    params = []
    if status:
        filters.append("t.status=?")
        params.append(status)
    if agent:
        filters.append("a.name=?")
        params.append(agent)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY t.priority DESC, t.created_at DESC LIMIT 20"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def agent_status():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM agents ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def agent_stats():
    conn = get_conn()
    stats = conn.execute(
        """SELECT a.name, a.role, a.status,
                  COUNT(t.id) as total,
                  SUM(CASE WHEN t.status='done' THEN 1 ELSE 0 END) as done,
                  SUM(CASE WHEN t.status='pending' THEN 1 ELSE 0 END) as pending,
                  SUM(CASE WHEN t.status='in_progress' THEN 1 ELSE 0 END) as in_progress
           FROM agents a LEFT JOIN tasks t ON a.id = t.agent_id
           GROUP BY a.id ORDER BY a.name"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in stats]

# ================= CLI =================

if __name__ == "__main__":
    init_db()
    print("🎯 Coordinator CLI — الموزع الذكي")
    print("الأمر: [نص الطلب] — يوزع المهمة على الوكيل المناسب")
    print("الأمر: status — حالة الوكلاء")
    print("الأمر: stats — إحصائيات")
    print("الأمر: tasks [agent] — عرض المهام")
    while True:
        cmd = input("\n> ").strip()
        if not cmd:
            continue
        parts = cmd.lower().split()
        if parts[0] in ("status", "حالة"):
            for a in agent_status():
                icon = {"idle": "🟢", "busy": "🟡", "error": "🔴"}
                print(f"  {icon.get(a['status'],'⚪')} {a['name']} ({a['role']}) — {a['status']}")
                print(f"     {a['specialty']}")
        elif parts[0] in ("stats", "احصائيات"):
            for s in agent_stats():
                print(f"  📋 {s['name']}: {s['done']}✅ {s['pending']}⏳ {s['in_progress']}🔄")
        elif parts[0] in ("tasks", "المهام"):
            agent_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            tasks = list_tasks(agent=agent_name)
            if not tasks:
                print("⚠️ لا يوجد مهام")
            else:
                for t in tasks:
                    status_icon = {"pending":"⏳","in_progress":"🔄","done":"✅","cancelled":"❌","failed":"💥"}
                    print(f"  [{t['id']}] {status_icon.get(t['status'],'')} {t['request'][:50]}... → {t['agent']} ({t['task_type']})")
        elif parts[0] in ("exit", "خروج"):
            break
        else:
            agent_name, task_type = assign_task(cmd)
            print(f"→ {agent_name} ({task_type})")
            print(f"  المهمة رقم {list_tasks()[0]['id'] if list_tasks() else '?'}")
