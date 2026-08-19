from django.test import SimpleTestCase

from apps.vpr.fioko_2026 import build_fioko_2026_layer
from apps.vpr.tests.fioko_fixtures import make_analytics, make_task


class FiokoPlannedResultsTests(SimpleTestCase):
    def test_fioko_achievement_status_separate_from_system(self):
        tasks = [
            make_task("1", completion=50, difficulty="Базовый", skill="Умение X", topic="T1"),
            make_task("2", completion=52, difficulty="Базовый", skill="Умение X", topic="T1"),
        ]
        analytics = make_analytics(tasks=tasks)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        self.assertTrue(layer.planned_results)
        row = next(p for p in layer.planned_results if "Умение X" in p.planned_result or p.planned_result)
        self.assertEqual(row.fioko_achievement_status, "insufficient")
        self.assertTrue(row.system_mastery_status)  # SYSTEM classify_mastery
        self.assertNotEqual(row.fioko_achievement_status, row.system_mastery_status)
