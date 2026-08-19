"""Профиль достижений участников — поверх метрик VprAnalyticsEngine."""

from __future__ import annotations

from apps.vpr.analytics.result import VprAnalyticsResult
from apps.vpr.comprehensive_analysis.schemas import VprAchievementProfile

# Пороги коэффициента вариации для оценки неоднородности (ФИОКО-подход)
CV_HIGH = 30.0
CV_MEDIUM = 15.0


class VprAchievementAnalyzer:
    """
    Не пересчитывает статистику: берёт summary/marks из analytics.
    Добавляет только классификацию неоднородности.
    """

    def analyze(self, analytics: VprAnalyticsResult) -> VprAchievementProfile:
        s = analytics.summary
        cv = s.cv_primary_score_percent
        return VprAchievementProfile(
            participants=int(s.participants_count or 0),
            mean_score=s.avg_primary_score,
            median=s.median_primary_score,
            max_score=int(s.max_primary_score or 0),
            stdev=s.stdev_primary_score,
            cv_percent=cv,
            distribution=dict(analytics.marks.vpr or {}),
            quality_percent=s.knowledge_quality_percent,
            absolute_percent=s.absolute_achievement_percent,
            heterogeneity=self._heterogeneity(cv),
        )

    @staticmethod
    def _heterogeneity(cv: float | None) -> str:
        if cv is None:
            return "unknown"
        if cv >= CV_HIGH:
            return "high"
        if cv >= CV_MEDIUM:
            return "medium"
        return "low"
