"""
Management command: VPR Stage 9 Final Production Acceptance.

Usage:
  python manage.py vpr_stage9_acceptance
  python manage.py vpr_stage9_acceptance --limit 5
  python manage.py vpr_stage9_acceptance --skip-upload
"""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "STAGE 9 final production acceptance (existing 138 + rebuild + upload lifecycle)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument(
            "--out-dir",
            type=str,
            default="apps/vpr/audit",
        )
        parser.add_argument(
            "--skip-upload",
            action="store_true",
            help="Skip new/duplicate/invalid upload tests (existing + rebuild only).",
        )

    def handle(self, *args, **options):
        from apps.vpr.audit.run_stage9_production_acceptance import (
            run_stage9_production_acceptance,
        )

        result = run_stage9_production_acceptance(
            limit=options.get("limit"),
            out_dir=options.get("out_dir") or "apps/vpr/audit",
            skip_upload=bool(options.get("skip_upload")),
        )
        final = result.get("FINAL_PRODUCTION_ACCEPTANCE")
        style = self.style.SUCCESS if final == "PASS_WITH_WARNINGS" else self.style.ERROR
        self.stdout.write(
            style(
                "FINAL={final} TOTAL={t} PASS={p} FAIL={f} BLOCKED={b} "
                "New={nu} Rebuild={rb} Isolation={iso}".format(
                    final=final,
                    t=result.get("TOTAL_EXISTING"),
                    p=result.get("PASS"),
                    f=result.get("FAIL"),
                    b=result.get("BLOCKED"),
                    nu=(result.get("New_upload") or {}).get("status"),
                    rb=(result.get("Rebuild") or {}).get("status"),
                    iso=(result.get("Isolation") or {}).get("status"),
                )
            )
        )
        self.stdout.write("MD: apps/vpr/audit/VPR_STAGE9_PRODUCTION_ACCEPTANCE.md")
        self.stdout.write("JSON: apps/vpr/audit/VPR_STAGE9_PRODUCTION_ACCEPTANCE.json")
