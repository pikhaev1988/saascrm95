"""Классификатор профиля риска школы."""

from __future__ import annotations

from apps.vpr.school_analysis.metrics import risk_group_percent, safe_mean
from apps.vpr.school_analysis.schemas import (
    SchoolDeficitsProfile,
    SchoolOverview,
    SchoolRiskProfile,
)

CLASS_HIGH = "HIGH_RISK"
CLASS_MEDIUM = "MEDIUM_RISK"
CLASS_LOW = "LOW_RISK"
CLASS_STABLE = "STABLE"


class SchoolRiskClassifier:
    def classify(
        self,
        *,
        overview: SchoolOverview,
        deficits: SchoolDeficitsProfile,
        analyses: list,
    ) -> SchoolRiskProfile:
        if not overview.has_data:
            return SchoolRiskProfile(
                classification=CLASS_STABLE,
                reasons=["Нет данных ВПР для классификации риска."],
            )

        quality = overview.avg_quality_percent
        completion = overview.avg_completion_percent
        deficits_total = (
            deficits.total_critical
            + deficits.total_high
            + deficits.total_medium
            + deficits.total_low
        )
        risk_pct = safe_mean([risk_group_percent(a) for a in analyses])
        reasons: list[str] = []

        high_signals = 0
        if quality is not None and quality < 40:
            high_signals += 1
            reasons.append("Низкое среднее качество знаний по школе.")
        if completion is not None and completion < 50:
            high_signals += 1
            reasons.append("Низкий средний процент выполнения.")
        if deficits.total_critical >= 3 or deficits_total >= 15:
            high_signals += 1
            reasons.append("Большое число образовательных дефицитов.")
        if risk_pct is not None and risk_pct >= 35:
            high_signals += 1
            reasons.append("Высокая доля участников группы риска.")

        medium_signals = 0
        if quality is not None and 40 <= quality < 55:
            medium_signals += 1
            reasons.append("Качество знаний ниже устойчивого уровня.")
        if completion is not None and 50 <= completion < 65:
            medium_signals += 1
            reasons.append("Результаты выполнения требуют внимания.")
        if deficits.total_high >= 3 or (5 <= deficits_total < 15):
            medium_signals += 1
            reasons.append("Зафиксированы дефициты высокого приоритета.")
        if risk_pct is not None and 20 <= risk_pct < 35:
            medium_signals += 1
            reasons.append("Заметная доля участников группы риска.")

        if high_signals >= 2:
            classification = CLASS_HIGH
        elif high_signals == 1 or medium_signals >= 2:
            classification = CLASS_MEDIUM
        elif medium_signals == 1:
            classification = CLASS_LOW
            reasons.append("Локальные риски без системного характера.")
        else:
            classification = CLASS_STABLE
            reasons.append("Критических системных рисков не выявлено.")

        return SchoolRiskProfile(
            classification=classification,
            reasons=reasons,
            risk_group_percent=risk_pct,
            quality_percent=quality,
            deficits_total=deficits_total,
        )
