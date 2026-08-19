from django.test import SimpleTestCase

from apps.vpr.fioko_2026 import build_fioko_2026_layer
from apps.vpr.tests.fioko_fixtures import make_analytics, make_student, make_task


class FiokoIndividualResultsTests(SimpleTestCase):
    def test_missing_level_is_null_not_zero(self):
        analytics = make_analytics(
            tasks=[
                make_task("1", completion=80, difficulty="Базовый", skill="A"),
                # нет high-заданий
            ],
            students=[make_student("1", primary=12, mark_vpr=4, mark_journal=4)],
        )
        layer = build_fioko_2026_layer(analytics, protocol=None, enrich_catalog=False)
        self.assertTrue(layer.individuals)
        row = layer.individuals[0]
        # без protocol task_scores — % по уровням null
        self.assertIsNone(row.basic_completion_percent)
        self.assertIsNone(row.advanced_completion_percent)
        self.assertIsNone(row.high_completion_percent)
        self.assertEqual(row.basic_status, "not_available")

    def test_individuals_passport_fields(self):
        analytics = make_analytics(n=5)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        self.assertEqual(len(layer.individuals), 5)
        for row in layer.individuals:
            self.assertIsNotNone(row.participant_code)
            self.assertIn("basic", row.difficulty_coverage)
