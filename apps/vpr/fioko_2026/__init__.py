"""
FIOKO 2026 compliance layer for VPR.

Adds confirmed methodological rules from:
«Рекомендации по проведению анализа результатов
Всероссийских проверочных работ», 2026
поверх существующего SYSTEM analytics layer.

Не заменяет Metric Contract (FULL/PARTIAL/ZERO) и SYSTEM thresholds.
"""

from apps.vpr.fioko_2026.engine import build_fioko_2026_layer
from apps.vpr.fioko_2026.mapping import FIOKO_ANALYSIS_DIRECTION, FIOKO_DIRECTION_TO_SECTIONS
from apps.vpr.fioko_2026.sample import GROUP_SAMPLE_MIN, group_sample_flags
from apps.vpr.fioko_2026.schemas import VprFioko2026Layer
from apps.vpr.fioko_2026.source import FIOKO_2026_SOURCE, SOURCE_SYSTEM

__all__ = [
    "FIOKO_2026_SOURCE",
    "SOURCE_SYSTEM",
    "FIOKO_ANALYSIS_DIRECTION",
    "FIOKO_DIRECTION_TO_SECTIONS",
    "GROUP_SAMPLE_MIN",
    "VprFioko2026Layer",
    "build_fioko_2026_layer",
    "group_sample_flags",
]
