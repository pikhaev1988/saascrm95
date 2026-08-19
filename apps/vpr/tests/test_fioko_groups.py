from django.test import SimpleTestCase

from apps.vpr.fioko_2026 import build_fioko_2026_layer
from apps.vpr.tests.fioko_fixtures import make_analytics, make_student


class FiokoGroupsTests(SimpleTestCase):
    def test_sample_warning_under_10(self):
        students = [make_student(str(i), primary=10 + i, mark_vpr=3) for i in range(8)]
        analytics = make_analytics(students=students, n=8)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        self.assertTrue(layer.groups.sample_warning)
        self.assertTrue(layer.groups.informational_only)

    def test_informative_from_10(self):
        students = [make_student(str(i), primary=10 + i, mark_vpr=2 + (i % 4)) for i in range(12)]
        analytics = make_analytics(students=students, n=12)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        self.assertFalse(layer.groups.sample_warning)
        self.assertTrue(layer.groups.buckets)
