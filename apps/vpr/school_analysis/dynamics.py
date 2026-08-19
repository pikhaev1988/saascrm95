"""Динамика результатов школы по учебным годам."""

from __future__ import annotations

from apps.vpr.school_analysis.metrics import (
    completion_percent,
    participants_count,
    quality_percent,
    safe_mean,
    academic_year_value,
)
from apps.vpr.school_analysis.schemas import SchoolDynamicsProfile, YearDynamicsPoint

INSUFFICIENT = "Недостаточно данных для анализа динамики."


class SchoolDynamicsAnalyzer:
    def analyze(self, analyses_by_year: dict[int, list]) -> SchoolDynamicsProfile:
        years = sorted(y for y, items in analyses_by_year.items() if items)
        if len(years) < 2:
            return SchoolDynamicsProfile(available=False, message=INSUFFICIENT, points=[])

        points: list[YearDynamicsPoint] = []
        prev_completion: float | None = None
        for year in years:
            items = analyses_by_year[year]
            completion = safe_mean([completion_percent(a) for a in items])
            quality = safe_mean([quality_percent(a) for a in items])
            trend = "baseline"
            if prev_completion is not None and completion is not None:
                delta = completion - prev_completion
                if delta >= 2:
                    trend = "up"
                elif delta <= -2:
                    trend = "down"
                else:
                    trend = "stable"
            points.append(
                YearDynamicsPoint(
                    academic_year=year,
                    avg_completion_percent=completion,
                    quality_percent=quality,
                    participants=sum(participants_count(a) for a in items),
                    protocols_count=len(items),
                    trend=trend,
                )
            )
            prev_completion = completion

        return SchoolDynamicsProfile(
            available=True,
            message="",
            points=points,
        )

    @staticmethod
    def group_by_year(analyses: list) -> dict[int, list]:
        result: dict[int, list] = {}
        for analysis in analyses:
            year = academic_year_value(analysis)
            result.setdefault(year, []).append(analysis)
        return result
