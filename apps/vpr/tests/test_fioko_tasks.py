from django.test import SimpleTestCase

from apps.vpr.fioko_2026 import build_fioko_2026_layer
from apps.vpr.tests.fioko_fixtures import make_analytics, make_task


class FiokoTasksTests(SimpleTestCase):
    def test_task_fioko_status_and_rates_preserved(self):
        tasks = [
            make_task("1", completion=55, difficulty="Базовый", skill="A", max_score=2, full=0, partial=11, zero=9),
            make_task("2", completion=58, difficulty="Базовый", skill="A"),  # uncertainty
            make_task("3", completion=70, difficulty="Базовый", skill="B"),  # sufficient
            make_task("4", completion=20, difficulty="Повышенный", skill="B"),  # insufficient P
            make_task("5", completion=40, difficulty="", skill=""),  # unknown
        ]
        analytics = make_analytics(tasks=tasks)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        by = {t.task_code: t for t in layer.tasks}
        self.assertEqual(by["1"].fioko_level_status, "insufficient")
        self.assertEqual(by["1"].visual_marker, "red")
        self.assertEqual(by["2"].fioko_level_status, "uncertainty")
        self.assertEqual(by["2"].visual_marker, "yellow")
        self.assertEqual(by["3"].fioko_level_status, "sufficient")
        self.assertEqual(by["3"].visual_marker, "green")
        self.assertEqual(by["4"].fioko_level_status, "insufficient")
        self.assertEqual(by["5"].fioko_level_status, "not_available")
        # Metric Contract: multi-score completion ≠ full_score_rate
        self.assertEqual(by["1"].full_score_rate, 0.0)
        self.assertEqual(by["1"].completion_percent, 55)
        self.assertNotEqual(by["1"].completion_percent, by["1"].full_score_rate)
