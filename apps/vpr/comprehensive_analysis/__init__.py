"""
Комплексный аналитический профиль ВПР (ФИОКО).

Оркестрирует существующие движки без изменения их логики
и добавляет управленческие срезы: группы, объективность, профиль ОО, рекомендации.
"""

from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
from apps.vpr.comprehensive_analysis.schemas import VprComprehensiveAnalysisResult
from apps.vpr.comprehensive_analysis.service import (
    clear_protocol_analysis_cache,
    get_protocol_analysis,
)

__all__ = [
    "VprComprehensiveAnalysisEngine",
    "VprComprehensiveAnalysisResult",
    "get_protocol_analysis",
    "clear_protocol_analysis_cache",
]
