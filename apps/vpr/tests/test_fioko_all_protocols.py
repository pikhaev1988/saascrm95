"""
Параметризованный прогон FIOKO layer по доступным протоколам.

Не ограничивается Biology #11 / English #6.
При пустой локальной БД — skip.
"""

from __future__ import annotations

from django.test import TestCase

from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
from apps.vpr.models import VprProtocol
from apps.vpr.subject_report import build_subject_report
from apps.vpr.validation.report_validator import VprReportValidator


class FiokoAllProtocolsTests(TestCase):
    def test_fioko_layer_on_all_available_protocols(self):
        qs = VprProtocol.objects.all().order_by("id")
        total = qs.count()
        if total == 0:
            self.skipTest("Нет VPR protocols в локальной БД")

        engine = VprComprehensiveAnalysisEngine()
        validator = VprReportValidator()
        failures: list[str] = []
        # ограничим CI-время: до 30 протоколов локально; полный прогон — acceptance script
        sample = list(qs[:30])
        for protocol in sample:
            try:
                analysis = engine.analyze(protocol)
                self.assertIsNotNone(analysis.fioko_2026)
                self.assertEqual(analysis.fioko_2026.source, "FIOKO_2026")
                report = build_subject_report(analysis, protocol, validate=False)
                self.assertTrue(report.methodology_basis)
                self.assertTrue(report.fioko_evidence)
                result = validator.validate(analysis, report)
                if not result.valid:
                    failures.append(
                        f"id={protocol.id} errors={result.errors[:2]}"
                    )
            except Exception as exc:  # noqa: BLE001
                failures.append(f"id={protocol.id} exc={exc}")

        self.assertFalse(failures, msg="; ".join(failures[:10]))
