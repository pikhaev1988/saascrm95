"""
Экспертная предметная интерпретация результатов ВПР (уровень ФИОКО).

Только Rule Engine поверх готовых данных get_protocol_analysis.
Существующие аналитические движки не вызываются и не изменяются.
"""

from apps.vpr.expert_analysis.engine import build_expert_analysis
from apps.vpr.expert_analysis.result import ExpertAnalysisResult

__all__ = ["ExpertAnalysisResult", "build_expert_analysis"]
