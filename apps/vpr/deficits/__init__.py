"""Выявление образовательных дефицитов ВПР (ФИОКО)."""

from apps.vpr.deficits.config import clear_thresholds_cache, load_deficit_thresholds
from apps.vpr.deficits.engine import VprDeficitEngine
from apps.vpr.deficits.result import VprDeficitResult

__all__ = [
    "VprDeficitEngine",
    "VprDeficitResult",
    "load_deficit_thresholds",
    "clear_thresholds_cache",
]
