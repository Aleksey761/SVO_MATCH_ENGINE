from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AuditLevel(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class AuditResult:
    name: str
    level: AuditLevel
    passed: bool
    count: int
    message: str
    details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "level": self.level.value,
            "passed": self.passed,
            "count": self.count,
            "message": self.message,
            "details": list(self.details),
        }
