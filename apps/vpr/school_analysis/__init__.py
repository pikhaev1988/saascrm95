"""
Комплексная аналитика образовательной организации по ВПР.

Агрегирует результаты VprComprehensiveAnalysisEngine по всем протоколам школы.
"""

from apps.vpr.school_analysis.engine import VprSchoolAnalysisEngine
from apps.vpr.school_analysis.schemas import SchoolAnalysisResult

__all__ = [
    "VprSchoolAnalysisEngine",
    "SchoolAnalysisResult",
]
