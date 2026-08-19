"""Группы участников по уровню выполнения."""

from __future__ import annotations

from apps.vpr.analytics.result import VprAnalyticsResult
from apps.vpr.comprehensive_analysis.schemas import VprGroupBucket, VprParticipantGroupsProfile

# Доля выполнения от максимума первичного балла
HIGH_MIN = 80.0
MEDIUM_MIN = 50.0


class VprParticipantGroupAnalyzer:
    """
    Делит участников по completion_percent из analytics.students
    (уже рассчитан VprAnalyticsEngine).
    """

    def analyze(self, analytics: VprAnalyticsResult) -> VprParticipantGroupsProfile:
        buckets: dict[str, list[str]] = {"high": [], "medium": [], "risk": []}
        for student in analytics.students:
            pct = student.completion_percent
            if pct is None and analytics.summary.max_primary_score and student.primary_score is not None:
                pct = float(student.primary_score) / float(analytics.summary.max_primary_score) * 100.0
            if pct is None:
                continue
            if pct >= HIGH_MIN:
                buckets["high"].append(student.participant_code)
            elif pct >= MEDIUM_MIN:
                buckets["medium"].append(student.participant_code)
            else:
                buckets["risk"].append(student.participant_code)

        total = sum(len(v) for v in buckets.values()) or 1
        groups = {
            key: VprGroupBucket(
                count=len(codes),
                percent=round(100.0 * len(codes) / total, 1),
                participant_codes=codes,
            )
            for key, codes in buckets.items()
        }
        return VprParticipantGroupsProfile(groups=groups)
