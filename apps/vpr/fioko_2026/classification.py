"""Классификация процента выполнения по порогам FIOKO 2026."""

from __future__ import annotations

from typing import Any, Literal

from apps.vpr.analytics.thresholds import VPR_THRESHOLDS
from apps.vpr.fioko_2026.difficulty import DifficultyCode, is_advanced_or_high

FiokoLevelStatus = Literal["sufficient", "insufficient", "uncertainty", "not_available"]
VisualMarker = Literal["green", "red", "yellow", "none"]

STATUS_TO_MARKER: dict[str, VisualMarker] = {
    "sufficient": "green",
    "insufficient": "red",
    "uncertainty": "yellow",
    "not_available": "none",
}


def fioko_threshold_band(difficulty: DifficultyCode) -> dict[str, float] | None:
    cfg = VPR_THRESHOLDS.get("fioko_2026") or {}
    if difficulty == "basic":
        band = cfg.get("basic") or {}
    elif is_advanced_or_high(difficulty):
        band = cfg.get("advanced_high") or {}
    else:
        return None
    if not band:
        return None
    return {
        "sufficient_min": float(band["sufficient_min"]),
        "insufficient_max": float(band["insufficient_max"]),
        "uncertainty_delta": float(band.get("uncertainty_delta") or 0),
    }


def classify_fioko_level(
    completion_percent: float | None,
    difficulty: DifficultyCode,
) -> dict[str, Any]:
    """
    Классификация без противоречивых статусов:

      if completion < insufficient_max → insufficient
      elif completion < sufficient_min → uncertainty
      else → sufficient

    При difficulty=unknown или completion=None → not_available.
    """
    if completion_percent is None or difficulty == "unknown":
        return {
            "fioko_level_status": "not_available",
            "visual_marker": "none",
            "completion_percent": completion_percent,
            "difficulty": difficulty,
            "band": None,
            "source": "FIOKO_2026",
        }

    band = fioko_threshold_band(difficulty)
    if band is None:
        return {
            "fioko_level_status": "not_available",
            "visual_marker": "none",
            "completion_percent": float(completion_percent),
            "difficulty": difficulty,
            "band": None,
            "source": "FIOKO_2026",
        }

    value = float(completion_percent)
    insufficient_max = band["insufficient_max"]
    sufficient_min = band["sufficient_min"]

    if value < insufficient_max:
        status: FiokoLevelStatus = "insufficient"
    elif value < sufficient_min:
        status = "uncertainty"
    else:
        status = "sufficient"

    return {
        "fioko_level_status": status,
        "visual_marker": STATUS_TO_MARKER[status],
        "completion_percent": value,
        "difficulty": difficulty,
        "band": band,
        "source": "FIOKO_2026",
    }


def classify_sample_quality(
    sample_size: int,
    *,
    context: str = "general",
) -> dict[str, Any]:
    """
    Оценка качества выборки (FIOKO 2026).

    groups: informative >=10
    distribution:
      N>=50 STANDARD/informative
      20–49 LIMITED_SAMPLE/approximate
      10–19 VERY_LIMITED_SAMPLE
      <10 HIGH_UNCERTAINTY
    """
    n = int(sample_size or 0)
    cfg = (VPR_THRESHOLDS.get("fioko_2026") or {}).get("sample") or {}

    if context == "groups":
        min_n = int(cfg.get("groups_informative_min") or 10)
        informative = n >= min_n
        return {
            "sample_size": n,
            "sample_quality": "informative" if informative else "limited",
            "sample_warning": not informative,
            "informational_only": not informative,
            "context": context,
            "threshold_min": min_n,
            "source": "FIOKO_2026",
            "tier": "STANDARD" if informative else "LIMITED_GROUP_SAMPLE",
        }

    if context == "distribution":
        from apps.vpr.analytics.config import distribution_sample_tier

        tier_info = distribution_sample_tier(n)
        quality_map = {
            "STANDARD": "informative",
            "LIMITED_SAMPLE": "approximate",
            "VERY_LIMITED_SAMPLE": "limited",
            "HIGH_UNCERTAINTY": "limited",
        }
        quality = quality_map.get(tier_info["tier"], "limited")
        return {
            "sample_size": n,
            "sample_quality": quality,
            "sample_warning": not tier_info["informative"],
            "informational_only": tier_info["tier"] in {"VERY_LIMITED_SAMPLE", "HIGH_UNCERTAINTY"},
            "context": context,
            "threshold_informative": tier_info["thresholds"]["informative_min"],
            "threshold_approximate": tier_info["thresholds"]["approximate_min"],
            "source": "FIOKO_2026",
            "tier": tier_info["tier"],
            "evidence_status": tier_info["evidence_status"],
            "wording": tier_info["wording"],
        }

    return {
        "sample_size": n,
        "sample_quality": "unknown",
        "sample_warning": False,
        "informational_only": False,
        "context": context,
        "source": "SYSTEM_ENHANCEMENT",
    }
