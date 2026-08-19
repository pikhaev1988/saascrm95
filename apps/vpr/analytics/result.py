"""Структуры результата аналитики ВПР."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class VprSummaryMetrics:
    participants_count: int
    max_primary_score: int
    avg_primary_score: float | None
    min_primary_score: float | None
    max_primary_result: float | None
    avg_mark_vpr: float | None
    avg_mark_journal: float | None
    knowledge_quality_percent: float | None  # качество знаний (4–5)
    absolute_achievement_percent: float | None  # абсолютная успеваемость (3–5)
    median_primary_score: float | None
    mode_primary_score: float | None
    stdev_primary_score: float | None
    cv_primary_score_percent: float | None
    sou_percent: float | None = None  # СОУ (степень обученности)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprMarksDistribution:
    """Распределение отметок ВПР и журнала."""

    vpr: dict[str, int] = field(default_factory=dict)
    journal: dict[str, int] = field(default_factory=dict)
    vpr_percents: dict[str, float] = field(default_factory=dict)
    journal_percents: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprScoresDistribution:
    """Распределение первичных баллов."""

    counts: dict[str, int] = field(default_factory=dict)
    percents: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprTaskAnalytics:
    task_code: str
    task_number: str
    position: int
    max_score: int
    avg_score: float | None
    completion_percent: float | None
    full_count: int
    partial_count: int
    zero_count: int
    answers_count: int
    # Явные счётчики для отчётов: правильно = полный балл, неправильно = 0 баллов
    correct_count: int = 0
    incorrect_count: int = 0
    # из справочника (если найдено)
    topic: str = ""
    program_section: str = ""
    checked_skill: str = ""
    difficulty: str = ""
    catalog_matched: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprTopicAnalytics:
    topic: str
    tasks_count: int
    avg_completion_percent: float | None
    avg_score: float | None
    errors_count: int
    task_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprSkillAnalytics:
    checked_skill: str
    tasks_count: int
    avg_completion_percent: float | None
    avg_score: float | None
    task_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprStudentAnalytics:
    participant_code: str
    full_name: str
    class_group: str
    gender: str
    primary_score: float | None
    mark_vpr: int | None
    mark_journal: int | None
    completion_percent: float | None
    avg_task_score: float | None
    place_overall: int | None
    place_in_class: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprAnalyticsResult:
    """Единый объект аналитики протокола ВПР."""

    protocol_id: int
    subject: str
    parallel: int
    academic_year: int
    organization_name: str
    summary: VprSummaryMetrics
    marks: VprMarksDistribution
    scores: VprScoresDistribution
    tasks: list[VprTaskAnalytics]
    topics: list[VprTopicAnalytics]
    skills: list[VprSkillAnalytics]
    students: list[VprStudentAnalytics]

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "subject": self.subject,
            "parallel": self.parallel,
            "academic_year": self.academic_year,
            "organization_name": self.organization_name,
            "summary": self.summary.to_dict(),
            "marks": self.marks.to_dict(),
            "scores": self.scores.to_dict(),
            "tasks": [item.to_dict() for item in self.tasks],
            "topics": [item.to_dict() for item in self.topics],
            "skills": [item.to_dict() for item in self.skills],
            "students": [item.to_dict() for item in self.students],
        }
