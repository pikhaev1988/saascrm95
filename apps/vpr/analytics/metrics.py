"""
VPR Metric Layer: воспроизводимые проценты и инварианты.

completion_percent ≠ full_score_rate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.vpr.exceptions import VprValidationError


@dataclass(slots=True)
class CalculationResult:
    """Прозрачный результат процентного расчёта VPR."""

    value: float | None
    numerator: float | None
    denominator: float | None
    formula_type: str
    rounding: int = 2
    source_metric: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "formula_type": self.formula_type,
            "rounding": self.rounding,
            "source_metric": self.source_metric,
        }


def rate_percent(
    numerator: float | int | None,
    denominator: float | int | None,
    *,
    formula_type: str,
    source_metric: str = "",
    digits: int = 2,
) -> CalculationResult:
    """
    Процент с явной формулой.
    Пустой знаменатель → value=None (нет данных), не 0% и не NaN.
    """
    if numerator is None or denominator is None:
        return CalculationResult(
            value=None,
            numerator=None if numerator is None else float(numerator),
            denominator=None if denominator is None else float(denominator),
            formula_type=formula_type,
            rounding=digits,
            source_metric=source_metric,
        )
    den = float(denominator)
    num = float(numerator)
    if den == 0:
        return CalculationResult(
            value=None,
            numerator=num,
            denominator=den,
            formula_type=formula_type,
            rounding=digits,
            source_metric=source_metric,
        )
    return CalculationResult(
        value=round((num / den) * 100.0, digits),
        numerator=num,
        denominator=den,
        formula_type=formula_type,
        rounding=digits,
        source_metric=source_metric,
    )


def assert_task_count_invariant(
    *,
    full_score_count: int,
    partial_score_count: int,
    zero_score_count: int,
    total_students: int,
    task_code: str = "",
) -> None:
    total = int(full_score_count) + int(partial_score_count) + int(zero_score_count)
    if total != int(total_students):
        raise VprValidationError(
            "VPR task metric invariant failed: full+partial+zero != total_students"
            + (f" (task={task_code})" if task_code else ""),
            details=[
                f"full={full_score_count}",
                f"partial={partial_score_count}",
                f"zero={zero_score_count}",
                f"sum={total}",
                f"total_students={total_students}",
            ],
        )


def build_task_rate_fields(
    *,
    full_score_count: int,
    partial_score_count: int,
    zero_score_count: int,
    total_students: int,
    earned_points_sum: float,
    max_score: int,
    task_code: str = "",
) -> dict[str, Any]:
    """Собрать канонические rate-поля задания (и проверить инвариант)."""
    assert_task_count_invariant(
        full_score_count=full_score_count,
        partial_score_count=partial_score_count,
        zero_score_count=zero_score_count,
        total_students=total_students,
        task_code=task_code,
    )
    max_points_sum = float(max_score) * float(total_students) if max_score > 0 else 0.0
    full_rate = rate_percent(
        full_score_count,
        total_students,
        formula_type="full_score_count/total_students*100",
        source_metric="full_score_rate",
    )
    partial_rate = rate_percent(
        partial_score_count,
        total_students,
        formula_type="partial_score_count/total_students*100",
        source_metric="partial_score_rate",
    )
    zero_rate = rate_percent(
        zero_score_count,
        total_students,
        formula_type="zero_score_count/total_students*100",
        source_metric="zero_score_rate",
    )
    completion = rate_percent(
        earned_points_sum,
        max_points_sum if max_score > 0 else None,
        formula_type="earned_points_sum/max_points_sum*100",
        source_metric="completion_percent",
    )
    return {
        "total_students": int(total_students),
        "full_score_count": int(full_score_count),
        "partial_score_count": int(partial_score_count),
        "zero_score_count": int(zero_score_count),
        "earned_points_sum": float(earned_points_sum),
        "max_points_sum": float(max_points_sum) if max_score > 0 else None,
        "full_score_rate": full_rate.value,
        "partial_score_rate": partial_rate.value,
        "zero_score_rate": zero_rate.value,
        "completion_percent": completion.value,
        "calculations": {
            "full_score_rate": full_rate.to_dict(),
            "partial_score_rate": partial_rate.to_dict(),
            "zero_score_rate": zero_rate.to_dict(),
            "completion_percent": completion.to_dict(),
        },
    }
