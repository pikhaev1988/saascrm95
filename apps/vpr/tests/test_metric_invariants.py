"""Инварианты VPR Metric Layer (этап 3)."""

from __future__ import annotations

import math

from django.test import SimpleTestCase

from apps.vpr.analytics.metrics import assert_task_count_invariant, build_task_rate_fields, rate_percent
from apps.vpr.analytics.result import (
    VprAnalyticsResult,
    VprMarksDistribution,
    VprScoresDistribution,
    VprStudentAnalytics,
    VprSummaryMetrics,
)
from apps.vpr.analytics.thresholds import VPR_THRESHOLDS, group_thresholds
from apps.vpr.comprehensive_analysis.groups import VprParticipantGroupAnalyzer
from apps.vpr.exceptions import VprValidationError


def _summary(n: int = 4) -> VprSummaryMetrics:
    return VprSummaryMetrics(
        participants_count=n,
        max_primary_score=100,
        avg_primary_score=50.0,
        min_primary_score=20.0,
        max_primary_result=90.0,
        avg_mark_vpr=3.5,
        avg_mark_journal=3.5,
        knowledge_quality_percent=40.0,
        absolute_achievement_percent=80.0,
        median_primary_score=50.0,
        mode_primary_score=50.0,
        stdev_primary_score=10.0,
        cv_primary_score_percent=20.0,
    )


def _student(code: str, pct: float | None, mark: int | None = 3) -> VprStudentAnalytics:
    return VprStudentAnalytics(
        participant_code=code,
        full_name=code,
        class_group="5А",
        gender="",
        primary_score=None if pct is None else pct,
        mark_vpr=mark,
        mark_journal=mark,
        completion_percent=pct,
        avg_task_score=None,
        place_overall=None,
        place_in_class=None,
    )


def _analytics(students: list[VprStudentAnalytics]) -> VprAnalyticsResult:
    return VprAnalyticsResult(
        protocol_id=1,
        subject="Биология",
        parallel=5,
        academic_year=2026,
        organization_name="Test",
        summary=_summary(len(students)),
        marks=VprMarksDistribution(),
        scores=VprScoresDistribution(),
        tasks=[],
        topics=[],
        skills=[],
        students=students,
    )


class VprMetricLayerUnitTests(SimpleTestCase):
    def test_rate_percent_empty_is_none_not_nan(self):
        r = rate_percent(0, 0, formula_type="x/y*100", source_metric="t")
        self.assertIsNone(r.value)
        self.assertFalse(isinstance(r.value, float) and math.isnan(r.value))

    def test_build_task_rates_biology_task3_shape(self):
        # N=49, max=2, full=0, partial=25, zero=24, earned=25 → completion≈25.51
        rates = build_task_rate_fields(
            full_score_count=0,
            partial_score_count=25,
            zero_score_count=24,
            total_students=49,
            earned_points_sum=25.0,
            max_score=2,
            task_code="3",
        )
        self.assertEqual(
            rates["full_score_count"] + rates["partial_score_count"] + rates["zero_score_count"],
            49,
        )
        self.assertEqual(rates["full_score_rate"], 0.0)
        self.assertAlmostEqual(rates["partial_score_rate"], 100.0 * 25 / 49, places=2)
        self.assertAlmostEqual(rates["zero_score_rate"], 100.0 * 24 / 49, places=2)
        self.assertAlmostEqual(rates["completion_percent"], 25.51, places=1)
        rate_sum = (
            (rates["full_score_rate"] or 0)
            + (rates["partial_score_rate"] or 0)
            + (rates["zero_score_rate"] or 0)
        )
        self.assertAlmostEqual(rate_sum, 100.0, places=1)
        self.assertGreaterEqual(rates["completion_percent"], 0)
        self.assertLessEqual(rates["completion_percent"], 100)

    def test_invariant_raises_on_mismatch(self):
        with self.assertRaises(VprValidationError):
            assert_task_count_invariant(
                full_score_count=1,
                partial_score_count=1,
                zero_score_count=1,
                total_students=2,
            )

    def test_empty_completion_not_zero(self):
        rates = build_task_rate_fields(
            full_score_count=0,
            partial_score_count=0,
            zero_score_count=0,
            total_students=0,
            earned_points_sum=0.0,
            max_score=2,
            task_code="empty",
        )
        self.assertIsNone(rates["completion_percent"])
        self.assertIsNone(rates["full_score_rate"])
        self.assertIsNone(rates["partial_score_rate"])
        self.assertIsNone(rates["zero_score_rate"])

    def test_thresholds_frozen_values(self):
        self.assertEqual(VPR_THRESHOLDS["deficits"]["high"], 90.0)
        self.assertEqual(VPR_THRESHOLDS["deficits"]["sufficient"], 75.0)
        self.assertEqual(VPR_THRESHOLDS["deficits"]["acceptable"], 60.0)
        self.assertEqual(VPR_THRESHOLDS["deficits"]["problem"], 40.0)
        high, medium = group_thresholds()
        self.assertEqual(high, 80.0)
        self.assertEqual(medium, 50.0)


class VprGroupInvariantTests(SimpleTestCase):
    def test_group_sum_equals_n(self):
        students = [
            _student("a", 90),
            _student("b", 60),
            _student("c", 20),
            _student("d", 50),
        ]
        profile = VprParticipantGroupAnalyzer().analyze(_analytics(students))
        total = sum(b.count for b in profile.groups.values())
        self.assertEqual(total, 4)
        self.assertEqual(profile.groups["high"].count, 1)
        self.assertEqual(profile.groups["medium"].count, 2)
        self.assertEqual(profile.groups["risk"].count, 1)
        self.assertTrue(profile.validation_ok)

    def test_missing_primary_fallback_data_incomplete(self):
        students = [
            _student("a", 90),
            _student("b", None),
        ]
        profile = VprParticipantGroupAnalyzer().analyze(_analytics(students))
        self.assertEqual(sum(b.count for b in profile.groups.values()), 2)
        self.assertTrue(profile.data_incomplete)
        self.assertIn("b", profile.incomplete_participant_codes)
        self.assertIn("b", profile.groups["risk"].participant_codes)

    def test_positive_potential_not_in_group_sum(self):
        students = [
            _student("a", 85, mark=5),
            _student("b", 55, mark=3),
            _student("c", 30, mark=2),
        ]
        profile = VprParticipantGroupAnalyzer().analyze(_analytics(students))
        group_sum = sum(b.count for b in profile.groups.values())
        self.assertEqual(group_sum, 3)
        self.assertIn("a", profile.positive_potential_codes)
        # potential — дополнительный флаг, не четвёртая группа
        self.assertEqual(group_sum, len(students))
