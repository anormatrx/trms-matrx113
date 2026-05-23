import sys
sys.path.insert(0, "D:\\DevCenter\\Database")
from coordinator import init_db, assign_task, agent_status, agent_stats, list_tasks
from task_manager import add_person, add_task, list_tasks as list_person_tasks

init_db()
print("\n=== Agent Status ===")
for a in agent_status():
    icon = {"idle": "GREEN", "busy": "YELLOW", "error": "RED"}
    print(f'  {icon.get(a["status"],"WHITE")} {a["name"]} ({a["role"]}) - {a["status"]}')
    print(f'    {a["specialty"]}')

print("\n=== Assignment Tests ===")
tests = [
    "صمم واجهة متجر الكتروني",
    "ابني API للمشروع",
    "راجع مشروعي",
    "حسّن هالبرومت",
    "شلون أسوي سيرفر Flask"
]
for req in tests:
    agent, ttype = assign_task(req)
    print(f'  "{req}" --> {agent} ({ttype})')

print("\n=== Stats ===")
for s in agent_stats():
    print(f'  {s["name"]}: total={s["total"]}, done={s["done"]}, pending={s["pending"]}')

print("\nDONE")
