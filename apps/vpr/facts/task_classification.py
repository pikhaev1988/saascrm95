"""
Единый Task Classification Engine.

Все пороги — из Methodology Registry / VPR_THRESHOLDS.
Запрещено дублировать if completion < … в renderer/narrative/recommendations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from apps.vpr.analytics.thresholds import VPR_THRESHOLDS
from apps.vpr.methodology import SYSTEM_ANALYTICS_RULES, rule_value

STATUS_HIGH = "HIGH"
STATUS_NORMAL = "NORMAL"
STATUS_RISK = "RISK"
STATUS_CRITICAL = "CRITICAL"
STATUS_NOT_AVAILABLE = "NOT_AVAILABLE"

RULE_BELOW_50 = "tasks.below_50"
RULE_BELOW_40 = "tasks.below_40"
RULE_CRITICAL_MAX = "tasks.critical_max"
RULE_RISK_MAX = "tasks.risk_max"
RULE_NORMAL_MAX = "tasks.normal_max"


def _thr(name: str, default: float) -> float:
    val = rule_value(SYSTEM_ANALYTICS_RULES, name, default)
    return float(val if val is not None else default)


def task_band_thresholds() -> dict[str, float]:
    deficits = VPR_THRESHOLDS.get("deficits") or {}
    return {
        "below_50": _thr(RULE_BELOW_50, 50.0),
        "below_40": _thr(RULE_BELOW_40, float(deficits.get("problem", 40.0))),
        "critical_max": _thr(RULE_CRITICAL_MAX, float(deficits.get("problem", 40.0))),
        "risk_max": _thr(RULE_RISK_MAX, float(deficits.get("acceptable", 60.0))),
        "normal_max": _thr(RULE_NORMAL_MAX, float(deficits.get("sufficient", 75.0))),
    }


@dataclass(slots=True)
class TaskClassificationResult:
    task_id: str
    completion_percent: float | None
    full_score: int
    partial_score: int
    zero_score: int
    classification: str
    classification_rule_id: str
    classification_source: str
    below_50: bool = False
    below_40: bool = False
    is_critical: bool = False
    is_problem: bool = False
    is_informative: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_task(
    *,
    task_id: str,
    completion_percent: float | None,
    full_score: int = 0,
    partial_score: int = 0,
    zero_score: int = 0,
    deficit_status: str | None = None,
    deficit_priority: str | None = None,
    deficit_mastery: str | None = None,
) -> TaskClassificationResult:
    bands = task_band_thresholds()
    source = "SYSTEM_ANALYTICS"
    rule_id = "tasks.mastery_bands"

    if completion_percent is None and not deficit_status:
        return TaskClassificationResult(
            task_id=str(task_id),
            completion_percent=None,
            full_score=int(full_score or 0),
            partial_score=int(partial_score or 0),
            zero_score=int(zero_score or 0),
            classification=STATUS_NOT_AVAILABLE,
            classification_rule_id="tasks.not_available",
            classification_source=source,
            below_50=False,
            below_40=False,
            is_critical=False,
            is_problem=False,
            is_informative=False,
        )

    status = STATUS_NORMAL
    if deficit_status == "critical_deficit" or deficit_priority == "Critical":
        status = STATUS_CRITICAL
        rule_id = "deficits.critical"
    elif deficit_status == "problem_zone" or deficit_priority == "High":
        status = STATUS_RISK
        rule_id = "deficits.problem"
    elif deficit_mastery in {"high", "sufficient"}:
        status = STATUS_HIGH
        rule_id = "deficits.mastery"
    elif deficit_status in {"ok", "not_available"}:
        status = STATUS_HIGH if deficit_mastery in {"high", "sufficient"} else STATUS_NORMAL
        rule_id = "deficits.status"
    elif completion_percent is None:
        status = STATUS_NOT_AVAILABLE
        rule_id = "tasks.not_available"
    else:
        pct = float(completion_percent)
        if pct < bands["critical_max"]:
            status = STATUS_CRITICAL
            rule_id = RULE_CRITICAL_MAX
        elif pct < bands["risk_max"]:
            status = STATUS_RISK
            rule_id = RULE_RISK_MAX
        elif pct < bands["normal_max"]:
            status = STATUS_NORMAL
            rule_id = RULE_NORMAL_MAX
        else:
            status = STATUS_HIGH
            rule_id = "tasks.high_min"

    pct = float(completion_percent) if completion_percent is not None else None
    from apps.vpr.analytics.config import below_50_threshold, is_below_threshold

    thr50, incl50 = below_50_threshold()
    below_50 = is_below_threshold(pct, thr50, inclusive=incl50)
    below_40 = pct is not None and pct < bands["below_40"]
    is_critical = status == STATUS_CRITICAL
    is_problem = status in {STATUS_CRITICAL, STATUS_RISK}
    is_informative = status != STATUS_NOT_AVAILABLE
    return TaskClassificationResult(
        task_id=str(task_id),
        completion_percent=pct,
        full_score=int(full_score or 0),
        partial_score=int(partial_score or 0),
        zero_score=int(zero_score or 0),
        classification=status,
        classification_rule_id=rule_id,
        classification_source=source,
        below_50=below_50,
        below_40=below_40,
        is_critical=is_critical,
        is_problem=is_problem,
        is_informative=is_informative,
    )


def classify_tasks(items: Iterable[Any], *, deficits_by_code: dict | None = None) -> list[TaskClassificationResult]:
    by_code = deficits_by_code or {}
    out: list[TaskClassificationResult] = []
    for item in items:
        code = str(
            getattr(item, "task_code", None)
            or getattr(item, "task", None)
            or getattr(item, "task_id", None)
            or ""
        )
        d = by_code.get(code)
        full = int(
            getattr(item, "full_score_count", None)
            or getattr(item, "full_count", None)
            or getattr(item, "correct_count", 0)
            or 0
        )
        partial = int(getattr(item, "partial_score_count", None) or getattr(item, "partial_count", 0) or 0)
        zero = int(
            getattr(item, "zero_score_count", None)
            or getattr(item, "zero_count", None)
            or getattr(item, "incorrect_count", 0)
            or 0
        )
        out.append(
            classify_task(
                task_id=code,
                completion_percent=getattr(item, "completion_percent", None),
                full_score=full,
                partial_score=partial,
                zero_score=zero,
                deficit_status=getattr(d, "status", None) if d is not None else None,
                deficit_priority=getattr(d, "priority", None) if d is not None else None,
                deficit_mastery=getattr(d, "mastery_level", None) if d is not None else None,
            )
        )
    return out
