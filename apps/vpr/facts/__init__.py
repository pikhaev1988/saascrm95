"""Единый слой фактов отчёта ВПР (single source of truth)."""

from apps.vpr.facts.report_facts import VPRReportFacts
from apps.vpr.facts.builder import build_vpr_report_facts
from apps.vpr.facts.task_classification import (
    TaskClassificationResult,
    classify_task,
    classify_tasks,
)

__all__ = [
    "VPRReportFacts",
    "build_vpr_report_facts",
    "TaskClassificationResult",
    "classify_task",
    "classify_tasks",
]
