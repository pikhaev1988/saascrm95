"""
MetricFact — минимальный provenance-контейнер Stage 10.

Не хранится в БД: строится на лету для ключевых агрегатов отчёта.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


CALCULATION_VERSION = "v10"


@dataclass(slots=True)
class MetricFact:
    metric: str
    value: Any
    source: str
    calculation: str
    threshold: float | None = None
    version: str = CALCULATION_VERSION
    generated_at: str | None = None
    analytics_source: str = "SYSTEM"  # FIOKO | SYSTEM
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if not payload.get("generated_at"):
            payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        if payload.get("extra") is None:
            payload.pop("extra", None)
        return payload


def metric_fact(
    metric: str,
    value: Any,
    *,
    source: str,
    calculation: str,
    threshold: float | None = None,
    analytics_source: str = "SYSTEM",
    **extra: Any,
) -> MetricFact:
    return MetricFact(
        metric=metric,
        value=value,
        source=source,
        calculation=calculation,
        threshold=threshold,
        analytics_source=analytics_source,
        extra=extra or None,
    )


def build_core_metric_facts(*, tasks_below_50: int, participants: int, sample_tier: str) -> list[dict[str, Any]]:
    """Набор ключевых MetricFact для audit/validate."""
    from apps.vpr.analytics.config import below_50_threshold

    thr, inclusive = below_50_threshold()
    return [
        metric_fact(
            "tasks_below_50",
            tasks_below_50,
            source="individual_results",
            calculation="task_completion_threshold",
            threshold=thr,
            analytics_source="SYSTEM",
            inclusive=inclusive,
        ).to_dict(),
        metric_fact(
            "participants",
            participants,
            source="protocol",
            calculation="count_students",
            analytics_source="FIOKO",
        ).to_dict(),
        metric_fact(
            "sample_tier",
            sample_tier,
            source="participants_count",
            calculation="distribution_sample_tier",
            analytics_source="FIOKO",
        ).to_dict(),
    ]
