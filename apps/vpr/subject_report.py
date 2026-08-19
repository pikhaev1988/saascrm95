"""
Презентационный слой «Аналитика предмета» ВПР.

Справка формируется по методологии ФИОКО
(см. apps.vpr.expert_analysis.fioko_report).
Движки и расчёты не вызываются напрямую.
"""

from __future__ import annotations

from apps.vpr.expert_analysis.fioko_report import (
    AnalyticCycle,
    ContentLineInsight,
    DeficitInsight,
    GroupInsight,
    GroupTaskInsight,
    IomBlock,
    KpiItem,
    MarkRow,
    PlanRow,
    PlannedResultRow,
    ScoreRow,
    SubjectReport,
    TaskPerformanceRow,
    build_fioko_report,
)

__all__ = [
    "AnalyticCycle",
    "ContentLineInsight",
    "DeficitInsight",
    "GroupInsight",
    "GroupTaskInsight",
    "IomBlock",
    "KpiItem",
    "MarkRow",
    "PlanRow",
    "PlannedResultRow",
    "ScoreRow",
    "SubjectReport",
    "TaskPerformanceRow",
    "build_subject_report",
]


def build_subject_report(analysis, protocol) -> SubjectReport:
    """Собрать аналитическую справку предмета в структуре ФИОКО (16 разделов)."""
    return build_fioko_report(analysis, protocol)
