"""Анализ выполнения заданий — классификация статусов поверх analytics/deficits."""

from __future__ import annotations

from apps.vpr.analytics.result import VprAnalyticsResult
from apps.vpr.comprehensive_analysis.schemas import VprTaskAnalysisProfile, VprTaskProfileItem
from apps.vpr.deficits.result import VprDeficitResult, VprTaskDeficit

STATUS_HIGH = "HIGH"
STATUS_NORMAL = "NORMAL"
STATUS_RISK = "RISK"
STATUS_CRITICAL = "CRITICAL"

PLACEHOLDER_TOPIC = "Без темы в справочнике"
PLACEHOLDER_SKILL = "Без умения в справочнике"


class VprTaskAnalyzer:
    """
    Использует completion_percent и справочные поля из analytics,
    приоритет дефицита — из VprDeficitEngine (без повторного расчёта %).
    """

    def analyze(
        self,
        analytics: VprAnalyticsResult,
        deficits: VprDeficitResult | None = None,
    ) -> VprTaskAnalysisProfile:
        deficit_by_code = {
            item.task_code: item for item in (deficits.tasks if deficits else [])
        }
        items: list[VprTaskProfileItem] = []
        matched = 0
        for task in analytics.tasks:
            d = deficit_by_code.get(task.task_code)
            status = self._status(task.completion_percent, d)
            topic = (task.topic or "").strip()
            skill = (task.checked_skill or "").strip()
            if task.catalog_matched:
                matched += 1
            correct = int(getattr(task, "correct_count", None) or task.full_count or 0)
            answers = int(task.answers_count or 0)
            incorrect = max(0, answers - correct)
            items.append(
                VprTaskProfileItem(
                    task=task.task_code,
                    topic=topic or PLACEHOLDER_TOPIC,
                    skill=skill or PLACEHOLDER_SKILL,
                    section=(task.program_section or "").strip(),
                    success=task.completion_percent,
                    difficulty=(task.difficulty or "").strip(),
                    status=status,
                    catalog_matched=bool(task.catalog_matched),
                    correct_count=correct,
                    incorrect_count=incorrect,
                    partial_count=int(task.partial_count or 0),
                    answers_count=answers,
                )
            )

        total = len(items)
        if total == 0 or matched == 0:
            coverage = "none"
        elif matched == total:
            coverage = "full"
        else:
            coverage = "partial"

        return VprTaskAnalysisProfile(
            items=items,
            catalog_coverage=coverage,
            critical_count=sum(1 for i in items if i.status == STATUS_CRITICAL),
            risk_count=sum(1 for i in items if i.status == STATUS_RISK),
        )

    @staticmethod
    def _status(completion: float | None, deficit: VprTaskDeficit | None) -> str:
        if deficit is not None:
            if deficit.status == "critical_deficit" or deficit.priority == "Critical":
                return STATUS_CRITICAL
            if deficit.status == "problem_zone" or deficit.priority == "High":
                return STATUS_RISK
            if deficit.mastery_level in {"high", "sufficient"}:
                return STATUS_HIGH
            return STATUS_NORMAL
        if completion is None:
            return STATUS_NORMAL
        if completion < 40:
            return STATUS_CRITICAL
        if completion < 60:
            return STATUS_RISK
        if completion < 75:
            return STATUS_NORMAL
        return STATUS_HIGH
