"""
Централизованный реестр методологических правил 2026.

Разделение источников:
  FIOKO_2026_RULES
  SYSTEM_ANALYTICS_RULES
  LOCAL_ANALYTICS_RULES

Не смешивать. Числовые значения берутся из VPR_THRESHOLDS (единый runtime-источник).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from apps.vpr.analytics.thresholds import VPR_THRESHOLDS


def _rule(
    *,
    name: str,
    value: Any,
    source: str,
    description: str,
    scope: str,
    effective_year: int = 2026,
) -> dict[str, Any]:
    return {
        "name": name,
        "value": value,
        "source": source,
        "description": description,
        "scope": scope,
        "effective_year": effective_year,
    }


def _build_system_rules() -> dict[str, dict[str, Any]]:
    t = VPR_THRESHOLDS
    return {
        "groups.high_min": _rule(
            name="groups.high_min",
            value=t["groups"]["high_min"],
            source="SYSTEM_ANALYTICS",
            description="Нижняя граница группы высокого уровня по completion_percent",
            scope="participant_groups",
        ),
        "groups.medium_min": _rule(
            name="groups.medium_min",
            value=t["groups"]["medium_min"],
            source="SYSTEM_ANALYTICS",
            description="Нижняя граница стабильной группы по completion_percent",
            scope="participant_groups",
        ),
        "deficits.bands": _rule(
            name="deficits.bands",
            value={k: v for k, v in t["deficits"].items() if not str(k).startswith("_")},
            source="SYSTEM_ANALYTICS",
            description="Полосы mastery 90/75/60/40",
            scope="deficits_mastery",
        ),
        "achievement.cv": _rule(
            name="achievement.cv",
            value={k: v for k, v in t["achievement_cv"].items() if not str(k).startswith("_")},
            source="SYSTEM_ANALYTICS",
            description="CV-полосы однородности",
            scope="achievement",
        ),
        "positive_potential": _rule(
            name="positive_potential",
            value={
                k: v for k, v in t["positive_potential"].items() if not str(k).startswith("_")
            },
            source="SYSTEM_ANALYTICS",
            description="Дополнительный признак положительного потенциала",
            scope="participant_groups",
        ),
        "tasks.below_50": _rule(
            name="tasks.below_50",
            value=50.0,
            source="SYSTEM_ANALYTICS",
            description="Порог массового затруднения по заданию (успешность ≤ 50%, SYSTEM)",
            scope="task_classification",
        ),
        "tasks.below_40": _rule(
            name="tasks.below_40",
            value=t["deficits"]["problem"],
            source="SYSTEM_ANALYTICS",
            description="Порог критического выполнения задания (= deficits.problem)",
            scope="task_classification",
        ),
        "tasks.critical_max": _rule(
            name="tasks.critical_max",
            value=t["deficits"]["problem"],
            source="SYSTEM_ANALYTICS",
            description="Верхняя граница CRITICAL по completion",
            scope="task_classification",
        ),
        "tasks.risk_max": _rule(
            name="tasks.risk_max",
            value=t["deficits"]["acceptable"],
            source="SYSTEM_ANALYTICS",
            description="Верхняя граница RISK по completion",
            scope="task_classification",
        ),
        "tasks.normal_max": _rule(
            name="tasks.normal_max",
            value=t["deficits"]["sufficient"],
            source="SYSTEM_ANALYTICS",
            description="Верхняя граница NORMAL по completion",
            scope="task_classification",
        ),
    }


def _build_fioko_rules() -> dict[str, dict[str, Any]]:
    f = VPR_THRESHOLDS["fioko_2026"]
    return {
        "basic.sufficient_min": _rule(
            name="basic.sufficient_min",
            value=f["basic"]["sufficient_min"],
            source="FIOKO_2026",
            description="Достаточный уровень базовых заданий (≥60%)",
            scope="task_classification",
        ),
        "basic.insufficient_max": _rule(
            name="basic.insufficient_max",
            value=f["basic"]["insufficient_max"],
            source="FIOKO_2026",
            description="Недостаточный уровень базовых заданий (≤57%)",
            scope="task_classification",
        ),
        "advanced.sufficient_min": _rule(
            name="advanced.sufficient_min",
            value=f["advanced_high"]["sufficient_min"],
            source="FIOKO_2026",
            description="Достаточный уровень повышенных/высоких заданий (≥30%)",
            scope="task_classification",
        ),
        "journal_gap_abs_min": _rule(
            name="journal_gap_abs_min",
            value=f["journal_gap_abs_min"],
            source="FIOKO_2026",
            description="Минимальный абсолютный разрыв ВПР/журнал для маркера",
            scope="journal_gap",
        ),
        "groups_sample_min": _rule(
            name="groups_sample_min",
            value=f.get("groups_sample_min") or f["sample"]["groups_informative_min"],
            source="FIOKO_2026",
            description="Минимум участников для информативного группового анализа",
            scope="groups_sample",
        ),
    }


def _build_local_rules() -> dict[str, dict[str, Any]]:
    return {
        "group_anomaly_pp": _rule(
            name="group_anomaly_pp",
            value=5.0,
            source="LOCAL_ANALYTICS",
            description="Порог аномалии: нижняя отметка превосходит верхнюю (п.п.)",
            scope="fioko_mark_groups",
        ),
        "hard_for_all_max_pct": _rule(
            name="hard_for_all_max_pct",
            value=40.0,
            source="LOCAL_ANALYTICS",
            description="Эвристика «трудно для всех» по % выполнения",
            scope="fioko_mark_groups",
        ),
        "easiest_min_pct": _rule(
            name="easiest_min_pct",
            value=80.0,
            source="LOCAL_ANALYTICS",
            description="Эвристика «наиболее доступные» по % выполнения",
            scope="fioko_mark_groups",
        ),
    }


FIOKO_2026_RULES: dict[str, dict[str, Any]] = _build_fioko_rules()
SYSTEM_ANALYTICS_RULES: dict[str, dict[str, Any]] = _build_system_rules()
LOCAL_ANALYTICS_RULES: dict[str, dict[str, Any]] = _build_local_rules()


def get_methodology_registry() -> dict[str, Any]:
    return {
        "FIOKO_2026_RULES": deepcopy(FIOKO_2026_RULES),
        "SYSTEM_ANALYTICS_RULES": deepcopy(SYSTEM_ANALYTICS_RULES),
        "LOCAL_ANALYTICS_RULES": deepcopy(LOCAL_ANALYTICS_RULES),
        "runtime_thresholds_ref": "apps.vpr.analytics.thresholds.VPR_THRESHOLDS",
    }


def rule_value(registry: dict[str, dict[str, Any]], name: str, default: Any = None) -> Any:
    item = registry.get(name)
    if not item:
        return default
    return item.get("value", default)
