"""Чистые статистические функции для аналитики ВПР."""

from __future__ import annotations

import math
from collections import Counter
from typing import Sequence


Number = int | float


def to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_mean(values: Sequence[Number]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 4)


def safe_median(values: Sequence[Number]) -> float | None:
    nums = sorted(float(v) for v in values if v is not None)
    if not nums:
        return None
    n = len(nums)
    mid = n // 2
    if n % 2:
        return round(nums[mid], 4)
    return round((nums[mid - 1] + nums[mid]) / 2, 4)


def safe_mode(values: Sequence[Number]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    counts = Counter(nums)
    max_freq = max(counts.values())
    if max_freq == 1 and len(counts) == len(nums):
        # все уникальные — моды нет в узком смысле; берём наиболее частое (каждое по 1)
        # для отметок/баллов возвращаем самое частое значение с max_freq
        pass
    modes = [value for value, freq in counts.items() if freq == max_freq]
    # при нескольких модах — наименьшая (стабильный выбор)
    return round(min(modes), 4)


def population_stdev(values: Sequence[Number]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if len(nums) < 2:
        return 0.0 if len(nums) == 1 else None
    mean = sum(nums) / len(nums)
    variance = sum((x - mean) ** 2 for x in nums) / len(nums)
    return round(math.sqrt(variance), 4)


def coefficient_of_variation(values: Sequence[Number]) -> float | None:
    """Коэффициент вариации в процентах."""
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    mean = sum(nums) / len(nums)
    if mean == 0:
        return None
    stdev = population_stdev(nums)
    if stdev is None:
        return None
    return round((stdev / abs(mean)) * 100, 4)


def percent(part: Number, whole: Number, *, digits: int = 2) -> float | None:
    whole_f = float(whole)
    if whole_f == 0:
        return None
    return round((float(part) / whole_f) * 100, digits)


# Веса отметок для СОУ (степень обученности учащихся) по формуле Симонова.
SOU_MARK_WEIGHTS: dict[int, int] = {5: 100, 4: 64, 3: 36, 2: 16, 1: 7}


def degree_of_learning(marks: Sequence[Number], *, digits: int = 2) -> float | None:
    """
    СОУ = (n5·100 + n4·64 + n3·36 + n2·16 [+ n1·7]) / N.

    N — число учтённых отметок; неизвестные отметки игнорируются.
    """
    weighted = 0
    total = 0
    for raw in marks:
        if raw is None:
            continue
        try:
            mark = int(raw)
        except (TypeError, ValueError):
            continue
        weight = SOU_MARK_WEIGHTS.get(mark)
        if weight is None:
            continue
        weighted += weight
        total += 1
    if total == 0:
        return None
    return round(weighted / total, digits)


def distribution_counts(values: Sequence[Number]) -> dict[str, int]:
    """Подсчёт частот с ключами-строками для JSON-стабильности."""
    counts: dict[str, int] = {}
    for value in values:
        if value is None:
            continue
        if isinstance(value, float) and value.is_integer():
            key = str(int(value))
        else:
            key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: _sort_key(item[0])))


def _sort_key(raw: str):
    try:
        return (0, float(raw))
    except ValueError:
        return (1, raw)
