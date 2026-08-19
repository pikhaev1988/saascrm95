"""Сильные стороны школы."""

from __future__ import annotations

from apps.vpr.labels import label_risk
from apps.vpr.school_analysis.metrics import safe_mean, skill_averages, topic_averages
from apps.vpr.school_analysis.schemas import (
    GradeSchoolRow,
    NamedMetricItem,
    StrengthsProfile,
    SubjectSchoolRow,
)

TOP_N = 5
STRONG_THRESHOLD = 75.0


class SchoolStrengthsAnalyzer:
    def analyze(
        self,
        *,
        analyses: list,
        subjects: list[SubjectSchoolRow],
        grades: list[GradeSchoolRow],
    ) -> StrengthsProfile:
        strong_subjects = [
            NamedMetricItem(
                name=row.subject,
                value=row.avg_completion_percent,
                context=f"риск: {label_risk(row.risk_level)}",
            )
            for row in subjects
            if (row.avg_completion_percent or 0) >= STRONG_THRESHOLD and row.risk_level == "low"
        ][:TOP_N]
        if not strong_subjects:
            strong_subjects = [
                NamedMetricItem(name=row.subject, value=row.avg_completion_percent)
                for row in subjects[: min(3, len(subjects))]
            ]

        topic_map = {k: safe_mean(v) for k, v in topic_averages(analyses).items()}
        skill_map = {k: safe_mean(v) for k, v in skill_averages(analyses).items()}

        topics = [
            NamedMetricItem(name=name, value=value)
            for name, value in sorted(
                topic_map.items(),
                key=lambda pair: pair[1] if pair[1] is not None else -1,
                reverse=True,
            )
            if value is not None and value >= STRONG_THRESHOLD
        ][:TOP_N]

        skills = [
            NamedMetricItem(name=name, value=value)
            for name, value in sorted(
                skill_map.items(),
                key=lambda pair: pair[1] if pair[1] is not None else -1,
                reverse=True,
            )
            if value is not None and value >= STRONG_THRESHOLD
        ][:TOP_N]

        strong_grades = [
            NamedMetricItem(
                name=f"{row.parallel} класс",
                value=row.avg_completion_percent,
            )
            for row in sorted(
                grades,
                key=lambda g: g.avg_completion_percent if g.avg_completion_percent is not None else -1,
                reverse=True,
            )
            if (row.avg_completion_percent or 0) >= STRONG_THRESHOLD
        ][:TOP_N]

        return StrengthsProfile(
            subjects=strong_subjects,
            topics=topics,
            skills=skills,
            grades=strong_grades,
        )
