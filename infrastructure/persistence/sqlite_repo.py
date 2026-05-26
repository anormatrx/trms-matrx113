import sqlite3
import json
import os
from typing import Optional, List
from core.entities.task import Task, TaskType, TaskStatus, TaskPriority
from core.entities.agent import Agent, AgentRole, AgentStatus


class SQLiteRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_schema(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                specialty TEXT DEFAULT '',
                status TEXT DEFAULT 'idle',
                error_count INTEGER DEFAULT 0,
                total_tasks INTEGER DEFAULT 0,
                successful_tasks INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                task_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                agent_id INTEGER,
                result TEXT DEFAULT '',
                error TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime')),
                completed_at TEXT,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type);
        """)
        conn.commit()

        defaults = [
            ("Design Agent", "design", "تصميم واجهات UI/UX"),
            ("Build Agent", "build", "بناء مشاريع وتشغيل سيرفرات"),
            ("Consulting Agent", "consulting", "استشارات وتحليل ومراجعة"),
            ("Prompt Engineer", "prompt", "هندسة برومتات وتحسين صيغ"),
        ]
        for name, role, spec in defaults:
            conn.execute(
                "INSERT OR IGNORE INTO agents (name, role, specialty) VALUES (?,?,?)",
                (name, role, spec),
            )
        conn.commit()
        conn.close()

    # ================= Tasks =================
    def save(self, task: Task) -> int:
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO tasks (title, description, task_type, status, priority, agent_id, result, error, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (task.title, task.description, task.task_type.value, task.status.value, task.priority.value, task.agent_id, task.result, task.error, task.created_at),
        )
        conn.commit()
        task.id = cur.lastrowid
        conn.close()
        return task.id

    def get(self, task_id: int) -> Optional[Task]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return Task(
            id=row["id"], title=row["title"], description=row["description"],
            task_type=TaskType(row["task_type"]), status=TaskStatus(row["status"]),
            priority=TaskPriority(row["priority"]), agent_id=row["agent_id"],
            result=row["result"], error=row["error"],
            created_at=row["created_at"], completed_at=row["completed_at"],
        )

    def update(self, task: Task) -> bool:
        conn = self._get_conn()
        cur = conn.execute(
            "UPDATE tasks SET status=?, result=?, error=?, completed_at=? WHERE id=?",
            (task.status.value, task.result, task.error, task.completed_at, task.id),
        )
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def delete(self, task_id: int) -> bool:
        conn = self._get_conn()
        cur = conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def list(self, status: Optional[str] = None, agent: Optional[str] = None, limit: int = 50) -> List[Task]:
        conn = self._get_conn()
        query = "SELECT * FROM tasks"
        filters = []
        params = []
        if status:
            filters.append("status=?")
            params.append(status)
        if agent:
            filters.append("agent_id IN (SELECT id FROM agents WHERE name=?)")
            params.append(agent)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY priority DESC, created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [
            Task(
                id=r["id"], title=r["title"], description=r["description"],
                task_type=TaskType(r["task_type"]), status=TaskStatus(r["status"]),
                priority=TaskPriority(r["priority"]), agent_id=r["agent_id"],
                result=r["result"], error=r["error"],
                created_at=r["created_at"], completed_at=r["completed_at"],
            )
            for r in rows
        ]

    def count_by_status(self) -> dict:
        conn = self._get_conn()
        rows = conn.execute("SELECT status, COUNT(*) as c FROM tasks GROUP BY status").fetchall()
        conn.close()
        return {r["status"]: r["c"] for r in rows}

    # ================= Agents =================
    def agent_save(self, agent: Agent) -> int:
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO agents (name, role, specialty, status, error_count, total_tasks, successful_tasks) VALUES (?,?,?,?,?,?,?)",
            (agent.name, agent.role.value, agent.specialty, agent.status.value, agent.error_count, agent.total_tasks, agent.successful_tasks),
        )
        conn.commit()
        agent.id = cur.lastrowid
        conn.close()
        return agent.id

    def agent_get(self, agent_id: int) -> Optional[Agent]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return Agent(
            id=row["id"], name=row["name"], role=AgentRole(row["role"]),
            specialty=row["specialty"], status=AgentStatus(row["status"]),
            error_count=row["error_count"], total_tasks=row["total_tasks"],
            successful_tasks=row["successful_tasks"],
        )

    def agent_get_by_role(self, role: AgentRole) -> Optional[Agent]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM agents WHERE role=? LIMIT 1", (role.value,)).fetchone()
        conn.close()
        if not row:
            return None
        return Agent(
            id=row["id"], name=row["name"], role=AgentRole(row["role"]),
            specialty=row["specialty"], status=AgentStatus(row["status"]),
            error_count=row["error_count"], total_tasks=row["total_tasks"],
            successful_tasks=row["successful_tasks"],
        )

    def agent_list(self) -> List[Agent]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM agents ORDER BY name").fetchall()
        conn.close()
        return [
            Agent(
                id=r["id"], name=r["name"], role=AgentRole(r["role"]),
                specialty=r["specialty"], status=AgentStatus(r["status"]),
                error_count=r["error_count"], total_tasks=r["total_tasks"],
                successful_tasks=r["successful_tasks"],
            )
            for r in rows
        ]

    def agent_update(self, agent: Agent) -> bool:
        conn = self._get_conn()
        cur = conn.execute(
            "UPDATE agents SET status=?, error_count=?, total_tasks=?, successful_tasks=? WHERE id=?",
            (agent.status.value, agent.error_count, agent.total_tasks, agent.successful_tasks, agent.id),
        )
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def agent_stats(self) -> List[dict]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT a.name, a.role, a.status,
                   COUNT(t.id) as total_tasks,
                   SUM(CASE WHEN t.status='done' THEN 1 ELSE 0 END) as done,
                   SUM(CASE WHEN t.status='pending' THEN 1 ELSE 0 END) as pending,
                   SUM(CASE WHEN t.status='failed' THEN 1 ELSE 0 END) as failed
            FROM agents a
            LEFT JOIN tasks t ON a.id = t.agent_id
            GROUP BY a.id
            ORDER BY a.name
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]
