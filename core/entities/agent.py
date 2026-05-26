from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


class AgentRole(str, Enum):
    DESIGN = "design"
    BUILD = "build"
    CONSULTING = "consulting"
    PROMPT = "prompt"


@dataclass
class Agent:
    id: Optional[int] = None
    name: str = ""
    role: AgentRole = AgentRole.CONSULTING
    specialty: str = ""
    status: AgentStatus = AgentStatus.IDLE
    error_count: int = 0
    total_tasks: int = 0
    successful_tasks: int = 0

    def assign(self) -> None:
        self.status = AgentStatus.BUSY
        self.total_tasks += 1

    def release(self, success: bool = True) -> None:
        self.status = AgentStatus.IDLE
        if success:
            self.successful_tasks += 1
        else:
            self.error_count += 1

    def mark_error(self) -> None:
        self.status = AgentStatus.ERROR
        self.error_count += 1

    def reset(self) -> None:
        self.status = AgentStatus.IDLE

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 1.0
        return self.successful_tasks / self.total_tasks
