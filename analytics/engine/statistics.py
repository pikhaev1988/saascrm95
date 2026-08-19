from __future__ import annotations

import math
from statistics import median


def safe_mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def safe_median(values: list[float]) -> float:
    return round(float(median(values)), 2) if values else 0.0


def pearson_correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return round(num / (den_x * den_y), 4)


def difficulty_index(success_rate: float) -> float:
    """Коэффициент сложности: доля неверных ответов (0–100)."""
    return round(max(0.0, 100.0 - success_rate), 2)


def measurable_stat(value: float, sample_size: int, min_size: int = 6) -> float | None:
    """Не показывать статистику при недостаточной выборке."""
    if sample_size < min_size:
        return None
    return value


def discrimination_index(task_success_flags: list[int], total_scores: list[float]) -> float | None:
    """Индекс дискриминации по верхней и нижней трети итогового балла."""
    if len(task_success_flags) != len(total_scores) or len(total_scores) < 6:
        return None
    paired = sorted(zip(total_scores, task_success_flags), key=lambda item: item[0])
    third = max(1, len(paired) // 3)
    low = paired[:third]
    high = paired[-third:]
    low_rate = sum(flag for _, flag in low) / len(low)
    high_rate = sum(flag for _, flag in high) / len(high)
    return round((high_rate - low_rate) * 100, 2)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return ordered[int(k)]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def dynamic_thresholds(success_rates: list[float]) -> dict[str, float]:
    """Автоматические пороги по распределению успешности заданий."""
    if not success_rates:
        return {"critical": 0.0, "weak": 25.0, "medium": 50.0, "strong": 75.0}
    q1 = percentile(success_rates, 25)
    q2 = percentile(success_rates, 50)
    q3 = percentile(success_rates, 75)
    return {
        "critical": round(max(0.0, q1 - 10), 1),
        "weak": round(q1, 1),
        "medium": round(q2, 1),
        "strong": round(q3, 1),
    }


def classify_by_thresholds(success_rate: float, thresholds: dict[str, float]) -> str:
    if success_rate <= thresholds["critical"]:
        return "критическое"
    if success_rate <= thresholds["weak"]:
        return "слабое"
    if success_rate <= thresholds["strong"]:
        return "среднее"
    return "сильное"


def task_correlation_matrix(task_flags: dict[int, list[int]]) -> list[dict]:
    """Пары заданий, которые чаще проваливаются вместе."""
    task_numbers = sorted(task_flags)
    pairs: list[dict] = []
    for i, t1 in enumerate(task_numbers):
        for t2 in task_numbers[i + 1 :]:
            flags1 = task_flags[t1]
            flags2 = task_flags[t2]
            corr = pearson_correlation([float(v) for v in flags1], [float(v) for v in flags2])
            if corr is None:
                continue
            fail_together = sum(1 for a, b in zip(flags1, flags2) if a == 0 and b == 0)
            if fail_together >= 2 and corr >= 0.35:
                pairs.append(
                    {
                        "task_a": t1,
                        "task_b": t2,
                        "correlation": corr,
                        "joint_failures": fail_together,
                    }
                )
    return sorted(pairs, key=lambda item: (-item["joint_failures"], -item["correlation"]))[:12]
