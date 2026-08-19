"""Универсальный DTO фактов отчёта ВПР (без subject/protocol-specific значений)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from apps.vpr.facts.task_classification import TaskClassificationResult


@dataclass(slots=True)
class GroupFact:
    count: int
    percent: float
    group_type: str = "EXCLUSIVE"  # EXCLUSIVE | OVERLAPPING
    classification_origin: str = "SYSTEM_ANALYTICS"
    evidence_status: str = "INFORMATIVE"
    allow_management_conclusion: bool = True
    sample_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MarksFact:
    vpr: dict[str, int] = field(default_factory=dict)
    journal: dict[str, int] = field(default_factory=dict)
    vpr_percents: dict[str, float] = field(default_factory=dict)
    journal_percents: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ComparisonFact:
    equal: int = 0
    vpr_lower_than_journal: int = 0
    vpr_higher_than_journal: int = 0
    gap_ge_2: int = 0
    compared: int = 0
    equal_percent: float | None = None
    lower_percent: float | None = None
    higher_percent: float | None = None
    status: str = "INFORMATIVE"  # INFORMATIVE | NOT_AVAILABLE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScoresFact:
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    stdev: float | None = None
    cv: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TaskSummaryFact:
    total: int = 0
    below_50: int = 0
    below_40: int = 0
    critical: int = 0
    problem: int = 0
    informative: int = 0
    not_available: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DeficitSummaryFact:
    established: int = 0
    difficulty: int = 0
    insufficient: int = 0
    topics_at_risk: int = 0
    skills_at_risk: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProfileFact:
    code: str = ""
    label: str = ""
    classification_origin: str = "SYSTEM_ANALYTICS"
    evidence_status: str = "INFORMATIVE"
    methodology_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlannedSummaryFact:
    total: int = 0
    not_achieved: int = 0
    partial: int = 0
    achieved: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VPRReportFacts:
    """
    Единый источник показателей для всех разделов HTML/DOCX.

    Не содержит protocol/subject/school-specific hardcoded значений.
    """

    participants: int = 0
    groups: dict[str, GroupFact] = field(default_factory=dict)
    marks: MarksFact = field(default_factory=MarksFact)
    comparison: ComparisonFact = field(default_factory=ComparisonFact)
    scores: ScoresFact = field(default_factory=ScoresFact)
    tasks: TaskSummaryFact = field(default_factory=TaskSummaryFact)
    task_results: list[TaskClassificationResult] = field(default_factory=list)
    planned_results: PlannedSummaryFact = field(default_factory=PlannedSummaryFact)
    deficits: DeficitSummaryFact = field(default_factory=DeficitSummaryFact)
    profile: ProfileFact = field(default_factory=ProfileFact)
    methodology: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendations: dict[str, Any] = field(default_factory=dict)

    def exclusive_group_sum(self) -> int:
        # stable — алиас medium; не суммировать дважды
        return sum(self.group(k).count for k in ("high", "medium", "risk"))

    def group(self, key: str) -> GroupFact:
        aliases = {"stable": "medium", "medium": "medium"}
        resolved = aliases.get(key, key)
        return self.groups.get(resolved) or GroupFact(count=0, percent=0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "participants": self.participants,
            "groups": {k: v.to_dict() for k, v in self.groups.items()},
            "marks": self.marks.to_dict(),
            "comparison": self.comparison.to_dict(),
            "scores": self.scores.to_dict(),
            "tasks": self.tasks.to_dict(),
            "task_results": [t.to_dict() for t in self.task_results],
            "planned_results": self.planned_results.to_dict(),
            "deficits": self.deficits.to_dict(),
            "profile": self.profile.to_dict(),
            "methodology": dict(self.methodology),
            "evidence": dict(self.evidence),
            "recommendations": dict(self.recommendations),
        }
