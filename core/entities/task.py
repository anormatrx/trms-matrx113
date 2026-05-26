from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(str, Enum):
    DESIGN = "design"
    BUILD = "build"
    CONSULTING = "consulting"
    PROMPT = "prompt"


@dataclass
class Task:
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    task_type: TaskType = TaskType.CONSULTING
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    agent_id: Optional[int] = None
    result: str = ""
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    def complete(self, result: str) -> None:
        self.status = TaskStatus.DONE
        self.result = result
        self.completed_at = datetime.now().isoformat()

    def fail(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now().isoformat()

    def start(self) -> None:
        self.status = TaskStatus.IN_PROGRESS

    def is_overdue(self, hours: int = 24) -> bool:
        if not self.created_at:
            return False
        created = datetime.fromisoformat(self.created_at)
        return (datetime.now() - created).total_seconds() > hours * 3600
