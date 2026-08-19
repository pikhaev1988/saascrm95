"""Анализ объективности: сопоставление отметки ВПР и журнала."""

from __future__ import annotations

from apps.vpr.analytics.result import VprAnalyticsResult
from apps.vpr.comprehensive_analysis.schemas import VprObjectivityProfile

RISK_HIGH_LOWER_PCT = 40.0
RISK_MEDIUM_LOWER_PCT = 20.0


class VprObjectivityAnalyzer:
    """
    Считает lower / equal / higher по парам mark_vpr vs mark_journal
    из analytics.students (без повторного чтения БД).
    """

    def analyze(self, analytics: VprAnalyticsResult) -> VprObjectivityProfile:
        lower = equal = higher = 0
        for student in analytics.students:
            vpr = student.mark_vpr
            journal = student.mark_journal
            if vpr is None or journal is None:
                continue
            if vpr < journal:
                lower += 1
            elif vpr > journal:
                higher += 1
            else:
                equal += 1

        compared = lower + equal + higher
        percents = {
            "lower": round(100.0 * lower / compared, 1) if compared else 0.0,
            "equal": round(100.0 * equal / compared, 1) if compared else 0.0,
            "higher": round(100.0 * higher / compared, 1) if compared else 0.0,
        }
        return VprObjectivityProfile(
            journal_comparison={"lower": lower, "equal": equal, "higher": higher},
            journal_comparison_percents=percents,
            compared_count=compared,
            risk_level=self._risk(percents["lower"], percents["higher"], analytics),
        )

    @staticmethod
    def _risk(lower_pct: float, higher_pct: float, analytics: VprAnalyticsResult) -> str:
        # подозрительное распределение: почти все 4–5 при низком среднем первичном
        marks = analytics.marks.vpr or {}
        total_marks = sum(int(v) for v in marks.values()) or 0
        high_share = 0.0
        if total_marks:
            high_share = 100.0 * (int(marks.get("4", 0)) + int(marks.get("5", 0))) / total_marks
        avg = analytics.summary.avg_primary_score
        max_score = analytics.summary.max_primary_score or 0
        avg_share = (float(avg) / float(max_score) * 100.0) if avg is not None and max_score else None
        suspicious = high_share >= 80 and avg_share is not None and avg_share < 55

        if lower_pct >= RISK_HIGH_LOWER_PCT or higher_pct >= RISK_HIGH_LOWER_PCT or suspicious:
            return "high"
        if lower_pct >= RISK_MEDIUM_LOWER_PCT or higher_pct >= RISK_MEDIUM_LOWER_PCT:
            return "medium"
        return "low"
