"""
Stage 10 unit tests: FIOKO thresholds, below_50 inclusive, sample tiers, integrity.
"""

from __future__ import annotations

from django.test import SimpleTestCase, TestCase


class VprStage10ConfigTests(SimpleTestCase):
    def test_fioko_basic_bounds_centralized(self):
        from apps.vpr.analytics.config import fioko_basic_bounds

        b = fioko_basic_bounds()
        self.assertEqual(b["insufficient_max"], 57.0)
        self.assertEqual(b["sufficient_min"], 60.0)
        self.assertEqual(b["uncertainty_delta"], 3.0)
        self.assertEqual(b["uncertainty_upper"], 63.0)

    def test_fioko_advanced_bounds_centralized(self):
        from apps.vpr.analytics.config import fioko_advanced_bounds

        b = fioko_advanced_bounds()
        self.assertEqual(b["insufficient_max"], 28.5)
        self.assertEqual(b["sufficient_min"], 30.0)
        self.assertEqual(b["uncertainty_delta"], 1.5)
        self.assertEqual(b["uncertainty_upper"], 31.5)

    def test_basic_threshold_ladder(self):
        from apps.vpr.fioko_2026.classification import classify_fioko_level

        self.assertEqual(classify_fioko_level(56.99, "basic")["fioko_level_status"], "insufficient")
        self.assertEqual(classify_fioko_level(57.00, "basic")["fioko_level_status"], "uncertainty")
        self.assertEqual(classify_fioko_level(60.00, "basic")["fioko_level_status"], "sufficient")
        # 63 — верхняя граница зоны ±3; статус sufficient (не отдельный enum)
        self.assertEqual(classify_fioko_level(63.00, "basic")["fioko_level_status"], "sufficient")

    def test_advanced_threshold_ladder(self):
        from apps.vpr.fioko_2026.classification import classify_fioko_level

        self.assertEqual(
            classify_fioko_level(28.49, "advanced")["fioko_level_status"], "insufficient"
        )
        self.assertEqual(
            classify_fioko_level(28.5, "advanced")["fioko_level_status"], "uncertainty"
        )
        self.assertEqual(classify_fioko_level(30.0, "advanced")["fioko_level_status"], "sufficient")
        self.assertEqual(classify_fioko_level(31.5, "high")["fioko_level_status"], "sufficient")

    def test_below_50_inclusive(self):
        from apps.vpr.facts.task_classification import classify_task

        self.assertTrue(classify_task(task_id="1", completion_percent=49.99).below_50)
        self.assertTrue(classify_task(task_id="2", completion_percent=50.0).below_50)
        self.assertFalse(classify_task(task_id="3", completion_percent=50.01).below_50)

    def test_partial_not_zero(self):
        from apps.vpr.facts.task_classification import classify_task

        r = classify_task(
            task_id="m",
            completion_percent=55.0,
            full_score=0,
            partial_score=10,
            zero_score=5,
        )
        self.assertEqual(r.partial_score, 10)
        self.assertEqual(r.zero_score, 5)
        self.assertNotEqual(r.partial_score, r.zero_score)

    def test_distribution_sample_tiers(self):
        from apps.vpr.analytics.config import distribution_sample_tier

        self.assertEqual(distribution_sample_tier(50)["tier"], "STANDARD")
        self.assertEqual(distribution_sample_tier(49)["tier"], "LIMITED_SAMPLE")
        self.assertIn("49", distribution_sample_tier(49)["wording"] or "")
        self.assertIn("50", distribution_sample_tier(49)["wording"] or "")
        self.assertEqual(distribution_sample_tier(15)["tier"], "VERY_LIMITED_SAMPLE")
        self.assertEqual(distribution_sample_tier(5)["tier"], "HIGH_UNCERTAINTY")

    def test_group_sample_flags(self):
        from apps.vpr.fioko_2026.sample import group_sample_flags

        self.assertFalse(group_sample_flags(9)["informative"])
        self.assertTrue(group_sample_flags(10)["informative"])

    def test_journal_gap_threshold_centralized(self):
        from apps.vpr.analytics.thresholds import VPR_THRESHOLDS

        self.assertEqual(VPR_THRESHOLDS["fioko_2026"]["journal_gap_abs_min"], 2)

    def test_metric_fact_provenance(self):
        from apps.vpr.evidence.metric_fact import metric_fact

        fact = metric_fact(
            "tasks_below_50",
            15,
            source="individual_results",
            calculation="task_completion_threshold",
            threshold=50.0,
            analytics_source="SYSTEM",
        ).to_dict()
        self.assertEqual(fact["value"], 15)
        self.assertEqual(fact["version"], "v10")
        self.assertEqual(fact["analytics_source"], "SYSTEM")
        self.assertIn("generated_at", fact)


class VprStage10BiologyRegressionTests(TestCase):
    """
    Regression: Biology 5 / protocol #11 — tasks_below_50 == 15.

    Не hardcode protocol_id в production logic; тест проверяет общий pipeline.
    """

    def test_biology_protocol_11_tasks_below_50_is_15(self):
        from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
        from apps.vpr.models import VprProtocol

        protocol = VprProtocol.objects.filter(pk=11).first()
        if protocol is None:
            self.skipTest("Protocol 11 not in this database")
        self.assertEqual(protocol.subject, "Биология")
        self.assertEqual(protocol.parallel, 5)
        self.assertEqual(protocol.participants_count, 49)

        analysis = VprComprehensiveAnalysisEngine().analyze(protocol)
        self.assertIsNotNone(analysis.facts)
        self.assertEqual(analysis.facts.tasks.below_50, 15)

        # Exactly one task at 50.0 must be included by inclusive rule
        at_50 = [
            t
            for t in analysis.analytics.tasks
            if t.completion_percent is not None and abs(float(t.completion_percent) - 50.0) < 1e-9
        ]
        self.assertGreaterEqual(len(at_50), 1)

        from apps.vpr.validation.integrity import VprIntegrityValidator

        result = VprIntegrityValidator().validate(analysis, protocol)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.metrics["tasks_below_50"], 15)
        self.assertEqual(result.metrics["sample_tier"], "LIMITED_SAMPLE")
