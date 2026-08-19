"""
NarrativeSanitizer — технические поля не должны попадать в основной текст HTML/DOCX.

Enum и служебные ключи остаются в DTO/JSON/audit.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from apps.vpr.evidence.envelope import hypothesis_wording
from apps.vpr.narrative.labels import USER_LABELS

# Служебные токены, которые нельзя оставлять в управленческом тексте
_TOKEN_REPLACEMENTS = [
    (re.compile(r"\bEDUCATIONAL_DIFFICULTY\b"), USER_LABELS["EDUCATIONAL_DIFFICULTY"]),
    (re.compile(r"\bEDUCATIONAL_DEFICIT\b"), USER_LABELS["EDUCATIONAL_DEFICIT"]),
    (re.compile(r"\bLIMITED_SAMPLE\b"), USER_LABELS["LIMITED_SAMPLE"]),
    (re.compile(r"\bINSUFFICIENT_DATA\b"), USER_LABELS["INSUFFICIENT_DATA"]),
    (re.compile(r"\bNOT_AVAILABLE\b"), USER_LABELS["NOT_AVAILABLE"]),
    (re.compile(r"\bSYSTEM_ANALYTICS\b"), USER_LABELS["SYSTEM_ANALYTICS"]),
    (re.compile(r"\bFIOKO_2026\b"), USER_LABELS["FIOKO_2026"]),
    (re.compile(r"\bLOCAL_ANALYTICS\b"), USER_LABELS["LOCAL_ANALYTICS"]),
    (re.compile(r"\bGENERAL_PEAK\b"), USER_LABELS["GENERAL_PEAK"]),
    (re.compile(r"\bOVERLAPPING_GROUP\b"), USER_LABELS["OVERLAPPING_GROUP"]),
    (re.compile(r"\bHYPOTHESIS\b"), USER_LABELS["HYPOTHESIS"]),
    (re.compile(r"\bINFORMATIVE\b"), USER_LABELS["INFORMATIVE"]),
    (re.compile(r"\bESTABLISHED\b"), USER_LABELS["ESTABLISHED"]),
]

_STRIP_PATTERNS = [
    re.compile(r"evidence_status\s*=\s*\S+", re.I),
    re.compile(r"catalog\s*=\s*\S+", re.I),
    re.compile(r"classify_mastery\b", re.I),
    re.compile(r"\bcompletion_percent\b", re.I),
    re.compile(r"\bjournal_gap_ge_2\b", re.I),
    re.compile(r"\banomaly_crossings\b", re.I),
    re.compile(r"rule_id\s*=\s*\S+", re.I),
    re.compile(r"source_metric\s*=\s*\S+", re.I),
    re.compile(r"linked_tasks\s*=\s*\S+", re.I),
    re.compile(r"boundary_peak_status\s*=\s*\S+", re.I),
    re.compile(r"boundary_source\s*=\s*\S+", re.I),
    re.compile(r"EvidenceStatus\.\w+"),
    re.compile(r"\bfinding\s*=\s*\S+", re.I),
    re.compile(r"\brationale\s*=\s*", re.I),
    re.compile(r"\bmark_2_dynamics_pp\b", re.I),
    re.compile(r"\bmark_2_percent\b", re.I),
    re.compile(r"\bred_share\b", re.I),
    re.compile(r"\bfioko_status\b", re.I),
    re.compile(r"\bboundary_peak_flags\b", re.I),
]

_FACT_PREFIX = re.compile(r"^\s*FACT:\s*", re.I)
_HYP_PREFIX = re.compile(r"^\s*HYPOTHESIS:\s*", re.I)


def sanitize_text(text: str | None) -> str:
    if not text:
        return ""
    out = str(text)
    for pat in _STRIP_PATTERNS:
        out = pat.sub("", out)
    for pat, repl in _TOKEN_REPLACEMENTS:
        out = pat.sub(repl, out)
    out = _FACT_PREFIX.sub("", out)
    out = _HYP_PREFIX.sub("", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    return out.strip()


def sanitize_list(items: Iterable[str] | None) -> list[str]:
    cleaned = []
    for item in items or []:
        text = sanitize_text(item)
        if text:
            cleaned.append(text)
    return cleaned


def as_hypothesis(text: str) -> str:
    return sanitize_text(hypothesis_wording(text))


def sanitize_cycle(cycle: Any) -> None:
    if cycle is None:
        return
    for attr in ("interpretation", "causes", "org_decisions", "method_decisions", "expected_effect"):
        vals = getattr(cycle, attr, None)
        if vals is not None:
            setattr(cycle, attr, sanitize_list(vals))


def sanitize_subject_report(report: Any) -> None:
    """Очистить пользовательские тексты справки (DTO-поля статусов не трогаем)."""
    if report is None:
        return
    for attr in (
        "passport_assessment",
        "gifted_actions",
        "parent_support_actions",
        "attendance_control",
        "content_pipeline",
        "admin_director",
        "admin_deputy",
        "smo_actions",
        "teacher_deficits",
        "teacher_actions",
        "parent_actions",
        "method_recommendations",
        "final_conclusion",
        "system_analytics_notes",
        "fioko_warnings",
    ):
        vals = getattr(report, attr, None)
        if isinstance(vals, list):
            setattr(report, attr, sanitize_list(vals))
    if getattr(report, "methodology_basis", None):
        report.methodology_basis = sanitize_text(report.methodology_basis)

    for attr in (
        "individual_cycle",
        "marks_cycle",
        "objectivity_cycle",
        "scores_cycle",
        "content_cycle",
        "planned_cycle",
        "group_task_cycle",
        "deficits_cycle",
        "admin_cycle",
        "smo_cycle",
        "teachers_cycle",
        "parents_cycle",
        "method_cycle",
    ):
        sanitize_cycle(getattr(report, attr, None))

    for g in getattr(report, "individual_groups", None) or []:
        if getattr(g, "characteristic", None):
            g.characteristic = sanitize_text(g.characteristic)
        if getattr(g, "actions", None):
            g.actions = sanitize_list(g.actions)

    for d in getattr(report, "deficit_items", None) or []:
        for field in ("impact_results", "impact_quality", "impact_program", "evidence"):
            val = getattr(d, field, None)
            if val:
                setattr(d, field, sanitize_text(val))
        if getattr(d, "management_decisions", None):
            d.management_decisions = sanitize_list(d.management_decisions)

    for insight in getattr(report, "group_task_insights", None) or []:
        if getattr(insight, "explanation", None):
            insight.explanation = sanitize_text(insight.explanation)
        if getattr(insight, "evidence", None):
            insight.evidence = sanitize_list(insight.evidence)

    for line in getattr(report, "content_lines", None) or []:
        for field in ("typical_errors", "probable_causes", "method_changes"):
            vals = getattr(line, field, None)
            if vals:
                setattr(line, field, sanitize_list(vals))

    for row in getattr(report, "planned_results", None) or []:
        for field in ("explanation", "subject_actions", "meta_actions", "content_adjustments", "evidence"):
            val = getattr(row, field, None)
            if val:
                setattr(row, field, sanitize_text(val))

    for row in getattr(report, "action_plan", None) or []:
        for field in (
            "action",
            "problem",
            "expected_result",
            "efficiency_indicator",
            "kpi",
            "baseline_value",
            "target_value",
        ):
            val = getattr(row, field, None)
            if val:
                setattr(row, field, sanitize_text(val))

    # Management recommendations (dict payloads from FIOKO layer)
    cleaned_recs = []
    for rec in getattr(report, "management_recommendations", None) or []:
        if not isinstance(rec, dict):
            cleaned_recs.append(rec)
            continue
        item = dict(rec)
        for field in (
            "problem",
            "evidence",
            "action",
            "responsible",
            "deadline",
            "control_metric",
            "expected_result",
        ):
            if field in item and item[field]:
                item[field] = sanitize_text(str(item[field]))
        if item.get("possible_causes"):
            item["possible_causes"] = sanitize_list(item.get("possible_causes"))
        cleaned_recs.append(item)
    if hasattr(report, "management_recommendations"):
        report.management_recommendations = cleaned_recs
