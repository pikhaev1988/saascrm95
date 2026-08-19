"""Схемы аналитического профиля школы по ВПР."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class SchoolOverview:
    protocols_count: int = 0
    subjects_count: int = 0
    grades_count: int = 0
    participants_total: int = 0
    avg_completion_percent: float | None = None
    avg_quality_percent: float | None = None
    avg_absolute_percent: float | None = None
    avg_deficits_count: float | None = None
    organization_name: str = ""
    academic_year: int | None = None
    has_data: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SubjectSchoolRow:
    subject: str
    protocols_count: int
    participants: int
    avg_completion_percent: float | None
    quality_percent: float | None
    absolute_percent: float | None
    deficits_count: int
    risk_level: str
    rank: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GradeSchoolRow:
    parallel: int
    protocols_count: int
    participants: int
    avg_completion_percent: float | None
    quality_percent: float | None
    risk_level: str
    main_topics: list[str] = field(default_factory=list)
    main_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NamedMetricItem:
    name: str
    value: float | None = None
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StrengthsProfile:
    subjects: list[NamedMetricItem] = field(default_factory=list)
    topics: list[NamedMetricItem] = field(default_factory=list)
    skills: list[NamedMetricItem] = field(default_factory=list)
    grades: list[NamedMetricItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subjects": [i.to_dict() for i in self.subjects],
            "topics": [i.to_dict() for i in self.topics],
            "skills": [i.to_dict() for i in self.skills],
            "grades": [i.to_dict() for i in self.grades],
        }


@dataclass(slots=True)
class WeaknessesProfile:
    subjects: list[NamedMetricItem] = field(default_factory=list)
    topics: list[NamedMetricItem] = field(default_factory=list)
    skills: list[NamedMetricItem] = field(default_factory=list)
    grades: list[NamedMetricItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subjects": [i.to_dict() for i in self.subjects],
            "topics": [i.to_dict() for i in self.topics],
            "skills": [i.to_dict() for i in self.skills],
            "grades": [i.to_dict() for i in self.grades],
        }


@dataclass(slots=True)
class DeficitPriorityBucket:
    priority: str
    count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SchoolDeficitsProfile:
    by_subject: list[dict[str, Any]] = field(default_factory=list)
    by_topic: list[dict[str, Any]] = field(default_factory=list)
    by_skill: list[dict[str, Any]] = field(default_factory=list)
    by_priority: list[DeficitPriorityBucket] = field(default_factory=list)
    total_critical: int = 0
    total_high: int = 0
    total_medium: int = 0
    total_low: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "by_subject": list(self.by_subject),
            "by_topic": list(self.by_topic),
            "by_skill": list(self.by_skill),
            "by_priority": [i.to_dict() for i in self.by_priority],
            "total_critical": self.total_critical,
            "total_high": self.total_high,
            "total_medium": self.total_medium,
            "total_low": self.total_low,
        }


@dataclass(slots=True)
class SchoolRiskProfile:
    classification: str
    reasons: list[str] = field(default_factory=list)
    risk_group_percent: float | None = None
    quality_percent: float | None = None
    deficits_total: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SchoolRecommendationGroup:
    key: str
    title: str
    actions: list[str] = field(default_factory=list)
    risk_level: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SchoolRecommendationsProfile:
    by_subject: list[SchoolRecommendationGroup] = field(default_factory=list)
    by_topic: list[SchoolRecommendationGroup] = field(default_factory=list)
    by_risk: list[SchoolRecommendationGroup] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "by_subject": [i.to_dict() for i in self.by_subject],
            "by_topic": [i.to_dict() for i in self.by_topic],
            "by_risk": [i.to_dict() for i in self.by_risk],
            "actions": list(self.actions),
        }


@dataclass(slots=True)
class YearDynamicsPoint:
    academic_year: int
    avg_completion_percent: float | None
    quality_percent: float | None
    participants: int
    protocols_count: int
    trend: str = ""  # up / down / stable / baseline

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SchoolDynamicsProfile:
    available: bool = False
    message: str = ""
    points: list[YearDynamicsPoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "message": self.message,
            "points": [p.to_dict() for p in self.points],
        }


@dataclass(slots=True)
class SchoolAnalysisResult:
    """Единый аналитический профиль ОО по ВПР."""

    overview: SchoolOverview
    subjects: list[SubjectSchoolRow] = field(default_factory=list)
    grades: list[GradeSchoolRow] = field(default_factory=list)
    strengths: StrengthsProfile = field(default_factory=StrengthsProfile)
    weaknesses: WeaknessesProfile = field(default_factory=WeaknessesProfile)
    deficits: SchoolDeficitsProfile = field(default_factory=SchoolDeficitsProfile)
    risk_profile: SchoolRiskProfile = field(
        default_factory=lambda: SchoolRiskProfile(classification="STABLE")
    )
    recommendations: SchoolRecommendationsProfile = field(
        default_factory=SchoolRecommendationsProfile
    )
    dynamics: SchoolDynamicsProfile = field(default_factory=SchoolDynamicsProfile)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overview": self.overview.to_dict(),
            "subjects": [i.to_dict() for i in self.subjects],
            "grades": [i.to_dict() for i in self.grades],
            "strengths": self.strengths.to_dict(),
            "weaknesses": self.weaknesses.to_dict(),
            "deficits": self.deficits.to_dict(),
            "risk_profile": self.risk_profile.to_dict(),
            "recommendations": self.recommendations.to_dict(),
            "dynamics": self.dynamics.to_dict(),
        }
