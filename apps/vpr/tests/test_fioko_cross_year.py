from django.test import SimpleTestCase

from apps.vpr.fioko_2026 import build_fioko_2026_layer
from apps.vpr.tests.fioko_fixtures import make_analytics, make_task


class FiokoCrossYearTests(SimpleTestCase):
    def test_not_available_without_previous(self):
        analytics = make_analytics()
        layer = build_fioko_2026_layer(analytics, protocol=None, enrich_catalog=False)
        self.assertEqual(layer.cross_year.status, "NOT_AVAILABLE")

    def test_comparable_overlap_skills(self):
        current = make_analytics(
            year=2026,
            tasks=[
                make_task("1", completion=60, skill="Умение A"),
                make_task("2", completion=40, skill="Умение B"),
            ],
        )
        previous = make_analytics(
            year=2025,
            tasks=[
                make_task("1", completion=50, skill="Умение A"),
                make_task("9", completion=70, skill="Умение C"),
            ],
        )
        layer = build_fioko_2026_layer(
            current, previous_analytics=previous, enrich_catalog=False
        )
        self.assertEqual(layer.cross_year.status, "OK")
        self.assertEqual(len(layer.cross_year.items), 1)
        self.assertEqual(layer.cross_year.items[0].skill_or_topic, "Умение A")
        self.assertEqual(layer.cross_year.items[0].delta_completion_pp, 10.0)

    def test_not_comparable_no_overlap(self):
        current = make_analytics(tasks=[make_task("1", completion=60, skill="X")])
        previous = make_analytics(tasks=[make_task("1", completion=60, skill="Y")])
        layer = build_fioko_2026_layer(
            current, previous_analytics=previous, enrich_catalog=False
        )
        self.assertEqual(layer.cross_year.status, "NOT_COMPARABLE")
