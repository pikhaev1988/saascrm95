"""NarrativeQualityValidator — проверка пользовательского текста перед HTML/DOCX."""

from __future__ import annotations

import re
from typing import Any

from apps.vpr.evidence.statuses import FORBIDDEN_AUTO_CAUSE_PHRASES
from apps.vpr.validation.consistency import ConsistencyIssue, ConsistencyResult

_LEAK_PATTERNS = [
    re.compile(r"\bSYSTEM_ANALYTICS\b"),
    re.compile(r"\bFIOKO_2026\b"),
    re.compile(r"\bLOCAL_ANALYTICS\b"),
    re.compile(r"evidence_status="),
    re.compile(r"catalog="),
    re.compile(r"classify_mastery"),
    re.compile(r"\bcompletion_percent\b"),
    re.compile(r"journal_gap_ge_2"),
    re.compile(r"anomaly_crossings"),
    re.compile(r"rule_id="),
    re.compile(r"source_metric="),
    re.compile(r"linked_tasks="),
    re.compile(r"EvidenceStatus\."),
    re.compile(r"\bGENERAL_PEAK\b"),
    re.compile(r"boundary_peak_status="),
]

_FACT_PREFIX = re.compile(r"\bFACT:\s", re.I)


class NarrativeQualityValidator:
    def validate(self, report: Any) -> ConsistencyResult:
        errors: list[ConsistencyIssue] = []
        warnings: list[ConsistencyIssue] = []
        blob = _collect_user_text(report)
        for pat in _LEAK_PATTERNS:
            if pat.search(blob):
                errors.append(
                    ConsistencyIssue(
                        code="narrative.technical_leak",
                        severity="error",
                        message=f"technical token in user narrative: {pat.pattern}",
                        actual=pat.pattern,
                    )
                )
        if _FACT_PREFIX.search(blob):
            errors.append(
                ConsistencyIssue(
                    code="narrative.fact_prefix",
                    severity="error",
                    message="FACT: prefix in user-facing narrative",
                )
            )
        low = blob.lower()
        for phrase in FORBIDDEN_AUTO_CAUSE_PHRASES:
            if phrase in low and "возможн" not in low:
                errors.append(
                    ConsistencyIssue(
                        code="narrative.forbidden_auto_cause",
                        severity="error",
                        message=phrase,
                    )
                )
        # KPI: 0% as baseline of missing VPR metric
        for row in getattr(report, "action_plan", None) or []:
            base = str(getattr(row, "baseline_value", "") or "")
            kpi = str(getattr(row, "kpi", "") or "").lower()
            if base.strip() in {"0%", "0"} and any(
                k in kpi for k in ("completion", "выполнен", "группы риска", "качеств")
            ):
                errors.append(
                    ConsistencyIssue(
                        code="kpi.zero_from_missing",
                        severity="error",
                        message="KPI baseline 0/% for a VPR metric without established source",
                        actual={"kpi": kpi, "baseline": base},
                    )
                )
        return ConsistencyResult(ok=not errors, errors=errors, warnings=warnings)


def _collect_user_text(report: Any) -> str:
    chunks: list[str] = []
    for attr in (
        "passport_assessment",
        "gifted_actions",
        "content_pipeline",
        "admin_director",
        "admin_deputy",
        "smo_actions",
        "teacher_actions",
        "method_recommendations",
        "final_conclusion",
        "methodology_basis",
    ):
        val = getattr(report, attr, None)
        if isinstance(val, list):
            chunks.extend(str(x) for x in val)
        elif val:
            chunks.append(str(val))
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
        "method_cycle",
    ):
        cycle = getattr(report, attr, None)
        if cycle is None:
            continue
        for part in ("interpretation", "causes", "org_decisions", "method_decisions", "expected_effect"):
            chunks.extend(str(x) for x in (getattr(cycle, part, None) or []))
    for g in getattr(report, "individual_groups", None) or []:
        chunks.append(str(getattr(g, "characteristic", "") or ""))
    for d in getattr(report, "deficit_items", None) or []:
        chunks.append(str(getattr(d, "impact_results", "") or ""))
        chunks.append(str(getattr(d, "evidence", "") or ""))
    return "\n".join(chunks)
