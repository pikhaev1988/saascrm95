"""Общая характеристика школы по протоколам ВПР."""

from __future__ import annotations

from apps.vpr.school_analysis.metrics import (
    absolute_percent,
    completion_percent,
    deficits_count,
    participants_count,
    quality_percent,
    subject_name,
    parallel_value,
    unique_participants_count,
    weighted_mean,
)
from apps.vpr.school_analysis.schemas import SchoolOverview


class SchoolOverviewBuilder:
    def build(
        self,
        analyses: list,
        *,
        organization_name: str,
        academic_year: int | None,
        protocols: list | None = None,
    ) -> SchoolOverview:
        if not analyses:
            return SchoolOverview(
                organization_name=organization_name,
                academic_year=academic_year,
                has_data=False,
            )
        subjects = {subject_name(a) for a in analyses if subject_name(a)}
        grades = {parallel_value(a) for a in analyses}
        weights = [participants_count(a) for a in analyses]
        protocol_list = protocols or [a.protocol for a in analyses if getattr(a, "protocol", None)]
        unique_total = unique_participants_count(protocol_list) if protocol_list else 0
        if unique_total > 0:
            participants_total = unique_total
        else:
            # Для моков/кратких DTO без student_results — максимум по протоколам
            participants_total = max((participants_count(a) for a in analyses), default=0)
        return SchoolOverview(
            protocols_count=len(analyses),
            subjects_count=len(subjects),
            grades_count=len(grades),
            participants_total=participants_total,
            avg_completion_percent=weighted_mean(
                [(completion_percent(a), w) for a, w in zip(analyses, weights)]
            ),
            avg_quality_percent=weighted_mean(
                [(quality_percent(a), w) for a, w in zip(analyses, weights)]
            ),
            avg_absolute_percent=weighted_mean(
                [(absolute_percent(a), w) for a, w in zip(analyses, weights)]
            ),
            avg_deficits_count=weighted_mean(
                [(float(deficits_count(a)), w) for a, w in zip(analyses, weights)]
            ),
            organization_name=organization_name,
            academic_year=academic_year,
            has_data=True,
        )
