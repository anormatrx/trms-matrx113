from typing import List, Tuple, Optional
from core.entities.task import Task, TaskType, TaskStatus
from core.entities.agent import Agent, AgentRole
from core.ports.repository import TaskRepository, AgentRepository


INTENT_PATTERNS = {
    TaskType.DESIGN: [
        "صمم", "تصميم", "واجهة", "قالب", "html", "css",
        "جمّل", "ui", "ux", "templates", "glassmorphism", "neon"
    ],
    TaskType.BUILD: [
        "ابني", "بناء", "شغل", "سيرفر", "نصب", "run",
        "server", "install", "flask", "fastapi", "api", "backend"
    ],
    TaskType.CONSULTING: [
        "راجع", "استشر", "حلل", "أخطاء", "رأيك", "review",
        "analyze", "check", "audit", "نصيحة", "شلون"
    ],
    TaskType.PROMPT: [
        "برومت", "prompt", "system", "صيغة", "هندسة",
        "حسّن", "اكتب برومت", "few-shot", "chain of thought"
    ],
}


class Coordinator:
    def __init__(self, task_repo: TaskRepository, agent_repo: AgentRepository):
        self.task_repo = task_repo
        self.agent_repo = agent_repo
        self._stats = {"total_routed": 0, "mixed_splits": 0}

    def classify(self, text: str) -> List[Tuple[TaskType, float]]:
        text_lower = text.lower()
        scores = []
        for task_type, patterns in INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if p.lower() in text_lower)
            if score > 0:
                scores.append((task_type, score))
        if not scores:
            scores.append((TaskType.CONSULTING, 1))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def route(self, text: str, priority: str = "medium") -> List[Tuple[Agent, Task]]:
        scores = self.classify(text)
        # إذا أكثر من تصنيف له نفس القوة تقريباً → شطر المهمة
        positive_scores = [s for _, s in scores]
        if len(positive_scores) >= 2 and positive_scores[0] - positive_scores[-1] <= 1:
            selected_types = [t for t, _ in scores]
        else:
            selected_types = [scores[0][0]]
        assignments = []

        for task_type in selected_types:
            from core.entities.agent import AgentRole
            agent = self.agent_repo.agent_get_by_role(AgentRole(task_type.value))
            if not agent:
                continue

            from core.entities.task import TaskPriority
            task = Task(
                title=text[:100],
                description=text,
                task_type=task_type,
                priority=TaskPriority(priority),
                agent_id=agent.id,
            )
            task_id = self.task_repo.save(task)
            task.id = task_id
            agent.assign()
            self.agent_repo.agent_update(agent)
            assignments.append((agent, task))

        self._stats["total_routed"] += len(assignments)
        if len(assignments) > 1:
            self._stats["mixed_splits"] += 1

        return assignments

    def complete_task(self, task_id: int, result: str) -> None:
        task = self.task_repo.get(task_id)
        if not task:
            return
        task.complete(result)
        self.task_repo.update(task)
        agent = self.agent_repo.agent_get(task.agent_id)
        if agent:
            agent.release(success=True)
            self.agent_repo.agent_update(agent)

    def fail_task(self, task_id: int, error: str) -> None:
        task = self.task_repo.get(task_id)
        if not task:
            return
        task.fail(error)
        self.task_repo.update(task)
        agent = self.agent_repo.agent_get(task.agent_id)
        if agent:
            agent.release(success=False)
            self.agent_repo.agent_update(agent)

    def get_stats(self) -> dict:
        task_counts = self.task_repo.count_by_status()
        agent_stats = self.agent_repo.agent_stats()
        return {
            "coordinator": self._stats,
            "tasks": task_counts,
            "agents": agent_stats,
        }
