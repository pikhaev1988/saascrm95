from django.test import SimpleTestCase

from apps.vpr.fioko_2026 import build_fioko_2026_layer
from apps.vpr.tests.fioko_fixtures import make_analytics, make_student


class FiokoMarksTests(SimpleTestCase):
    def test_mark_percents(self):
        students = [
            make_student("1", primary=5, mark_vpr=2),
            make_student("2", primary=8, mark_vpr=2),
            make_student("3", primary=10, mark_vpr=3),
            make_student("4", primary=12, mark_vpr=4),
            make_student("5", primary=15, mark_vpr=5),
        ]
        analytics = make_analytics(students=students, n=5)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        self.assertEqual(layer.marks.mark_2_percent, 40.0)
        self.assertEqual(layer.marks.mark_3_percent, 20.0)
        self.assertEqual(layer.marks.mark_2_dynamics_status, "NOT_AVAILABLE")
        self.assertIsNone(layer.marks.mark_2_dynamics_pp)
