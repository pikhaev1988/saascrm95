from django.test import SimpleTestCase

from apps.vpr.fioko_2026 import build_fioko_2026_layer
from apps.vpr.fioko_2026.mapping import FIOKO_DIRECTION_TO_SECTIONS, get_fioko_mapping_matrix
from apps.vpr.tests.fioko_fixtures import make_analytics, make_task


class FiokoManagementTests(SimpleTestCase):
    def test_mapping_matrix_programmatic(self):
        matrix = get_fioko_mapping_matrix()
        self.assertEqual(len(matrix["directions"]), 7)
        self.assertIn("task_performance", FIOKO_DIRECTION_TO_SECTIONS)
        self.assertIn("task_performance_rows", FIOKO_DIRECTION_TO_SECTIONS["task_performance"])

    def test_management_recommendations_structure(self):
        tasks = [
            make_task("1", completion=40, difficulty="Базовый", skill="A"),
            make_task("2", completion=42, difficulty="Базовый", skill="A"),
            make_task("3", completion=45, difficulty="Базовый", skill="A"),
        ]
        analytics = make_analytics(subject="Физика", parallel=7, tasks=tasks)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        self.assertTrue(layer.management_recommendations)
        rec = layer.management_recommendations[0]
        for field in (
            "problem",
            "evidence",
            "possible_causes",
            "action",
            "responsible",
            "deadline",
            "control_metric",
            "expected_result",
        ):
            self.assertTrue(getattr(rec, field) or field == "possible_causes")
        self.assertTrue(rec.possible_causes)
        self.assertIn("Физика", rec.problem)
        self.assertEqual(layer.source, "FIOKO_2026")
        self.assertTrue(layer.methodology_basis)
