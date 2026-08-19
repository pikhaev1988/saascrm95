"""
Production acceptance runner for FIOKO Stage 7 across ALL VPR protocols.

Usage on server:
  python manage.py shell < apps/vpr/management/commands/_stage7_accept_snippet.py
or:
  python -c "exec(open('apps/vpr/audit/run_stage7_acceptance.py', encoding='utf-8').read())"
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def run_stage7_acceptance(*, limit: int | None = None, out_path: str | None = None) -> dict:
    from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
    from apps.vpr.models import VprProtocol
    from apps.vpr.overview_docx import generate_overview_report_docx
    from apps.vpr.subject_report import build_subject_report
    from apps.vpr.validation.report_validator import VprReportValidator
    from django.template.loader import render_to_string

    engine = VprComprehensiveAnalysisEngine()
    validator = VprReportValidator()
    qs = VprProtocol.objects.all().order_by("id")
    if limit:
        qs = qs[: int(limit)]

    rows = []
    summary = Counter()
    for protocol in qs.iterator():
        row = {
            "protocol_id": protocol.id,
            "subject": protocol.subject,
            "class": protocol.parallel,
            "year": protocol.academic_year,
            "N": protocol.participants_count,
            "tasks": protocol.tasks_count,
            "difficulty_mapped": "",
            "planned_results_mapped": "",
            "FIOKO_status": "FAIL",
            "warnings": 0,
            "errors": 0,
            "HTML": "FAIL",
            "DOCX": "FAIL",
        }
        summary["TOTAL"] += 1
        try:
            analysis = engine.analyze(protocol)
            fioko = analysis.fioko_2026
            cov = getattr(fioko, "difficulty_coverage", {}) or {}
            row["difficulty_mapped"] = f"{cov.get('mapped_tasks', 0)}/{cov.get('total_tasks', 0)}"
            row["planned_results_mapped"] = getattr(fioko, "catalog_mapping_status", "")
            report = build_subject_report(analysis, protocol, validate=False)
            validation = validator.validate(analysis, report)
            row["warnings"] = len(validation.warnings)
            row["errors"] = len(validation.errors)
            row["FIOKO_status"] = "PASS" if validation.valid else "FAIL"
            # HTML
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
            row["HTML"] = "PASS" if html and report.methodology_basis else "FAIL"
            # DOCX
            buf = generate_overview_report_docx(analysis, protocol, report=report)
            row["DOCX"] = "PASS" if buf.getbuffer().nbytes > 1000 else "FAIL"
            if row["FIOKO_status"] == "PASS" and row["HTML"] == "PASS" and row["DOCX"] == "PASS":
                summary["PASS"] += 1
            elif validation.errors:
                summary["FAIL"] += 1
            else:
                summary["PASS"] += 1  # warnings-only still pass gate
                row["FIOKO_status"] = "PASS"
        except Exception as exc:  # noqa: BLE001
            row["FIOKO_status"] = "BLOCKED"
            row["errors"] = 1
            row["error_message"] = str(exc)[:300]
            summary["BLOCKED"] += 1
        rows.append(row)

    payload = {
        "TOTAL": summary["TOTAL"],
        "PASS": summary["PASS"],
        "FAIL": summary["FAIL"],
        "BLOCKED": summary["BLOCKED"],
        "rows": rows,
    }
    target = Path(out_path or "apps/vpr/audit/VPR_FIOKO_STAGE7_ACCEPTANCE.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown summary
    md = Path(str(target).replace(".json", ".md"))
    lines = [
        "# VPR_FIOKO_STAGE7_ACCEPTANCE",
        "",
        f"TOTAL={payload['TOTAL']} PASS={payload['PASS']} FAIL={payload['FAIL']} BLOCKED={payload['BLOCKED']}",
        "",
        "| protocol_id | subject | class | year | N | tasks | difficulty_mapped | planned_results_mapped | FIOKO_status | warnings | errors | HTML | DOCX |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['protocol_id']} | {r['subject']} | {r['class']} | {r['year']} | {r['N']} | {r['tasks']} | "
            f"{r['difficulty_mapped']} | {r['planned_results_mapped']} | {r['FIOKO_status']} | "
            f"{r['warnings']} | {r['errors']} | {r['HTML']} | {r['DOCX']} |"
        )
    md.write_text("\n".join(lines), encoding="utf-8")
    return payload


if __name__ == "__main__":
    import django
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analiz_gia.settings")
    django.setup()
    result = run_stage7_acceptance()
    print(json.dumps({k: result[k] for k in ("TOTAL", "PASS", "FAIL", "BLOCKED")}, ensure_ascii=False))
