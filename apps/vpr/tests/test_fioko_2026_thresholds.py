"""Пороги FIOKO 2026."""

from django.test import SimpleTestCase

from apps.vpr.analytics.thresholds import VPR_THRESHOLDS, fioko_2026_thresholds
from apps.vpr.fioko_2026.classification import classify_fioko_level


class Fioko2026ThresholdsTests(SimpleTestCase):
    def test_namespace_exists_and_isolated(self):
        cfg = VPR_THRESHOLDS["fioko_2026"]
        self.assertEqual(cfg["basic"]["sufficient_min"], 60.0)
        self.assertEqual(cfg["basic"]["insufficient_max"], 57.0)
        self.assertEqual(cfg["advanced_high"]["sufficient_min"], 30.0)
        self.assertEqual(cfg["advanced_high"]["insufficient_max"], 28.5)
        # SYSTEM groups не перезаписаны
        self.assertEqual(VPR_THRESHOLDS["groups"]["high_min"], 80.0)
        self.assertEqual(VPR_THRESHOLDS["groups"]["_source"], "SYSTEM_ANALYTICS")
        self.assertEqual(cfg["_source"], "FIOKO_2026")
        self.assertEqual(fioko_2026_thresholds()["basic"]["sufficient_min"], 60.0)

    def test_basic_classification_bands(self):
        self.assertEqual(classify_fioko_level(56.9, "basic")["fioko_level_status"], "insufficient")
        self.assertEqual(classify_fioko_level(57.0, "basic")["fioko_level_status"], "uncertainty")
        self.assertEqual(classify_fioko_level(59.9, "basic")["fioko_level_status"], "uncertainty")
        self.assertEqual(classify_fioko_level(60.0, "basic")["fioko_level_status"], "sufficient")
        self.assertEqual(classify_fioko_level(63.0, "basic")["fioko_level_status"], "sufficient")

    def test_advanced_classification_bands(self):
        self.assertEqual(
            classify_fioko_level(28.4, "advanced")["fioko_level_status"], "insufficient"
        )
        self.assertEqual(
            classify_fioko_level(28.5, "high")["fioko_level_status"], "uncertainty"
        )
        self.assertEqual(
            classify_fioko_level(30.0, "advanced")["fioko_level_status"], "sufficient"
        )

    def test_unknown_difficulty_not_available(self):
        self.assertEqual(
            classify_fioko_level(90.0, "unknown")["fioko_level_status"], "not_available"
        )
        self.assertEqual(
            classify_fioko_level(None, "basic")["fioko_level_status"], "not_available"
        )
