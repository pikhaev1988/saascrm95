"""
Management command: full quality audit across ALL VPR protocols.

Usage:
  python manage.py vpr_global_quality_audit
  python manage.py vpr_global_quality_audit --limit 10
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Global VPR quality audit for all uploaded protocols (analytics + evidence + DOCX)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument(
            "--out",
            type=str,
            default="apps/vpr/audit/VPR_GLOBAL_QUALITY_AUDIT.md",
        )

    def handle(self, *args, **options):
        from apps.vpr.audit.run_global_quality_audit import run_global_quality_audit

        limit = options.get("limit")
        out = options.get("out")
        result = run_global_quality_audit(limit=limit, out_path=out)
        self.stdout.write(
            self.style.SUCCESS(
                "TOTAL={TOTAL} PASS={PASS} FAIL={FAIL} BLOCKED={BLOCKED} "
                "Critical={Critical} High={High} status={status}".format(**result)
            )
        )
        json_path = Path(str(out).replace(".md", ".json"))
        if json_path.exists():
            self.stdout.write(f"JSON: {json_path}")
        self.stdout.write(f"MD: {out}")
