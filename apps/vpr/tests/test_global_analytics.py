"""Global modernization regression tests (all protocols share the same pipeline)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from apps.vpr.comprehensive_analysis.groups import VprParticipantGroupAnalyzer
from apps.vpr.comprehensive_analysis.schemas import VprGroupBucket, VprParticipantGroupsProfile
from apps.vpr.deficits.classification import EducationalFindingKind, classify_educational_finding
from apps.vpr.evidence import EvidenceStatus, AnalyticalOrigin, CauseType, build_evidence
from apps.vpr.evidence.envelope import hypothesis_wording
from apps.vpr.expert_analysis.profiles import build_preparation_profile_result
from apps.vpr.methodology import FIOKO_2026_RULES, SYSTEM_ANALYTICS_RULES, get_methodology_registry
from apps.vpr.validation.consistency import CrossReportConsistencyValidator


class GlobalEvidenceTests(TestCase):
    def test_limited_sample_blocks_management(self):
        env = build_evidence(
            status=EvidenceStatus.ESTABLISHED,
            origin=AnalyticalOrigin.SYSTEM_ANALYTICS,
            sample_size=3,
            source_metrics=["completion"],
        )
        self.assertEqual(env.evidence_status, EvidenceStatus.LIMITED_SAMPLE)
        self.assertFalse(env.allow_management_conclusion)

    def test_hypothesis_wording(self):
        text = hypothesis_wording("методика неэффективна")
        self.assertIn("Возможная причина", text)
        self.assertIn("требует дополнительной проверки", text.lower())

    def test_cause_type_fact_not_default_from_completion(self):
        # Epistemic default is HYPOTHESIS; FACT is not auto from % alone
        self.assertEqual(CauseType.HYPOTHESIS.value, "HYPOTHESIS")
        self.assertEqual(CauseType.FACT.value, "FACT")


class GlobalDeficitClassificationTests(TestCase):
    def test_low_percent_alone_is_difficulty_not_deficit(self):
        c = classify_educational_finding(
            completion_percent=35.0,
            linked_tasks=["1"],
            sample_size=40,
            problem_band=True,
        )
        self.assertEqual(c.finding_kind, EducationalFindingKind.EDUCATIONAL_DIFFICULTY)
        self.assertFalse(c.allow_deficit_term)
        self.assertFalse(c.allow_management_conclusion)

    def test_multi_task_problem_allows_deficit(self):
        c = classify_educational_finding(
            completion_percent=35.0,
            linked_tasks=["1", "2", "3"],
            sample_size=40,
            problem_band=True,
        )
        self.assertEqual(c.finding_kind, EducationalFindingKind.EDUCATIONAL_DEFICIT)
        self.assertTrue(c.allow_deficit_term)
        self.assertEqual(c.evidence_status, EvidenceStatus.ESTABLISHED)

    def test_insufficient_partial_catalog(self):
        c = classify_educational_finding(
            completion_percent=40.0,
            linked_tasks=[],
            sample_size=20,
            catalog_status="PARTIAL",
            problem_band=True,
        )
        self.assertEqual(c.evidence_status, EvidenceStatus.INSUFFICIENT_DATA)
        self.assertFalse(c.allow_deficit_term)


class GlobalProfileTests(TestCase):
    def test_profile_marked_system_analytics(self):
        p = build_preparation_profile_result(
            code="critical",
            label="критический профиль",
            explanations=["risk share high"],
        )
        self.assertEqual(p.classification_origin, "SYSTEM_ANALYTICS")
        self.assertIn("внутренний аналитический профиль", p.methodology_note.lower())
        self.assertIn("не официальная классификация ФИОКО", p.methodology_note)


class GlobalMethodologyTests(TestCase):
    def test_rules_separated(self):
        reg = get_methodology_registry()
        self.assertIn("FIOKO_2026_RULES", reg)
        self.assertIn("SYSTEM_ANALYTICS_RULES", reg)
        self.assertIn("LOCAL_ANALYTICS_RULES", reg)
        self.assertEqual(SYSTEM_ANALYTICS_RULES["groups.high_min"]["source"], "SYSTEM_ANALYTICS")
        self.assertEqual(FIOKO_2026_RULES["groups_sample_min"]["source"], "FIOKO_2026")


class GlobalGroupConsistencyTests(TestCase):
    def test_risk_stable_high_sum_equals_participants(self):
        """Regression: 32+17+2 must equal N=51; any other total is ERROR."""
        n = 51
        profile = VprParticipantGroupsProfile(
            groups={
                "high": VprGroupBucket(count=2, percent=round(100 * 2 / n, 1)),
                "medium": VprGroupBucket(count=17, percent=round(100 * 17 / n, 1)),
                "risk": VprGroupBucket(count=32, percent=round(100 * 32 / n, 1)),
            },
            validation_ok=True,
        )
        analysis = SimpleNamespace(
            summary=SimpleNamespace(participants_count=n),
            participant_groups=profile,
            task_analysis=None,
            tasks=[],
            marks=None,
        )
        result = CrossReportConsistencyValidator().validate(analysis)
        self.assertTrue(result.ok, result.errors)

        # Broken case: sum shows 49 instead of 51
        broken = VprParticipantGroupsProfile(
            groups={
                "high": VprGroupBucket(count=2, percent=4.0),
                "medium": VprGroupBucket(count=15, percent=30.0),
                "risk": VprGroupBucket(count=32, percent=62.7),
            }
        )
        analysis.participant_groups = broken
        bad = CrossReportConsistencyValidator().validate(analysis)
        self.assertFalse(bad.ok)
        self.assertTrue(any(e.code == "consistency.groups_sum" for e in bad.errors))

    def test_group_bucket_has_system_origin(self):
        from apps.vpr.analytics.result import (
            VprAnalyticsResult,
            VprMarksDistribution,
            VprScoresDistribution,
            VprStudentAnalytics,
            VprSummaryMetrics,
        )

        def _stu(code: str, completion: float, mark: int) -> VprStudentAnalytics:
            return VprStudentAnalytics(
                participant_code=code,
                full_name=code,
                class_group="A",
                gender="",
                primary_score=completion / 2.0,
                mark_vpr=mark,
                mark_journal=None,
                completion_percent=completion,
                avg_task_score=None,
                place_overall=None,
                place_in_class=None,
            )

        students = []
        for i in range(2):
            students.append(_stu(f"H{i}", 85.0, 5))
        for i in range(17):
            students.append(_stu(f"M{i}", 60.0, 4))
        for i in range(32):
            students.append(_stu(f"R{i}", 20.0, 2))
        analytics = VprAnalyticsResult(
            protocol_id=0,
            subject="Тест",
            parallel=5,
            academic_year=2026,
            organization_name="",
            summary=VprSummaryMetrics(
                participants_count=51,
                max_primary_score=50,
                avg_primary_score=None,
                min_primary_score=None,
                max_primary_result=None,
                avg_mark_vpr=None,
                avg_mark_journal=None,
                knowledge_quality_percent=None,
                absolute_achievement_percent=None,
                median_primary_score=None,
                mode_primary_score=None,
                stdev_primary_score=None,
                cv_primary_score_percent=None,
            ),
            marks=VprMarksDistribution(),
            scores=VprScoresDistribution(),
            tasks=[],
            topics=[],
            skills=[],
            students=students,
        )
        profile = VprParticipantGroupAnalyzer().analyze(analytics)
        self.assertEqual(
            profile.groups["high"].count
            + profile.groups["medium"].count
            + profile.groups["risk"].count,
            51,
        )
        self.assertEqual(profile.groups["high"].count, 2)
        self.assertEqual(profile.groups["medium"].count, 17)
        self.assertEqual(profile.groups["risk"].count, 32)
        for key in ("high", "medium", "risk"):
            self.assertEqual(profile.groups[key].classification_origin, "SYSTEM_ANALYTICS")
            if profile.groups[key].count < 10:
                self.assertEqual(profile.groups[key].evidence_status, "LIMITED_SAMPLE")
                self.assertFalse(profile.groups[key].allow_management_conclusion)


class GlobalFactsTests(TestCase):
    def test_facts_exclusive_sum_and_overlapping_potential(self):
        from apps.vpr.facts.builder import build_vpr_report_facts

        n = 51
        profile = VprParticipantGroupsProfile(
            groups={
                "high": VprGroupBucket(count=2, percent=round(100 * 2 / n, 1)),
                "medium": VprGroupBucket(count=17, percent=round(100 * 17 / n, 1)),
                "risk": VprGroupBucket(count=32, percent=round(100 * 32 / n, 1)),
            },
            positive_potential_codes=["H0", "H1"],
            validation_ok=True,
        )
        analysis = SimpleNamespace(
            summary=SimpleNamespace(
                participants_count=n,
                min_primary_score=1,
                max_primary_result=20,
                avg_primary_score=10,
                median_primary_score=9,
                stdev_primary_score=2,
                cv_primary_score_percent=20,
            ),
            participant_groups=profile,
            task_analysis=None,
            tasks=[],
            marks=None,
            analytics=SimpleNamespace(tasks=[], students=[], marks=None, summary=None),
            objectivity=SimpleNamespace(
                compared_count=10,
                journal_comparison={"equal": 4, "lower": 3, "higher": 3},
                journal_comparison_percents={"equal": 40.0, "lower": 30.0, "higher": 30.0},
            ),
            deficits=None,
            school_profile=SimpleNamespace(classification="critical"),
            fioko_2026=None,
        )
        facts = build_vpr_report_facts(analysis)
        self.assertEqual(facts.participants, 51)
        self.assertEqual(facts.exclusive_group_sum(), 51)
        self.assertEqual(facts.group("stable").count, 17)
        self.assertEqual(facts.groups["positive_potential"].group_type, "OVERLAPPING")
        self.assertEqual(facts.groups["positive_potential"].count, 2)
        cons = CrossReportConsistencyValidator().validate(analysis)
        self.assertTrue(cons.ok, cons.errors)

    def test_task_classification_none_not_critical(self):
        from apps.vpr.facts.task_classification import classify_task

        r = classify_task(task_id="1", completion_percent=None)
        self.assertEqual(r.classification, "NOT_AVAILABLE")
        self.assertFalse(r.below_50)
        self.assertFalse(r.is_critical)

    def test_task_classification_uses_registry_not_renderer(self):
        from apps.vpr.facts.task_classification import classify_task

        r = classify_task(task_id="1", completion_percent=35.0)
        self.assertEqual(r.classification, "CRITICAL")
        self.assertTrue(r.below_50)
        self.assertTrue(r.below_40)
        r2 = classify_task(task_id="2", completion_percent=55.0)
        self.assertEqual(r2.classification, "RISK")
        self.assertFalse(r2.below_50)
        self.assertFalse(r2.below_40)
        r3 = classify_task(task_id="3", completion_percent=45.0)
        self.assertEqual(r3.classification, "RISK")
        self.assertTrue(r3.below_50)
        self.assertFalse(r3.below_40)
        r50 = classify_task(task_id="50", completion_percent=50.0)
        self.assertTrue(r50.below_50)

    def test_sanitizer_strips_technical_tokens(self):
        from apps.vpr.narrative import sanitize_text

        text = sanitize_text(
            "FACT: SYSTEM_ANALYTICS evidence_status=ESTABLISHED catalog=PARTIAL "
            "LIMITED_SAMPLE EDUCATIONAL_DEFICIT"
        )
        self.assertNotIn("SYSTEM_ANALYTICS", text)
        self.assertNotIn("evidence_status=", text)
        self.assertNotIn("catalog=", text)
        self.assertNotIn("LIMITED_SAMPLE", text)
        self.assertIn("образовательный дефицит", text)

    def test_not_available_not_zero(self):
        from apps.vpr.deficits.config import load_deficit_thresholds

        level = load_deficit_thresholds().classify(None)
        self.assertEqual(level.code, "not_available")
        self.assertNotEqual(level.code, "critical")

    def test_narrative_quality_flags_leak(self):
        from apps.vpr.validation.narrative import NarrativeQualityValidator

        report = SimpleNamespace(
            passport_assessment=["SYSTEM_ANALYTICS groups"],
            action_plan=[],
            individual_cycle=None,
            marks_cycle=None,
            objectivity_cycle=None,
            scores_cycle=None,
            content_cycle=None,
            planned_cycle=None,
            group_task_cycle=None,
            deficits_cycle=None,
            admin_cycle=None,
            method_cycle=None,
            individual_groups=[],
            deficit_items=[],
        )
        result = NarrativeQualityValidator().validate(report)
        self.assertFalse(result.ok)
        self.assertTrue(any(e.code == "narrative.technical_leak" for e in result.errors))
