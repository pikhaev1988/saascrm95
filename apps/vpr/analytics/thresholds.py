"""
Единый источник порогов аналитики ВПР.

SYSTEM_ANALYTICS: значения этапа 2 (не подтверждены PDF ФИОКО 2026 как обязательные).
fioko_2026: пороги из «Рекомендаций… ВПР», 2026 (подтверждённый источник).

НЕ смешивать namespace'ы. НЕ менять SYSTEM числа без отдельного решения.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# Канонический конфиг VPR Analytics.
VPR_THRESHOLDS: dict[str, Any] = {
    # --- SYSTEM_ANALYTICS (этап 2 contract; не переименовывать в «требование ФИОКО») ---
    "deficits": {
        "high": 90.0,
        "sufficient": 75.0,
        "acceptable": 60.0,
        "problem": 40.0,
        "_source": "SYSTEM_ANALYTICS",
    },
    "groups": {
        "high_min": 80.0,
        "medium_min": 50.0,
        "_source": "SYSTEM_ANALYTICS",
    },
    "achievement_cv": {
        "homogeneous_max": 15.0,  # cv < 15
        "moderate_max": 30.0,  # 15 <= cv < 30; else heterogeneous
        "_source": "SYSTEM_ANALYTICS",
    },
    "objectivity": {
        "high_divergence_pct": 40.0,
        "medium_divergence_pct": 20.0,
        "suspicious_high_marks_pct": 80.0,
        "suspicious_avg_share_max": 55.0,
        "_source": "SYSTEM_ANALYTICS",
    },
    "conclusion": {
        "risk_share_local": 0.15,
        "risk_share_mass": 0.40,
        "_source": "SYSTEM_ANALYTICS",
    },
    "planned_results_status": {
        # classify_mastery: те же полосы, что deficits
        "high": 90.0,
        "sufficient": 75.0,
        "acceptable": 60.0,
        "problem": 40.0,
        "_source": "SYSTEM_ANALYTICS",
    },
    "positive_potential": {
        "min_mark_vpr": 4,
        "min_completion_percent": 70.0,
        "_source": "SYSTEM_ANALYTICS",
    },
    # --- FIOKO_2026 (PDF Рекомендации_для_ОО, 2026; §§1,5, стр. 6/17) ---
    "fioko_2026": {
        "_source": "FIOKO_2026",
        "basic": {
            "sufficient_min": 60.0,
            "insufficient_max": 57.0,
            "uncertainty_delta": 3.0,
            # sufficient_min + uncertainty_delta (документированная верхняя граница зоны ±3)
            "uncertainty_upper": 63.0,
        },
        "advanced_high": {
            "sufficient_min": 30.0,
            "insufficient_max": 28.5,
            "uncertainty_delta": 1.5,
            "uncertainty_upper": 31.5,
        },
        "journal_gap_abs_min": 2,
        "groups_sample_min": 10,
        "mark2_negative_dynamics_pp": 10.0,
        "sample": {
            "groups_informative_min": 10,
            "distribution_informative_min": 50,
            "distribution_approximate_min": 20,
            "very_limited_max": 19,
            "high_uncertainty_max": 9,
        },
    },
    # SYSTEM: порог массовой трудности заданий (не требование ФИОКО)
    "system_tasks": {
        "below_50": 50.0,
        "below_50_inclusive": True,  # «успешность ≤ 50%»
        "below_40": 40.0,
        "_source": "SYSTEM_ANALYTICS",
    },
}


def get_vpr_thresholds() -> dict[str, Any]:
    """Копия конфига (защита от мутаций на месте)."""
    return deepcopy(VPR_THRESHOLDS)


def group_thresholds() -> tuple[float, float]:
    g = VPR_THRESHOLDS["groups"]
    return float(g["high_min"]), float(g["medium_min"])


def objectivity_thresholds() -> dict[str, float]:
    return {
        k: float(v)
        for k, v in VPR_THRESHOLDS["objectivity"].items()
        if not str(k).startswith("_")
    }


def achievement_cv_thresholds() -> tuple[float, float]:
    c = VPR_THRESHOLDS["achievement_cv"]
    return float(c["homogeneous_max"]), float(c["moderate_max"])


def conclusion_risk_shares() -> tuple[float, float]:
    c = VPR_THRESHOLDS["conclusion"]
    return float(c["risk_share_local"]), float(c["risk_share_mass"])


def mastery_band_thresholds() -> dict[str, float]:
    return {
        k: float(v)
        for k, v in VPR_THRESHOLDS["planned_results_status"].items()
        if not str(k).startswith("_")
    }


def positive_potential_thresholds() -> tuple[int, float]:
    p = VPR_THRESHOLDS["positive_potential"]
    return int(p["min_mark_vpr"]), float(p["min_completion_percent"])


def fioko_2026_thresholds() -> dict[str, Any]:
    return deepcopy(VPR_THRESHOLDS["fioko_2026"])
