"""
VPR_ANALYTICS_CONFIG — единый конфиг расчётов Stage 10.

Алиас над VPR_THRESHOLDS с явными FIOKO/SYSTEM блоками и
вычисляемыми границами зон неопределённости.

Запрещены hardcoded 57/60/63/28.5/30/31.5/50 вне этого модуля
и потребителей, читающих конфиг.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from apps.vpr.analytics.thresholds import VPR_THRESHOLDS, get_vpr_thresholds

# Канонический публичный алиас Stage 10
VPR_ANALYTICS_CONFIG: dict[str, Any] = VPR_THRESHOLDS


def get_vpr_analytics_config() -> dict[str, Any]:
    cfg = get_vpr_thresholds()
    fioko = cfg.setdefault("fioko_2026", {})
    basic = fioko.setdefault("basic", {})
    adv = fioko.setdefault("advanced_high", {})
    # Явные верхние границы зон ±δ (для отчётов/тестов; не отдельный статус)
    if "uncertainty_upper" not in basic:
        basic["uncertainty_upper"] = float(basic["sufficient_min"]) + float(
            basic.get("uncertainty_delta") or 0
        )
    if "uncertainty_upper" not in adv:
        adv["uncertainty_upper"] = float(adv["sufficient_min"]) + float(
            adv.get("uncertainty_delta") or 0
        )
    system = cfg.setdefault("system_tasks", {})
    system.setdefault("below_50", 50.0)
    system.setdefault("below_50_inclusive", True)  # успешность ≤ 50%
    system.setdefault("below_40", 40.0)
    system.setdefault("_source", "SYSTEM_ANALYTICS")
    sample = fioko.setdefault("sample", {})
    sample.setdefault("distribution_informative_min", 50)
    sample.setdefault("distribution_approximate_min", 20)
    sample.setdefault("groups_informative_min", 10)
    sample.setdefault("very_limited_max", 19)  # 10..19 → VERY_LIMITED
    sample.setdefault("high_uncertainty_max", 9)  # <10
    return cfg


def below_50_threshold() -> tuple[float, bool]:
    """Порог SYSTEM «успешность ≤ / < 50%». Returns (threshold, inclusive)."""
    cfg = get_vpr_analytics_config()
    system = cfg.get("system_tasks") or {}
    # fallback на methodology rule default
    thr = float(system.get("below_50") or 50.0)
    inclusive = bool(system.get("below_50_inclusive", True))
    return thr, inclusive


def is_below_threshold(completion_percent: float | None, threshold: float, *, inclusive: bool) -> bool:
    if completion_percent is None:
        return False
    value = float(completion_percent)
    return value <= threshold if inclusive else value < threshold


def fioko_basic_bounds() -> dict[str, float]:
    cfg = get_vpr_analytics_config()["fioko_2026"]["basic"]
    return {
        "insufficient_max": float(cfg["insufficient_max"]),
        "sufficient_min": float(cfg["sufficient_min"]),
        "uncertainty_delta": float(cfg.get("uncertainty_delta") or 0),
        "uncertainty_upper": float(cfg["uncertainty_upper"]),
    }


def fioko_advanced_bounds() -> dict[str, float]:
    cfg = get_vpr_analytics_config()["fioko_2026"]["advanced_high"]
    return {
        "insufficient_max": float(cfg["insufficient_max"]),
        "sufficient_min": float(cfg["sufficient_min"]),
        "uncertainty_delta": float(cfg.get("uncertainty_delta") or 0),
        "uncertainty_upper": float(cfg["uncertainty_upper"]),
    }


def distribution_sample_tier(n: int) -> dict[str, Any]:
    """
    N >= 50 → STANDARD (informative)
    20 <= N < 50 → LIMITED_SAMPLE
    10 <= N < 20 → VERY_LIMITED_SAMPLE
    N < 10 → HIGH_UNCERTAINTY
    """
    cfg = get_vpr_analytics_config()["fioko_2026"]["sample"]
    informative = int(cfg["distribution_informative_min"])
    approximate = int(cfg["distribution_approximate_min"])
    very_lim = int(cfg.get("very_limited_max") or 19)
    high_unc = int(cfg.get("high_uncertainty_max") or 9)
    n = int(n or 0)
    if n >= informative:
        tier = "STANDARD"
        status = "INFORMATIVE"
    elif n >= approximate:
        tier = "LIMITED_SAMPLE"
        status = "LIMITED_SAMPLE"
    elif n >= high_unc + 1:  # 10..19
        tier = "VERY_LIMITED_SAMPLE"
        status = "LIMITED_SAMPLE"
    else:
        tier = "HIGH_UNCERTAINTY"
        status = "LIMITED_SAMPLE"
    wording = None
    if n < informative:
        wording = (
            f"Выборка составляет {n} участников и находится ниже "
            f"рекомендуемого ФИОКО объёма {informative} участников для информативного "
            f"анализа распределения первичных баллов."
        )
    return {
        "n": n,
        "tier": tier,
        "evidence_status": status,
        "source": "FIOKO_2026",
        "informative": n >= informative,
        "wording": wording,
        "thresholds": {
            "informative_min": informative,
            "approximate_min": approximate,
            "very_limited_max": very_lim,
            "high_uncertainty_max": high_unc,
        },
    }
