"""Схемы комплексного аналитического профиля ВПР."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class VprAchievementProfile:
    participants: int
    mean_score: float | None
    median: float | None
    max_score: int
    stdev: float | None
    cv_percent: float | None
    distribution: dict[str, int] = field(default_factory=dict)
    quality_percent: float | None = None
    absolute_percent: float | None = None
    heterogeneity: str = ""  # low / medium / high

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprTaskProfileItem:
    task: str
    topic: str
    skill: str
    section: str
    success: float | None
    difficulty: str
    status: str  # HIGH / NORMAL / RISK / CRITICAL
    catalog_matched: bool = False
    correct_count: int = 0
    incorrect_count: int = 0
    partial_count: int = 0
    answers_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprTaskAnalysisProfile:
    items: list[VprTaskProfileItem] = field(default_factory=list)
    catalog_coverage: str = "none"  # full / partial / none
    critical_count: int = 0
    risk_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "catalog_coverage": self.catalog_coverage,
            "critical_count": self.critical_count,
            "risk_count": self.risk_count,
        }


@dataclass(slots=True)
class VprTopicProfileItem:
    topic: str
    tasks: list[str] = field(default_factory=list)
    average: float | None = None
    deficit_type: str = "none"  # none / local / mass
    low_tasks_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprTopicAnalysisProfile:
    items: list[VprTopicProfileItem] = field(default_factory=list)
    mass_deficits: list[str] = field(default_factory=list)
    local_deficits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "mass_deficits": list(self.mass_deficits),
            "local_deficits": list(self.local_deficits),
        }


@dataclass(slots=True)
class VprSkillProfileItem:
    skill: str
    level: str  # high / medium / low
    tasks: list[str] = field(default_factory=list)
    average: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprSkillAnalysisProfile:
    items: list[VprSkillProfileItem] = field(default_factory=list)
    formed: list[str] = field(default_factory=list)
    underformed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "formed": list(self.formed),
            "underformed": list(self.underformed),
        }


@dataclass(slots=True)
class VprGroupBucket:
    count: int
    percent: float
    participant_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprParticipantGroupsProfile:
    groups: dict[str, VprGroupBucket] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"groups": {key: value.to_dict() for key, value in self.groups.items()}}


@dataclass(slots=True)
class VprObjectivityProfile:
    journal_comparison: dict[str, int] = field(default_factory=dict)
    journal_comparison_percents: dict[str, float] = field(default_factory=dict)
    compared_count: int = 0
    risk_level: str = "low"  # low / medium / high

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprSchoolProfile:
    classification: str
    reasons: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprRecommendationItem:
    topic: str
    skill: str
    deficit: str
    cause: str
    actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprRecommendationsProfile:
    items: list[VprRecommendationItem] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "actions": list(self.actions),
        }


@dataclass(slots=True)
class VprProtocolBrief:
    protocol_id: int
    subject: str
    parallel: int
    academic_year: int
    organization_name: str
    participants_count: int
    max_primary_score: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprComprehensiveAnalysisResult:
    """Единый экспертный аналитический профиль протокола ВПР."""

    protocol: VprProtocolBrief
    achievement: VprAchievementProfile
    task_analysis: VprTaskAnalysisProfile
    topic_analysis: VprTopicAnalysisProfile
    skill_analysis: VprSkillAnalysisProfile
    participant_groups: VprParticipantGroupsProfile
    objectivity: VprObjectivityProfile
    school_profile: VprSchoolProfile
    # Типизированные объекты движков (для UI / сериализации)
    deficits: Any = None
    causes: Any = None
    recommendations: VprRecommendationsProfile = field(default_factory=VprRecommendationsProfile)
    conclusion: Any = None
    analytics: Any = None

    # --- алиасы для шаблонов (analysis.tasks / topics / skills) ---

    @property
    def tasks(self) -> VprTaskAnalysisProfile:
        return self.task_analysis

    @property
    def topics(self) -> VprTopicAnalysisProfile:
        return self.topic_analysis

    @property
    def skills(self) -> VprSkillAnalysisProfile:
        return self.skill_analysis

    # --- срезы экрана «Обзор» ---

    @property
    def summary(self):
        return self.analytics.summary if self.analytics is not None else None

    @property
    def subject(self) -> str:
        if self.analytics is not None:
            return self.analytics.subject
        return self.protocol.subject

    @property
    def parallel(self) -> int:
        if self.analytics is not None:
            return self.analytics.parallel
        return self.protocol.parallel

    @property
    def academic_year(self) -> int:
        if self.analytics is not None:
            return self.analytics.academic_year
        return self.protocol.academic_year

    @property
    def organization_name(self) -> str:
        if self.analytics is not None:
            return self.analytics.organization_name
        return self.protocol.organization_name

    @property
    def marks_rows(self) -> list[dict[str, Any]]:
        from apps.vpr.comprehensive_analysis.presentation import build_marks_rows

        return build_marks_rows(self)

    @property
    def scores_rows(self) -> list[dict[str, Any]]:
        from apps.vpr.comprehensive_analysis.presentation import build_scores_rows

        return build_scores_rows(self)

    @property
    def task_rows(self) -> list[dict[str, Any]]:
        from apps.vpr.comprehensive_analysis.presentation import build_task_rows

        return build_task_rows(self)

    @property
    def topic_rows(self) -> list:
        if self.deficits is None:
            return []
        return list(getattr(self.deficits, "topics", []) or [])

    @property
    def skill_rows(self) -> list:
        if self.deficits is None:
            return []
        return list(getattr(self.deficits, "skills", []) or [])

    @property
    def student_rows(self) -> list[dict[str, Any]]:
        from apps.vpr.comprehensive_analysis.presentation import build_student_rows

        return build_student_rows(self)

    @property
    def priority_summary(self) -> list[dict[str, Any]]:
        from apps.vpr.comprehensive_analysis.presentation import build_priority_summary

        return build_priority_summary(self)

    @property
    def deficit_summary(self):
        if self.deficits is None:
            return None
        return getattr(self.deficits, "summary", None)

    @property
    def conclusion_sections(self) -> list:
        if self.conclusion is None:
            return []
        return list(getattr(self.conclusion, "sections", []) or [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol.to_dict(),
            "achievement": self.achievement.to_dict(),
            "task_analysis": self.task_analysis.to_dict(),
            "topic_analysis": self.topic_analysis.to_dict(),
            "skill_analysis": self.skill_analysis.to_dict(),
            "participant_groups": self.participant_groups.to_dict(),
            "objectivity": self.objectivity.to_dict(),
            "school_profile": self.school_profile.to_dict(),
            "deficits": self.deficits.to_dict() if hasattr(self.deficits, "to_dict") else dict(self.deficits or {}),
            "causes": self.causes.to_dict() if hasattr(self.causes, "to_dict") else dict(self.causes or {}),
            "recommendations": self.recommendations.to_dict(),
            "conclusion": (
                self.conclusion.to_dict()
                if hasattr(self.conclusion, "to_dict")
                else dict(self.conclusion or {})
            ),
        }
