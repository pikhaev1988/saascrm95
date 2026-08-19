"""Тематический анализ — группировка заданий и классификация дефицитов."""

from __future__ import annotations

from apps.vpr.analytics.result import VprAnalyticsResult
from apps.vpr.comprehensive_analysis.schemas import VprTopicAnalysisProfile, VprTopicProfileItem
from apps.vpr.deficits.result import VprDeficitResult

LOW_THRESHOLD = 60.0
PLACEHOLDER = "Без темы в справочнике"


class VprTopicAnalyzer:
    """
    Берёт агрегаты тем из analytics.topics (уже посчитаны движком).
    Классифицирует локальный/массовый тематический дефицит по числу слабых заданий.
    """

    def analyze(
        self,
        analytics: VprAnalyticsResult,
        deficits: VprDeficitResult | None = None,
        *,
        low_threshold: float = LOW_THRESHOLD,
    ) -> VprTopicAnalysisProfile:
        deficit_topics = {
            item.topic: item for item in (deficits.topics if deficits else []) if item.topic
        }
        # completion по кодам заданий
        task_pct = {
            t.task_code: t.completion_percent
            for t in analytics.tasks
            if t.completion_percent is not None
        }

        items: list[VprTopicProfileItem] = []
        mass: list[str] = []
        local: list[str] = []

        for topic_row in analytics.topics:
            topic = (topic_row.topic or "").strip() or PLACEHOLDER
            codes = list(topic_row.task_codes or [])
            low_codes = [
                code
                for code in codes
                if task_pct.get(code) is not None and float(task_pct[code]) < low_threshold
            ]
            avg = topic_row.avg_completion_percent
            d = deficit_topics.get(topic)
            if d is not None and d.avg_completion_percent is not None:
                avg = d.avg_completion_percent

            deficit_type = self._deficit_type(
                topic=topic,
                low_count=len(low_codes),
                tasks_count=len(codes),
                deficit_risk=(d.risk if d else ""),
            )
            items.append(
                VprTopicProfileItem(
                    topic=topic,
                    tasks=codes,
                    average=avg,
                    deficit_type=deficit_type,
                    low_tasks_count=len(low_codes),
                )
            )
            if deficit_type == "mass" and topic != PLACEHOLDER:
                mass.append(topic)
            elif deficit_type == "local" and topic != PLACEHOLDER:
                local.append(topic)

        return VprTopicAnalysisProfile(items=items, mass_deficits=mass, local_deficits=local)

    @staticmethod
    def _deficit_type(
        *,
        topic: str,
        low_count: int,
        tasks_count: int,
        deficit_risk: str,
    ) -> str:
        if topic == PLACEHOLDER:
            return "none"
        if low_count >= 2 or (tasks_count >= 2 and deficit_risk == "high"):
            return "mass"
        if low_count == 1 or deficit_risk in {"medium", "high"}:
            return "local"
        return "none"
