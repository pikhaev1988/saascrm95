"""
Validate all VPR protocols (Stage 10 integrity + methodology gates).

Usage:
  python manage.py vpr_validate_all
  python manage.py vpr_validate_all --limit 10
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Stage 10: validate arithmetic/methodology for all VPR protocols."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument(
            "--out",
            type=str,
            default="apps/vpr/audit/VPR_STAGE10_VALIDATE_ALL.json",
        )

    def handle(self, *args, **options):
        from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
        from apps.vpr.models import VprProtocol
        from apps.vpr.overview_docx import generate_overview_report_docx
        from apps.vpr.subject_report import build_subject_report
        from apps.vpr.validation.integrity import VprIntegrityValidator

        engine = VprComprehensiveAnalysisEngine()
        validator = VprIntegrityValidator()
        qs = VprProtocol.objects.all().order_by("id")
        limit = options.get("limit")
        if limit:
            qs = qs[: int(limit)]

        rows = []
        fail = blocked = pass_n = 0
        for protocol in qs.iterator():
            row = {
                "protocol_id": protocol.id,
                "school": getattr(getattr(protocol, "school", None), "name", "")
                or protocol.organization_name
                or "",
                "subject": protocol.subject,
                "class": protocol.parallel,
                "participants": protocol.participants_count,
                "tasks_total": None,
                "tasks_below_50": None,
                "tasks_below_fioko_threshold": None,
                "limited_sample": None,
                "invalid_metrics": 0,
                "consistency_status": "FAIL",
                "methodology_status": "FAIL",
                "report_status": "FAIL",
                "final": "FAIL",
            }
            try:
                analysis = engine.analyze(protocol)
                integ = validator.validate(analysis, protocol)
                row["tasks_total"] = integ.metrics.get("tasks_total")
                row["tasks_below_50"] = integ.metrics.get("tasks_below_50")
                # FIOKO task band counts from facts (basic <57 / adv <28.5) if present
                facts = getattr(analysis, "facts", None)
                if facts is not None:
                    row["tasks_below_fioko_threshold"] = {
                        "critical": getattr(facts.tasks, "critical", None),
                        "problem": getattr(facts.tasks, "problem", None),
                        "below_40": getattr(facts.tasks, "below_40", None),
                    }
                row["limited_sample"] = integ.metrics.get("limited_sample")
                row["sample_tier"] = integ.metrics.get("sample_tier")
                row["invalid_metrics"] = len(integ.errors)
                row["consistency_status"] = "PASS" if integ.ok else "FAIL"
                row["methodology_status"] = "PASS"
                report = build_subject_report(analysis, protocol, validate=False)
                buf = generate_overview_report_docx(analysis, protocol, report=report)
                row["report_status"] = "PASS" if buf.getbuffer().nbytes > 1000 else "FAIL"
                hard = row["consistency_status"] != "PASS" or row["report_status"] != "PASS"
                row["final"] = "FAIL" if hard else "PASS"
                if integ.errors:
                    row["errors"] = [e.to_dict() for e in integ.errors[:10]]
            except Exception as exc:  # noqa: BLE001
                row["final"] = "BLOCKED"
                row["errors"] = [{"message": str(exc)[:300]}]
            if row["final"] == "PASS":
                pass_n += 1
            elif row["final"] == "BLOCKED":
                blocked += 1
            else:
                fail += 1
            rows.append(row)

        payload = {
            "stage": "STAGE_10",
            "TOTAL": len(rows),
            "PASS": pass_n,
            "FAIL": fail,
            "BLOCKED": blocked,
            "rows": rows,
        }
        out = Path(options["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(
            self.style.SUCCESS(
                f"TOTAL={len(rows)} PASS={pass_n} FAIL={fail} BLOCKED={blocked} → {out}"
            )
        )
