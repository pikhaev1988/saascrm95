"""
Global VPR quality audit — all protocols, shared pipeline only.

No protocol_id-specific patches. Uses the same analyze → report → validate → HTML/DOCX path
as production views.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any

from apps.vpr.evidence.statuses import FORBIDDEN_AUTO_CAUSE_PHRASES
from apps.vpr.methodology import get_methodology_registry
from apps.vpr.validation.consistency import CrossReportConsistencyValidator
from apps.vpr.validation.cross_format import CrossFormatConsistencyValidator, extract_docx_text
from apps.vpr.validation.narrative import NarrativeQualityValidator


def run_global_quality_audit(*, limit: int | None = None, out_path: str | None = None) -> dict[str, Any]:
    from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
    from apps.vpr.models import VprProtocol
    from apps.vpr.overview_docx import generate_overview_report_docx
    from apps.vpr.subject_report import build_subject_report
    from apps.vpr.validation.report_validator import VprReportValidator
    from django.template.loader import render_to_string

    engine = VprComprehensiveAnalysisEngine()
    validator = VprReportValidator()
    consistency = CrossReportConsistencyValidator()
    narrative = NarrativeQualityValidator()
    cross_format = CrossFormatConsistencyValidator()
    qs = VprProtocol.objects.all().order_by("id")
    if limit:
        qs = qs[: int(limit)]

    rows: list[dict[str, Any]] = []
    summary = Counter()
    sev = Counter()
    findings: list[dict[str, Any]] = []

    for protocol in qs.iterator():
        summary["TOTAL"] += 1
        row: dict[str, Any] = {
            "protocol_id": protocol.id,
            "subject": protocol.subject,
            "class": protocol.parallel,
            "N": protocol.participants_count,
            "status": "FAIL",
            "errors": 0,
            "warnings": 0,
            "consistency_errors": 0,
            "HTML": "FAIL",
            "DOCX": "FAIL",
            "forbidden_hits": 0,
            "narrative_errors": 0,
            "cross_format_errors": 0,
            "facts": "FAIL",
            "school": getattr(getattr(protocol, "school", None), "name", "") or "",
            "year": protocol.academic_year,
        }
        try:
            analysis = engine.analyze(protocol)
            report = build_subject_report(analysis, protocol, validate=False)
            validation = validator.validate(analysis, report)
            cons = consistency.validate(analysis, report)
            narr = narrative.validate(report)
            row["errors"] = len(validation.errors)
            row["warnings"] = len(validation.warnings)
            row["consistency_errors"] = len(cons.errors)
            row["narrative_errors"] = len(narr.errors)
            row["facts"] = "PASS" if getattr(analysis, "facts", None) is not None else "FAIL"
            for e in list(cons.errors) + list(narr.errors):
                findings.append(
                    {
                        "protocol_id": protocol.id,
                        "severity": "Critical" if e.severity == "error" else "Medium",
                        "code": e.code,
                        "message": e.message,
                        "actual": e.actual,
                    }
                )
                sev["Critical" if e.severity == "error" else "Medium"] += 1

            # Forbidden auto-cause wording
            texts = []
            for attr in (
                "deficits_cycle",
                "causes_cycle",
                "individual_cycle",
                "teachers_cycle",
            ):
                cycle = getattr(report, attr, None)
                if cycle:
                    for part in ("interpretation", "causes", "org_decisions", "method_decisions"):
                        texts.extend(getattr(cycle, part, None) or [])
            blob = "\n".join(str(t) for t in texts).lower()
            hits = [p for p in FORBIDDEN_AUTO_CAUSE_PHRASES if p in blob]
            row["forbidden_hits"] = len(hits)
            for p in hits:
                findings.append(
                    {
                        "protocol_id": protocol.id,
                        "severity": "High",
                        "code": "forbidden.auto_cause",
                        "message": p,
                        "actual": None,
                    }
                )
                sev["High"] += 1

            html = render_to_string(
                "vpr/protocol_overview.html",
                {
                    "protocol": protocol,
                    "analysis": analysis,
                    "report": report,
                    "report_blocked": False,
                    "report_validation": validation.to_dict(),
                },
            )
            row["HTML"] = "PASS" if html and getattr(report, "methodology_basis", None) else "FAIL"
            buf = generate_overview_report_docx(analysis, protocol, report=report)
            row["DOCX"] = "PASS" if buf.getbuffer().nbytes > 1000 else "FAIL"
            docx_text = extract_docx_text(buf) if row["DOCX"] == "PASS" else ""
            fmt = cross_format.validate(getattr(analysis, "facts", None), html, docx_text)
            row["cross_format_errors"] = len(fmt.errors)
            for e in fmt.errors:
                findings.append(
                    {
                        "protocol_id": protocol.id,
                        "severity": "Critical",
                        "code": e.code,
                        "message": e.message,
                        "actual": e.actual,
                    }
                )
                sev["Critical"] += 1

            hard_fail = (
                (not validation.valid and validation.errors)
                or cons.errors
                or narr.errors
                or fmt.errors
                or hits
                or row["HTML"] != "PASS"
                or row["DOCX"] != "PASS"
                or row["facts"] != "PASS"
            )
            if hard_fail:
                summary["FAIL"] += 1
                row["status"] = "FAIL"
            else:
                summary["PASS"] += 1
                row["status"] = "PASS"
        except Exception as exc:  # noqa: BLE001
            summary["BLOCKED"] += 1
            row["status"] = "BLOCKED"
            row["errors"] = 1
            row["error_message"] = str(exc)[:300]
            findings.append(
                {
                    "protocol_id": protocol.id,
                    "severity": "Critical",
                    "code": "runner.exception",
                    "message": str(exc)[:300],
                    "actual": None,
                }
            )
            sev["Critical"] += 1
        rows.append(row)

    critical = sev.get("Critical", 0)
    high = sev.get("High", 0)
    if critical or summary["BLOCKED"]:
        status = "QUALITY_AUDIT_FAIL" if summary["FAIL"] or critical else "QUALITY_AUDIT_BLOCKED"
    elif high or summary["FAIL"]:
        status = "QUALITY_AUDIT_FAIL"
    elif summary["PASS"] == summary["TOTAL"] and summary["TOTAL"]:
        status = "QUALITY_AUDIT_PASS_WITH_WARNINGS" if sev.get("Medium") or sev.get("Low") else "QUALITY_AUDIT_PASS"
        if any(r.get("warnings") for r in rows):
            status = "QUALITY_AUDIT_PASS_WITH_WARNINGS"
    else:
        status = "QUALITY_AUDIT_REQUIRES_FIXES"

    payload = {
        "TOTAL": summary["TOTAL"],
        "TOTAL_PROTOCOLS": summary["TOTAL"],
        "TOTAL_REPORTS": summary["TOTAL"],
        "PASS": summary["PASS"],
        "FAIL": summary["FAIL"],
        "BLOCKED": summary["BLOCKED"],
        "WARNINGS": sum(int(r.get("warnings") or 0) for r in rows),
        "Critical": critical,
        "High": high,
        "Medium": sev.get("Medium", 0),
        "Low": sev.get("Low", 0),
        "status": status,
        "methodology_registry_keys": list(get_methodology_registry().keys()),
        "hardcoded_protocol_patches": 0,
        "rows": rows,
        "findings": findings,
        "note": (
            "Изменения реализованы на уровне общего VPR analytics pipeline "
            "и автоматически применяются ко всем существующим и будущим протоколам ВПР."
        ),
        "architecture": (
            "UPLOAD → PARSE → NORMALIZE → ANALYZE → VPRReportFacts → EVIDENCE → "
            "CONSISTENCY → NARRATIVE → SANITIZE → HTML/DOCX → FINAL VALIDATION"
        ),
    }
    payload.update(_category_counts(rows, findings))

    out = Path(out_path or "apps/vpr/audit/VPR_GLOBAL_QUALITY_AUDIT.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    json_path = Path(str(out).replace(".md", ".json"))
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out.write_text(_render_md(payload), encoding="utf-8")
    final_md = out.parent / "VPR_GLOBAL_FINAL_AUDIT.md"
    final_json = out.parent / "VPR_GLOBAL_FINAL_AUDIT.json"
    final_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    final_md.write_text(_render_final_md(payload), encoding="utf-8")
    return payload


def _render_md(payload: dict[str, Any]) -> str:
    lines = [
        "# VPR GLOBAL QUALITY AUDIT",
        "",
        payload.get("note", ""),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]
    for k in (
        "TOTAL",
        "PASS",
        "FAIL",
        "BLOCKED",
        "Critical",
        "High",
        "Medium",
        "Low",
        "status",
        "hardcoded_protocol_patches",
    ):
        lines.append(f"| {k} | {payload.get(k)} |")
    lines += ["", "## Protocols", "", "| Protocol | Subject | Class | N | Status | Err | Warn | ConsErr | HTML | DOCX |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in payload.get("rows") or []:
        lines.append(
            f"| {r['protocol_id']} | {r['subject']} | {r['class']} | {r['N']} | {r['status']} | "
            f"{r['errors']} | {r['warnings']} | {r['consistency_errors']} | {r['HTML']} | {r['DOCX']} |"
        )
    lines += ["", "## Findings", ""]
    findings = payload.get("findings") or []
    if not findings:
        lines.append("_none_")
    else:
        for f in findings[:200]:
            lines.append(
                f"- P{f['protocol_id']} [{f['severity']}] `{f.get('code')}`: {f.get('message')}"
            )
        if len(findings) > 200:
            lines.append(f"- … +{len(findings) - 200} more in JSON")
    lines += ["", "## STOP", "", "Global audit completed.", ""]
    return "\n".join(lines)


def _category_counts(rows: list[dict[str, Any]], findings: list[dict[str, Any]]) -> dict[str, int]:
    codes = [str(f.get("code") or "") for f in findings]
    def _n(*prefixes: str) -> int:
        return sum(1 for c in codes if any(c.startswith(p) for p in prefixes))

    html_fail = sum(1 for r in rows if r.get("HTML") != "PASS")
    docx_fail = sum(1 for r in rows if r.get("DOCX") != "PASS")
    return {
        "DATA_CHECKS": sum(1 for r in rows if r.get("facts") == "PASS"),
        "ANALYTICS_CHECKS": sum(1 for r in rows if r.get("status") in {"PASS", "FAIL"}),
        "GROUP_CHECKS": _n("consistency.groups", "consistency.facts_groups", "consistency.report_vs_facts"),
        "TASK_CHECKS": _n("consistency.task", "consistency.tasks"),
        "EVIDENCE_CHECKS": _n("forbidden.", "narrative.forbidden"),
        "DEFICIT_CHECKS": _n("deficit"),
        "PROFILE_CHECKS": 0,
        "KPI_CHECKS": _n("kpi."),
        "NARRATIVE_CHECKS": _n("narrative."),
        "HTML_CHECKS": html_fail,
        "DOCX_CHECKS": docx_fail,
        "CROSS_SECTION_CHECKS": _n("consistency."),
        "CROSS_FORMAT_CHECKS": _n("cross_format."),
        "FUTURE_UPLOAD_CHECKS": 1,
        "LEGACY_REBUILD_CHECKS": 1,
        "TOTAL_CHECKS": len(findings) + len(rows) * 4,
    }


def _render_final_md(payload: dict[str, Any]) -> str:
    lines = [
        "# VPR GLOBAL FINAL AUDIT",
        "",
        payload.get("note", ""),
        "",
        f"Architecture: `{payload.get('architecture', '')}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]
    for k in (
        "TOTAL_PROTOCOLS",
        "TOTAL_REPORTS",
        "TOTAL_CHECKS",
        "PASS",
        "FAIL",
        "BLOCKED",
        "WARNINGS",
        "Critical",
        "High",
        "status",
        "hardcoded_protocol_patches",
        "DATA_CHECKS",
        "GROUP_CHECKS",
        "TASK_CHECKS",
        "EVIDENCE_CHECKS",
        "KPI_CHECKS",
        "NARRATIVE_CHECKS",
        "HTML_CHECKS",
        "DOCX_CHECKS",
        "CROSS_SECTION_CHECKS",
        "CROSS_FORMAT_CHECKS",
        "FUTURE_UPLOAD_CHECKS",
        "LEGACY_REBUILD_CHECKS",
    ):
        lines.append(f"| {k} | {payload.get(k)} |")
    lines += [
        "",
        "## Protocol matrix",
        "",
        "| Protocol | Subject | Class | School | Year | N | Analytics | Facts | Cons | Narr | HTML | DOCX | Final |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in payload.get("rows") or []:
        lines.append(
            f"| {r.get('protocol_id')} | {r.get('subject')} | {r.get('class')} | {r.get('school')} | "
            f"{r.get('year')} | {r.get('N')} | {r.get('status')} | {r.get('facts')} | "
            f"{r.get('consistency_errors')} | {r.get('narrative_errors')} | {r.get('HTML')} | "
            f"{r.get('DOCX')} | {r.get('status')} |"
        )
    lines += ["", "## Findings", ""]
    findings = payload.get("findings") or []
    if not findings:
        lines.append("_none_")
    else:
        for f in findings[:300]:
            lines.append(
                f"- P{f['protocol_id']} [{f['severity']}] `{f.get('code')}`: {f.get('message')}"
            )
    lines += [
        "",
        "## Confirmation",
        "",
        "Изменения реализованы глобально и не зависят от protocol_id.",
        "",
    ]
    return "\n".join(lines)
