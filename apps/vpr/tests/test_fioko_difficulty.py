from django.test import SimpleTestCase

from apps.vpr.fioko_2026.difficulty import normalize_difficulty


class FiokoDifficultyTests(SimpleTestCase):
    def test_normalize_variants(self):
        self.assertEqual(normalize_difficulty("Б"), "basic")
        self.assertEqual(normalize_difficulty("Базовый"), "basic")
        self.assertEqual(normalize_difficulty("П"), "advanced")
        self.assertEqual(normalize_difficulty("Повышенный"), "advanced")
        self.assertEqual(normalize_difficulty("В"), "high")
        self.assertEqual(normalize_difficulty("Высокий"), "high")
        self.assertEqual(normalize_difficulty(""), "unknown")
        self.assertEqual(normalize_difficulty(None), "unknown")
        self.assertEqual(normalize_difficulty("неизвестно"), "unknown")
