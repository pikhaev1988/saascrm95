"""Пересборка аналитики/отчётов всех протоколов без повторной загрузки файлов."""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Rebuild VPR analytics/HTML/DOCX for existing protocols from stored data "
        "(does not re-upload files)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--protocol-id", type=int, default=None)

    def handle(self, *args, **options):
        from apps.vpr.comprehensive_analysis.service import (
            clear_protocol_analysis_cache,
            get_protocol_analysis,
        )
        from apps.vpr.models import VprProtocol

        qs = VprProtocol.objects.all().order_by("id")
        pid = options.get("protocol_id")
        if pid:
            qs = qs.filter(pk=int(pid))
        limit = options.get("limit")
        if limit:
            qs = qs[: int(limit)]

        ok = fail = 0
        for protocol in qs.iterator():
            try:
                clear_protocol_analysis_cache(protocol)
                get_protocol_analysis(protocol, use_cache=False)
                ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                self.stderr.write(f"P{protocol.id} FAIL: {exc}")
        self.stdout.write(self.style.SUCCESS(f"REBUILD ok={ok} fail={fail}"))
