from django.test import SimpleTestCase

from apps.vpr.fioko_2026 import build_fioko_2026_layer
from apps.vpr.tests.fioko_fixtures import make_analytics, make_student


class FiokoJournalGapTests(SimpleTestCase):
    def test_gap_ge_2(self):
        students = [
            make_student("1", primary=10, mark_vpr=2, mark_journal=4),  # gap 2
            make_student("2", primary=11, mark_vpr=3, mark_journal=3),  # 0
            make_student("3", primary=12, mark_vpr=4, mark_journal=5),  # 1
            make_student("4", primary=9, mark_vpr=2, mark_journal=5),  # 3
        ]
        analytics = make_analytics(students=students, n=4)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        self.assertEqual(layer.journal.status, "OK")
        self.assertEqual(layer.journal.gap_ge_2_count, 2)
        self.assertTrue(all(r.journal_gap_ge_2 for r in layer.journal.rows))
        self.assertIn("существенное расхождение", layer.journal.wording.lower())

    def test_no_journal_not_available(self):
        students = [make_student("1", primary=10, mark_vpr=4, mark_journal=None)]
        analytics = make_analytics(students=students, n=1)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        self.assertEqual(layer.journal.status, "NOT_AVAILABLE")
