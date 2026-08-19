"""
Разделение EDUCATIONAL_DIFFICULTY / EDUCATIONAL_DEFICIT / CAUSE / RECOMMENDATION.

Низкий completion_percent сам по себе НЕ доказывает причину и не всегда
достаточен для термина «образовательный дефицит».
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from apps.vpr.evidence.statuses import AnalyticalOrigin, EvidenceStatus
from apps.vpr.fioko_2026.sample import GROUP_SAMPLE_MIN


class EducationalFindingKind:
    EDUCATIONAL_DIFFICULTY = "EDUCATIONAL_DIFFICULTY"
    EDUCATIONAL_DEFICIT = "EDUCATIONAL_DEFICIT"
    CAUSE = "CAUSE"
    RECOMMENDATION = "RECOMMENDATION"


@dataclass(frozen=True, slots=True)
class EducationalClassification:
    finding_kind: str
    evidence_status: str
    analytical_origin: str
    allow_deficit_term: bool
    allow_management_conclusion: bool
    rationale: str


def classify_educational_finding(
    *,
    completion_percent: float | None,
    linked_tasks: Sequence[str] | None = None,
    sample_size: int | None = None,
    catalog_status: str = "",
    problem_band: bool = False,
) -> EducationalClassification:
    """
    Алгоритм:
    1) зафиксировать факт затруднения (низкий % / problem band);
    2) проверить связанность нескольких заданий;
    3) проверить достаточность выборки;
    4) определить evidence_status;
    5) только затем разрешать термин EDUCATIONAL_DEFICIT.
    """
    links = [str(x) for x in (linked_tasks or []) if str(x).strip()]
    multi_task = len(links) >= 2
    has_stat = completion_percent is not None
    cat = (catalog_status or "").upper()
    n = int(sample_size) if sample_size is not None else None

    if n is not None and n < GROUP_SAMPLE_MIN:
        return EducationalClassification(
            finding_kind=EducationalFindingKind.EDUCATIONAL_DIFFICULTY,
            evidence_status=EvidenceStatus.LIMITED_SAMPLE,
            analytical_origin=AnalyticalOrigin.SYSTEM_ANALYTICS,
            allow_deficit_term=False,
            allow_management_conclusion=False,
            rationale=f"N={n} < {GROUP_SAMPLE_MIN}: только диагностическое затруднение.",
        )

    if cat == "PARTIAL" and not links:
        return EducationalClassification(
            finding_kind=EducationalFindingKind.EDUCATIONAL_DIFFICULTY,
            evidence_status=EvidenceStatus.INSUFFICIENT_DATA,
            analytical_origin=AnalyticalOrigin.SYSTEM_ANALYTICS,
            allow_deficit_term=False,
            allow_management_conclusion=False,
            rationale="PARTIAL catalog without linked tasks.",
        )

    if not has_stat and not links:
        return EducationalClassification(
            finding_kind=EducationalFindingKind.EDUCATIONAL_DIFFICULTY,
            evidence_status=EvidenceStatus.INSUFFICIENT_DATA,
            analytical_origin=AnalyticalOrigin.SYSTEM_ANALYTICS,
            allow_deficit_term=False,
            allow_management_conclusion=False,
            rationale="No completion stats and no linked tasks.",
        )

    # Single low % without multi-task linkage → difficulty, not proven deficit
    if problem_band and has_stat and not multi_task:
        return EducationalClassification(
            finding_kind=EducationalFindingKind.EDUCATIONAL_DIFFICULTY,
            evidence_status=EvidenceStatus.INFORMATIVE,
            analytical_origin=AnalyticalOrigin.SYSTEM_ANALYTICS,
            allow_deficit_term=False,
            allow_management_conclusion=False,
            rationale=(
                "Низкий процент выполнения фиксирует затруднение; "
                "устойчивый дефицит без связки ≥2 заданий не устанавливается."
            ),
        )

    if problem_band and multi_task and has_stat:
        return EducationalClassification(
            finding_kind=EducationalFindingKind.EDUCATIONAL_DEFICIT,
            evidence_status=EvidenceStatus.ESTABLISHED,
            analytical_origin=AnalyticalOrigin.SYSTEM_ANALYTICS,
            allow_deficit_term=True,
            allow_management_conclusion=True,
            rationale="Problem band + ≥2 linked tasks + completion stats.",
        )

    if multi_task and has_stat:
        return EducationalClassification(
            finding_kind=EducationalFindingKind.EDUCATIONAL_DIFFICULTY,
            evidence_status=EvidenceStatus.INFORMATIVE,
            analytical_origin=AnalyticalOrigin.SYSTEM_ANALYTICS,
            allow_deficit_term=False,
            allow_management_conclusion=False,
            rationale="Linked tasks present but band is not problem/critical.",
        )

    return EducationalClassification(
        finding_kind=EducationalFindingKind.EDUCATIONAL_DIFFICULTY,
        evidence_status=EvidenceStatus.INFORMATIVE if has_stat else EvidenceStatus.INSUFFICIENT_DATA,
        analytical_origin=AnalyticalOrigin.SYSTEM_ANALYTICS,
        allow_deficit_term=False,
        allow_management_conclusion=False,
        rationale="Default: difficulty/diagnostic only.",
    )
