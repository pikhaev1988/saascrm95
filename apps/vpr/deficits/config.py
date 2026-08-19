"""Конфигурация уровней освоения и приоритетов дефицитов ВПР (ФИОКО)."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "thresholds.json"


@dataclass(frozen=True, slots=True)
class MasteryLevel:
    code: str
    label: str
    min_percent: float
    max_percent: float


@dataclass(frozen=True, slots=True)
class DeficitThresholds:
    levels: tuple[MasteryLevel, ...]
    priority_by_level: dict[str, str]
    risk_by_level: dict[str, str]
    problem_levels: tuple[str, ...]
    critical_levels: tuple[str, ...]

    def classify(self, completion_percent: float | None) -> MasteryLevel:
        if completion_percent is None:
            # нет данных — считаем критическим дефицитом освоения
            return next(level for level in self.levels if level.code == "critical")
        value = float(completion_percent)
        for level in self.levels:
            if level.min_percent <= value <= level.max_percent:
                return level
        # ниже нуля / выше 100 — ближайшая граница
        if value < 0:
            return next(level for level in self.levels if level.code == "critical")
        return next(level for level in self.levels if level.code == "high")

    def priority_for(self, level_code: str) -> str:
        return self.priority_by_level.get(level_code, "medium")

    def risk_for(self, level_code: str) -> str:
        return self.risk_by_level.get(level_code, "medium")

    def is_problem(self, level_code: str) -> bool:
        return level_code in self.problem_levels

    def is_critical(self, level_code: str) -> bool:
        return level_code in self.critical_levels


def _parse_config(raw: dict[str, Any]) -> DeficitThresholds:
    levels = tuple(
        MasteryLevel(
            code=str(item["code"]),
            label=str(item.get("label") or item["code"]),
            min_percent=float(item["min_percent"]),
            max_percent=float(item["max_percent"]),
        )
        for item in raw.get("mastery_levels", [])
    )
    if not levels:
        raise ValueError("VPR deficit config: mastery_levels is empty")
    return DeficitThresholds(
        levels=levels,
        priority_by_level={str(k): str(v) for k, v in (raw.get("priority_by_level") or {}).items()},
        risk_by_level={str(k): str(v) for k, v in (raw.get("risk_by_level") or {}).items()},
        problem_levels=tuple(raw.get("problem_levels") or ("problem", "critical")),
        critical_levels=tuple(raw.get("critical_levels") or ("critical",)),
    )


@lru_cache(maxsize=4)
def load_deficit_thresholds(config_path: str | None = None) -> DeficitThresholds:
    """
    Загрузить пороги из JSON.
    Можно переопределить через settings.VPR_DEFICIT_THRESHOLDS_PATH
    или settings.VPR_DEFICIT_THRESHOLDS (dict).
    """
    override = getattr(settings, "VPR_DEFICIT_THRESHOLDS", None)
    if isinstance(override, dict) and override:
        return _parse_config(deepcopy(override))

    path = Path(
        config_path
        or getattr(settings, "VPR_DEFICIT_THRESHOLDS_PATH", "")
        or DEFAULT_CONFIG_PATH
    )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _parse_config(raw)


def clear_thresholds_cache() -> None:
    load_deficit_thresholds.cache_clear()
