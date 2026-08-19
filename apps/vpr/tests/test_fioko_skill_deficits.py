from django.test import SimpleTestCase

from apps.vpr.fioko_2026 import build_fioko_2026_layer
from apps.vpr.tests.fioko_fixtures import make_analytics, make_task


class FiokoSkillDeficitsTests(SimpleTestCase):
    def test_system_deficit_majority_red(self):
        tasks = [
            make_task("1", completion=40, difficulty="Базовый", skill="Текст"),
            make_task("2", completion=45, difficulty="Базовый", skill="Текст"),
            make_task("3", completion=80, difficulty="Базовый", skill="Текст"),
        ]
        analytics = make_analytics(tasks=tasks)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        sd = next(s for s in layer.skill_deficits if s.skill == "Текст")
        self.assertTrue(sd.system_deficit)
        self.assertEqual(sd.status, "OK")
        self.assertEqual(len(sd.red_tasks), 2)

    def test_single_task_insufficient_data(self):
        tasks = [make_task("1", completion=40, difficulty="Базовый", skill="Одиночное")]
        analytics = make_analytics(tasks=tasks)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        sd = next(s for s in layer.skill_deficits if s.skill == "Одиночное")
        self.assertFalse(sd.system_deficit)
        self.assertEqual(sd.status, "INSUFFICIENT_DATA")
