"""Структуры результата выявления образовательных дефицитов ВПР."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class VprTaskDeficit:
    task_code: str
    completion_percent: float | None
    mastery_level: str
    mastery_label: str
    status: str
    priority: str
    topic: str = ""
    program_section: str = ""
    checked_skill: str = ""
    difficulty: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprTopicDeficit:
    topic: str
    avg_completion_percent: float | None
    tasks_count: int
    critical_tasks_count: int
    problem_tasks_count: int
    mastery_level: str
    mastery_label: str
    risk: str
    priority: str
    task_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprSkillDeficit:
    checked_skill: str
    avg_completion_percent: float | None
    tasks_count: int
    critical_tasks_count: int
    problem_tasks_count: int
    mastery_level: str
    mastery_label: str
    risk: str
    priority: str
    task_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprStudentDeficit:
    participant_code: str
    full_name: str
    class_group: str
    completion_percent: float | None
    mastery_level: str
    mastery_label: str
    priority: str
    unfinished_tasks_count: int
    critical_tasks_count: int
    problem_tasks_count: int
    problem_topics: list[str] = field(default_factory=list)
    problem_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprDeficitSummary:
    tasks_total: int
    tasks_critical: int
    tasks_problem: int
    topics_at_risk: int
    skills_at_risk: int
    students_at_risk: int
    critical_priority_count: int
    high_priority_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprDeficitResult:
    protocol_id: int
    tasks: list[VprTaskDeficit]
    topics: list[VprTopicDeficit]
    skills: list[VprSkillDeficit]
    students: list[VprStudentDeficit]
    summary: VprDeficitSummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "tasks": [item.to_dict() for item in self.tasks],
            "topics": [item.to_dict() for item in self.topics],
            "skills": [item.to_dict() for item in self.skills],
            "students": [item.to_dict() for item in self.students],
            "summary": self.summary.to_dict(),
        }
