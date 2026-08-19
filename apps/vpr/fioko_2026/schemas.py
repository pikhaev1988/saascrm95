"""DTO слоя FIOKO 2026."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class FiokoTaskRow:
    task_code: str
    task_number: str
    difficulty: str  # basic|advanced|high|unknown
    difficulty_label: str
    difficulty_status: str  # ok|NOT_AVAILABLE
    completion_percent: float | None
    fioko_level_status: str
    visual_marker: str
    checked_skill: str = ""
    topic: str = ""
    planned_result: str = ""
    catalog_mapping_status: str = "NOT_AVAILABLE"  # COMPLETE|PARTIAL|NOT_AVAILABLE|NOT_MAPPED
    full_score_rate: float | None = None
    partial_score_rate: float | None = None
    zero_score_rate: float | None = None
    max_score: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoIndividualRow:
    participant_code: str
    full_name: str
    primary_score: float | None
    mark_vpr: int | None
    mark_journal: int | None
    task_scores: dict[str, float | None] = field(default_factory=dict)
    basic_completion_percent: float | None = None
    advanced_completion_percent: float | None = None
    high_completion_percent: float | None = None
    basic_status: str = "not_available"
    advanced_status: str = "not_available"
    high_status: str = "not_available"
    difficulty_coverage: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoMarksStats:
    mark_2_percent: float | None = None
    mark_3_percent: float | None = None
    mark_4_percent: float | None = None
    mark_5_percent: float | None = None
    previous_year_mark_2_percent: float | None = None
    mark_2_dynamics_pp: float | None = None
    mark_2_dynamics_status: str = "NOT_AVAILABLE"  # positive|negative|neutral|NOT_AVAILABLE
    mark_2_trend: list[dict[str, Any]] = field(default_factory=list)
    sample_size: int = 0
    source: str = "FIOKO_2026"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoJournalGapRow:
    participant_code: str
    mark_vpr: int
    mark_journal: int
    journal_gap_abs: int
    journal_gap_direction: str  # vpr_lower|vpr_higher|equal
    journal_gap_ge_2: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoJournalAnalysis:
    status: str = "NOT_AVAILABLE"  # OK|NOT_AVAILABLE
    compared_count: int = 0
    gap_ge_2_count: int = 0
    gap_ge_2_percent: float | None = None
    rows: list[FiokoJournalGapRow] = field(default_factory=list)
    wording: str = ""
    sample_size: int = 0
    source: str = "FIOKO_2026"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "compared_count": self.compared_count,
            "gap_ge_2_count": self.gap_ge_2_count,
            "gap_ge_2_percent": self.gap_ge_2_percent,
            "rows": [r.to_dict() for r in self.rows],
            "wording": self.wording,
            "sample_size": self.sample_size,
            "source": self.source,
        }


@dataclass(slots=True)
class FiokoBoundaryPeakFlag:
    boundary: str  # "2->3"|"3->4"|"4->5"
    primary_score: float | None
    observed_count: int
    expected_context: str
    status: str  # flagged|ok|NOT_AVAILABLE|POSSIBLE_MARKER

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoGeneralPeak:
    primary_score: float | None = None
    observed_count: int = 0
    percent: float | None = None
    is_peak: bool = False
    note: str = "Статистическая особенность распределения; не является маркером объективности."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoPrimaryDistribution:
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    stdev: float | None = None
    cv: float | None = None
    histogram: dict[str, int] = field(default_factory=dict)
    general_peak: FiokoGeneralPeak = field(default_factory=FiokoGeneralPeak)
    boundary_peak_flags: list[FiokoBoundaryPeakFlag] = field(default_factory=list)
    boundary_peak_status: str = "NOT_AVAILABLE"  # OK|HAS_MARKER|NOT_AVAILABLE
    possible_objectivity_marker: bool = False
    boundary_source: str = "NOT_AVAILABLE"  # official|NOT_AVAILABLE
    sample_size: int = 0
    sample_quality: str = "limited"
    sample_warning: bool = True
    wording: str = ""
    # CV — SYSTEM_ANALYTICS, не вывод об объективности
    cv_source: str = "SYSTEM_ANALYTICS"
    source: str = "FIOKO_2026"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["general_peak"] = self.general_peak.to_dict()
        d["boundary_peak_flags"] = [f.to_dict() for f in self.boundary_peak_flags]
        return d


@dataclass(slots=True)
class FiokoSkillDeficit:
    skill: str
    linked_tasks: list[str] = field(default_factory=list)
    red_tasks: list[str] = field(default_factory=list)
    yellow_tasks: list[str] = field(default_factory=list)
    green_tasks: list[str] = field(default_factory=list)
    red_share: float | None = None
    system_deficit: bool = False
    status: str = "OK"  # OK|INSUFFICIENT_DATA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoPlannedResultRow:
    planned_result: str
    linked_tasks: list[str] = field(default_factory=list)
    difficulties: list[str] = field(default_factory=list)
    completion_percent: float | None = None
    fioko_achievement_status: str = "not_available"
    visual_marker: str = "none"
    evidence: str = ""
    # SYSTEM mastery status сохраняется отдельно в отчёте
    system_mastery_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoMarkGroupBucket:
    mark: str
    group_size: int
    informational_only: bool
    sample_warning: bool
    sample_status: str = "INFORMATIVE"  # INFORMATIVE | LIMITED_SAMPLE
    informative: bool = True
    task_completion: dict[str, float | None] = field(default_factory=dict)
    weak_tasks: list[str] = field(default_factory=list)
    strong_tasks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoGroupsAnalysis:
    sample_size: int = 0
    sample_warning: bool = False
    informational_only: bool = False
    buckets: list[FiokoMarkGroupBucket] = field(default_factory=list)
    hard_for_all: list[str] = field(default_factory=list)
    easiest: list[str] = field(default_factory=list)
    anomaly_crossings: list[dict[str, Any]] = field(default_factory=list)
    anomaly_wording: str = ""
    source: str = "FIOKO_2026"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_size": self.sample_size,
            "sample_warning": self.sample_warning,
            "informational_only": self.informational_only,
            "buckets": [b.to_dict() for b in self.buckets],
            "hard_for_all": list(self.hard_for_all),
            "easiest": list(self.easiest),
            "anomaly_crossings": list(self.anomaly_crossings),
            "anomaly_wording": self.anomaly_wording,
            "source": self.source,
        }


@dataclass(slots=True)
class FiokoManagementRecommendation:
    problem: str
    evidence: str
    possible_causes: list[str] = field(default_factory=list)
    action: str = ""
    responsible: str = ""
    deadline: str = ""
    control_metric: str = ""
    expected_result: str = ""
    audience: str = ""  # teacher|smo|admin|students|parents
    source: str = "FIOKO_2026"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoCrossYearItem:
    skill_or_topic: str
    kind: str  # skill|topic
    current_completion: float | None
    previous_completion: float | None
    delta_completion_pp: float | None
    comparison_status: str  # OK|NOT_COMPARABLE|NOT_AVAILABLE
    delta_deficit_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoCrossYearAnalysis:
    status: str = "NOT_AVAILABLE"
    previous_protocol_id: int | None = None
    previous_year: int | None = None
    items: list[FiokoCrossYearItem] = field(default_factory=list)
    note: str = ""
    source: str = "FIOKO_2026"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "previous_protocol_id": self.previous_protocol_id,
            "previous_year": self.previous_year,
            "items": [i.to_dict() for i in self.items],
            "note": self.note,
            "source": self.source,
        }


@dataclass(slots=True)
class FiokoCrossSubjectItem:
    subject: str
    parallel: int
    year: int
    skill: str
    topic: str
    completion: float | None
    comparison_status: str = "NOT_COMPARABLE"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FiokoCrossSubjectAnalysis:
    status: str = "NOT_AVAILABLE"
    items: list[FiokoCrossSubjectItem] = field(default_factory=list)
    note: str = "Сравнение предметов без усреднения «среднего результата школы»."
    source: str = "FIOKO_2026"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "items": [i.to_dict() for i in self.items],
            "note": self.note,
            "source": self.source,
        }


@dataclass(slots=True)
class VprFioko2026Layer:
    """Единый FIOKO 2026 слой для любого протокола ВПР."""

    source: str = "FIOKO_2026"
    document: dict[str, Any] = field(default_factory=dict)
    mapping: dict[str, Any] = field(default_factory=dict)
    catalog_mapping_status: str = "NOT_AVAILABLE"
    difficulty_coverage: dict[str, Any] = field(default_factory=dict)
    tasks: list[FiokoTaskRow] = field(default_factory=list)
    individuals: list[FiokoIndividualRow] = field(default_factory=list)
    marks: FiokoMarksStats = field(default_factory=FiokoMarksStats)
    journal: FiokoJournalAnalysis = field(default_factory=FiokoJournalAnalysis)
    distribution: FiokoPrimaryDistribution = field(default_factory=FiokoPrimaryDistribution)
    skill_deficits: list[FiokoSkillDeficit] = field(default_factory=list)
    planned_results: list[FiokoPlannedResultRow] = field(default_factory=list)
    groups: FiokoGroupsAnalysis = field(default_factory=FiokoGroupsAnalysis)
    management_recommendations: list[FiokoManagementRecommendation] = field(default_factory=list)
    cross_year: FiokoCrossYearAnalysis = field(default_factory=FiokoCrossYearAnalysis)
    cross_subject: FiokoCrossSubjectAnalysis = field(default_factory=FiokoCrossSubjectAnalysis)
    methodology_basis: str = ""
    warnings: list[str] = field(default_factory=list)
    system_analytics_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "document": dict(self.document),
            "mapping": dict(self.mapping),
            "catalog_mapping_status": self.catalog_mapping_status,
            "difficulty_coverage": dict(self.difficulty_coverage),
            "tasks": [t.to_dict() for t in self.tasks],
            "individuals": [i.to_dict() for i in self.individuals],
            "marks": self.marks.to_dict(),
            "journal": self.journal.to_dict(),
            "distribution": self.distribution.to_dict(),
            "skill_deficits": [s.to_dict() for s in self.skill_deficits],
            "planned_results": [p.to_dict() for p in self.planned_results],
            "groups": self.groups.to_dict(),
            "management_recommendations": [m.to_dict() for m in self.management_recommendations],
            "cross_year": self.cross_year.to_dict(),
            "cross_subject": self.cross_subject.to_dict(),
            "methodology_basis": self.methodology_basis,
            "warnings": list(self.warnings),
            "system_analytics_notes": list(self.system_analytics_notes),
        }
