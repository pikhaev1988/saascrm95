"""Агрегация по предметам."""

from __future__ import annotations

from apps.vpr.school_analysis.metrics import (
    absolute_percent,
    classify_item_risk,
    completion_percent,
    deficits_count,
    participants_count,
    quality_percent,
    safe_mean,
    subject_name,
)
from apps.vpr.school_analysis.schemas import SubjectSchoolRow


class SchoolSubjectsAnalyzer:
    def analyze(self, analyses: list) -> list[SubjectSchoolRow]:
        by_subject: dict[str, list] = {}
        for analysis in analyses:
            name = subject_name(analysis)
            if not name:
                continue
            by_subject.setdefault(name, []).append(analysis)

        rows: list[SubjectSchoolRow] = []
        for subject, items in by_subject.items():
            completion = safe_mean([completion_percent(a) for a in items])
            quality = safe_mean([quality_percent(a) for a in items])
            absolute = safe_mean([absolute_percent(a) for a in items])
            deficits = sum(deficits_count(a) for a in items)
            rows.append(
                SubjectSchoolRow(
                    subject=subject,
                    protocols_count=len(items),
                    participants=sum(participants_count(a) for a in items),
                    avg_completion_percent=completion,
                    quality_percent=quality,
                    absolute_percent=absolute,
                    deficits_count=deficits,
                    risk_level=classify_item_risk(
                        completion=completion,
                        quality=quality,
                        deficits=deficits,
                    ),
                    rank=0,
                )
            )

        rows.sort(
            key=lambda row: (
                -(row.avg_completion_percent or -1),
                row.deficits_count,
                row.subject,
            )
        )
        for idx, row in enumerate(rows, start=1):
            row.rank = idx
        return rows
