"""
DevCenter v2.0 — Clean Architecture
نظام وكلاء ذكاء اصطناعي بهندسة نظيفة قابلة للتوسع
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.entities.task import TaskType
from core.entities.agent import AgentRole
from core.usecases.coordinator import Coordinator
from infrastructure.persistence.sqlite_repo import SQLiteRepository
from infrastructure.security.vault import SecurityVault
from infrastructure.system.health import get_health, record_metric
from config.loader import ConfigLoader


class DevCenterApp:
    def __init__(self):
        # Load config
        config = ConfigLoader.load_config()
        self.config = config
        self.db_path = config["database"]["path"]

        # Initialize infrastructure
        self.repo = SQLiteRepository(self.db_path)
        self.vault = SecurityVault()
        self.coordinator = Coordinator(self.repo, self.repo)

        # Ensure agents exist
        self._init_agents()

    def _init_agents(self):
        existing = self.repo.agent_list()
        if not existing:
            defaults = [
                ("Design Agent", AgentRole.DESIGN, "تصميم واجهات UI/UX - HTML, CSS, JS, أنماط, مكتبات CDN"),
                ("Build Agent", AgentRole.BUILD, "بناء مشاريع، تشغيل سيرفرات، تثبيت مكتبات، حل مشاكل"),
                ("Consulting Agent", AgentRole.CONSULTING, "استشارات، تحليل أكواد، مراجعة أمان وأداء"),
                ("Prompt Engineer", AgentRole.PROMPT, "هندسة برومتات، تحسين صيغ، System prompts"),
            ]
            from core.entities.agent import Agent
            for name, role, spec in defaults:
                agent = Agent(name=name, role=role, specialty=spec)
                self.repo.agent_save(agent)

    def handle(self, text: str) -> str:
        record_metric("requests", 1)

        # Route task
        assignments = self.coordinator.route(text)

        if not assignments:
            return "⚠️ ما لقيت وكيل مناسب لهالمهمة"

        result_parts = []
        for agent, task in assignments:
            result_parts.append(f"→ {agent.name} (المهمة #{task.id})")

        if len(assignments) > 1:
            result_parts.insert(0, f"شطرت المهمة على {len(assignments)} وكلاء:")

        return "\n".join(result_parts)

    def status(self) -> str:
        agents = self.repo.agent_list()
        lines = ["🤖 حالة الوكلاء:"]
        icons = {"idle": "🟢", "busy": "🟡", "error": "🔴"}
        for a in agents:
            icon = icons.get(a.status.value, "⚪")
            lines.append(f"  {icon} {a.name} ({a.role.value}) — {a.status.value}")
            lines.append(f"     مهام: {a.total_tasks} | نجاح: {a.successful_tasks} | أخطاء: {a.error_count}")
        health = get_health()
        lines.append(f"\n📊 النظام:")
        lines.append(f"  CPU: {health.get('cpu_percent', '?')}% | RAM: {health.get('ram_percent', '?')}%")
        lines.append(f"  الحالة: {health.get('status', 'unknown')}")
        return "\n".join(lines)

    def stats(self) -> str:
        stats = self.coordinator.get_stats()
        lines = ["📊 إحصائيات:"]
        for s in stats.get("agents", []):
            lines.append(f"  {s['name']}: {s['total_tasks']} مهام | {s['done']}✅ | {s['pending']}⏳ | {s['failed']}💥")
        tasks = stats.get("tasks", {})
        lines.append(f"\n📋 إجمالي المهام: {sum(tasks.values())}")
        return "\n".join(lines)

    def run(self):
        print("🤖 DevCenter v2.0 — بنية نظيفة قابلة للتوسع")
        print("الأوامر: status | stats | health | exit")
        while True:
            try:
                cmd = input("\n> ").strip()
                if not cmd:
                    continue
                if cmd.lower() in ("exit", "خروج"):
                    break
                elif cmd.lower() in ("status", "حالة"):
                    print(self.status())
                elif cmd.lower() in ("stats", "احصائيات"):
                    print(self.stats())
                elif cmd.lower() in ("health", "صحة"):
                    h = get_health()
                    for k, v in h.items():
                        print(f"  {k}: {v}")
                else:
                    print(self.handle(cmd))
            except KeyboardInterrupt:
                print("\n👋 إلى اللقاء")
                break
            except Exception as e:
                print(f"❌ خطأ: {e}")


if __name__ == "__main__":
    app = DevCenterApp()
    app.run()
