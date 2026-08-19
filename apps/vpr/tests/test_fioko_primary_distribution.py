from django.test import SimpleTestCase

from apps.vpr.fioko_2026 import build_fioko_2026_layer
from apps.vpr.tests.fioko_fixtures import make_analytics, make_student


class FiokoPrimaryDistributionTests(SimpleTestCase):
    def test_distribution_stats_and_boundaries(self):
        students = [
            make_student(str(i), primary=float(i), mark_vpr=2 if i < 5 else (3 if i < 10 else 4))
            for i in range(1, 25)
        ]
        analytics = make_analytics(students=students, n=24)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        d = layer.distribution
        self.assertEqual(d.min, 1.0)
        self.assertEqual(d.max, 24.0)
        self.assertIsNotNone(d.mean)
        self.assertIsNotNone(d.median)
        self.assertEqual(d.cv_source, "SYSTEM_ANALYTICS")
        self.assertEqual(len(d.boundary_peak_flags), 3)
        self.assertEqual(d.boundary_peak_status, "NOT_AVAILABLE")
        self.assertFalse(d.possible_objectivity_marker)
        self.assertEqual(d.sample_size, 24)
        self.assertIn(d.sample_quality, {"approximate", "limited", "informative"})
