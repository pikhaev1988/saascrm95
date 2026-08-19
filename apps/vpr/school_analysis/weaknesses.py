"""Проблемные направления школы."""

from __future__ import annotations

from apps.vpr.labels import label_risk
from apps.vpr.school_analysis.metrics import safe_mean, skill_averages, topic_averages
from apps.vpr.school_analysis.schemas import (
    GradeSchoolRow,
    NamedMetricItem,
    SubjectSchoolRow,
    WeaknessesProfile,
)

TOP_N = 5
WEAK_THRESHOLD = 60.0


class SchoolWeaknessesAnalyzer:
    def analyze(
        self,
        *,
        analyses: list,
        subjects: list[SubjectSchoolRow],
        grades: list[GradeSchoolRow],
    ) -> WeaknessesProfile:
        weak_subjects = [
            NamedMetricItem(
                name=row.subject,
                value=row.avg_completion_percent,
                context=f"дефицитов: {row.deficits_count}",
            )
            for row in sorted(
                subjects,
                key=lambda r: (
                    r.avg_completion_percent if r.avg_completion_percent is not None else 999,
                    -r.deficits_count,
                ),
            )
            if (row.avg_completion_percent is not None and row.avg_completion_percent < WEAK_THRESHOLD)
            or row.risk_level in {"high", "medium"}
            or row.deficits_count > 0
        ][:TOP_N]

        topic_map = {k: safe_mean(v) for k, v in topic_averages(analyses).items()}
        skill_map = {k: safe_mean(v) for k, v in skill_averages(analyses).items()}

        topics = [
            NamedMetricItem(name=name, value=value)
            for name, value in sorted(
                topic_map.items(),
                key=lambda pair: pair[1] if pair[1] is not None else 999,
            )
            if value is not None and value < WEAK_THRESHOLD
        ][:TOP_N]

        skills = [
            NamedMetricItem(name=name, value=value)
            for name, value in sorted(
                skill_map.items(),
                key=lambda pair: pair[1] if pair[1] is not None else 999,
            )
            if value is not None and value < WEAK_THRESHOLD
        ][:TOP_N]

        weak_grades = [
            NamedMetricItem(
                name=f"{row.parallel} класс",
                value=row.avg_completion_percent,
                context=f"риск: {label_risk(row.risk_level)}",
            )
            for row in sorted(
                grades,
                key=lambda g: g.avg_completion_percent if g.avg_completion_percent is not None else 999,
            )
            if (row.avg_completion_percent is not None and row.avg_completion_percent < WEAK_THRESHOLD)
            or row.risk_level in {"high", "medium"}
        ][:TOP_N]

        return WeaknessesProfile(
            subjects=weak_subjects,
            topics=topics,
            skills=skills,
            grades=weak_grades,
        )
