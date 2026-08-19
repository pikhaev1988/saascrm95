"""Классификация образовательной организации по результатам ВПР."""

from __future__ import annotations

from apps.vpr.comprehensive_analysis.schemas import (
    VprAchievementProfile,
    VprObjectivityProfile,
    VprParticipantGroupsProfile,
    VprSchoolProfile,
    VprTopicAnalysisProfile,
)
from apps.vpr.deficits.result import VprDeficitResult

CLASS_HIGH = "HIGH_RESULTS"
CLASS_LOW = "LOW_RESULTS"
CLASS_OBJECTIVITY = "OBJECTIVITY_RISK"
CLASS_STABLE = "STABLE"
CLASS_ATTENTION = "ATTENTION_REQUIRED"


class VprSchoolProfileClassifier:
    """
    Правила классификации ОО на основе уже собранных срезов профиля.
    Не пересчитывает первичные метрики.
    """

    def classify(
        self,
        *,
        achievement: VprAchievementProfile,
        groups: VprParticipantGroupsProfile,
        objectivity: VprObjectivityProfile,
        topics: VprTopicAnalysisProfile,
        deficits: VprDeficitResult | None = None,
    ) -> VprSchoolProfile:
        reasons: list[str] = []
        labels: list[str] = []

        risk_group = groups.groups.get("risk")
        risk_pct = risk_group.percent if risk_group else 0.0
        high_group = groups.groups.get("high")
        high_pct = high_group.percent if high_group else 0.0

        quality = achievement.quality_percent
        mean = achievement.mean_score
        max_score = achievement.max_score or 0
        mean_share = (float(mean) / float(max_score) * 100.0) if mean is not None and max_score else None

        deficits_count = 0
        if deficits is not None:
            deficits_count = int(deficits.summary.tasks_critical) + int(deficits.summary.tasks_problem)

        mass_topics = len(topics.mass_deficits)

        low_results = (
            (mean_share is not None and mean_share < 50)
            or (quality is not None and quality < 40)
            or risk_pct >= 40
            or deficits_count >= 5
            or mass_topics >= 2
        )
        if low_results:
            reasons.append("Низкий средний результат и/или высокая доля группы риска, много дефицитов.")
            labels.append(CLASS_LOW)

        objectivity_risk = objectivity.risk_level == "high"
        if objectivity_risk:
            reasons.append("Существенные расхождения отметок ВПР и журнала или подозрительное распределение.")
            labels.append(CLASS_OBJECTIVITY)

        high_results = (
            (mean_share is not None and mean_share >= 70)
            and (quality is not None and quality >= 60)
            and risk_pct < 15
            and deficits_count <= 1
            and not objectivity_risk
        )
        if high_results:
            reasons.append("Высокие результаты, низкая доля группы риска, дефициты единичны.")
            labels.append(CLASS_HIGH)

        # итоговая классификация (приоритет рисков)
        if objectivity_risk and low_results:
            classification = CLASS_ATTENTION
            reasons.append("Требуется управленческое внимание: сочетание низких результатов и рисков объективности.")
        elif objectivity_risk:
            classification = CLASS_OBJECTIVITY
        elif low_results:
            classification = CLASS_LOW
        elif high_results:
            classification = CLASS_HIGH
        elif risk_pct >= 20 or mass_topics >= 1 or deficits_count >= 2:
            classification = CLASS_ATTENTION
            reasons.append("Есть признаки неустойчивости результатов, требуется методический контроль.")
            labels.append(CLASS_ATTENTION)
        else:
            classification = CLASS_STABLE
            reasons.append("Результаты относительно стабильны, критических системных рисков не выявлено.")
            labels.append(CLASS_STABLE)

        if high_pct >= 50 and classification == CLASS_STABLE:
            reasons.append("Значительная доля участников с высоким уровнем выполнения.")

        return VprSchoolProfile(
            classification=classification,
            reasons=reasons,
            labels=sorted(set(labels)),
        )
