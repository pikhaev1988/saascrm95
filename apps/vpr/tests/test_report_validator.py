"""Тесты VPR_REPORT_VALIDATOR (этап 4) — только mock/fixture, без production id."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.vpr.analytics.result import (
    VprAnalyticsResult,
    VprMarksDistribution,
    VprScoresDistribution,
    VprStudentAnalytics,
    VprSummaryMetrics,
    VprTaskAnalytics,
)
from apps.vpr.comprehensive_analysis.schemas import (
    VprGroupBucket,
    VprObjectivityProfile,
    VprParticipantGroupsProfile,
)
from apps.vpr.expert_analysis.fioko_report import (
    AnalyticCycle,
    DeficitInsight,
    PlanRow,
    PlannedResultRow,
    SubjectReport,
    TaskPerformanceRow,
)
from apps.vpr.validation.report_validator import (
    VprReportBlockedError,
    VprReportValidator,
)


def _summary(**kw) -> VprSummaryMetrics:
    base = dict(
        participants_count=4,
        max_primary_score=20,
        avg_primary_score=12.0,
        min_primary_score=8.0,
        max_primary_result=18.0,
        avg_mark_vpr=3.5,
        avg_mark_journal=3.5,
        knowledge_quality_percent=50.0,
        absolute_achievement_percent=75.0,
        median_primary_score=12.0,
        mode_primary_score=12.0,
        stdev_primary_score=2.0,
        cv_primary_score_percent=16.0,
    )
    base.update(kw)
    return VprSummaryMetrics(**base)


def _student(code: str, score: float | None = 12.0, mark: int = 3) -> VprStudentAnalytics:
    return VprStudentAnalytics(
        participant_code=code,
        full_name=code,
        class_group="5А",
        gender="",
        primary_score=score,
        mark_vpr=mark,
        mark_journal=mark,
        completion_percent=60.0 if score is not None else None,
        avg_task_score=None,
        place_overall=None,
        place_in_class=None,
    )


def _task(
    code: str,
    *,
    n: int = 4,
    full: int = 1,
    partial: int = 1,
    zero: int = 2,
    max_score: int = 2,
    completion: float = 40.0,
) -> VprTaskAnalytics:
    return VprTaskAnalytics(
        task_code=code,
        task_number=code,
        position=int(code) if str(code).isdigit() else 1,
        max_score=max_score,
        avg_score=0.8,
        completion_percent=completion,
        full_count=full,
        partial_count=partial,
        zero_count=zero,
        answers_count=n,
        correct_count=full,
        incorrect_count=zero,
        total_students=n,
        full_score_count=full,
        partial_score_count=partial,
        zero_score_count=zero,
        earned_points_sum=3.2,
        max_points_sum=float(max_score * n),
        mean_score=0.8,
        full_score_rate=round(100.0 * full / n, 2),
        partial_score_rate=round(100.0 * partial / n, 2),
        zero_score_rate=round(100.0 * zero / n, 2),
    )


def _groups(high=1, medium=1, risk=2, codes=None) -> VprParticipantGroupsProfile:
    codes = codes or {
        "high": ["a"],
        "medium": ["b"],
        "risk": ["c", "d"],
    }
    total = high + medium + risk
    return VprParticipantGroupsProfile(
        groups={
            "high": VprGroupBucket(count=high, percent=round(100 * high / total, 1), participant_codes=codes["high"]),
            "medium": VprGroupBucket(
                count=medium, percent=round(100 * medium / total, 1), participant_codes=codes["medium"]
            ),
            "risk": VprGroupBucket(count=risk, percent=round(100 * risk / total, 1), participant_codes=codes["risk"]),
        },
        positive_potential_codes=["a"],
        data_incomplete=False,
        validation_ok=True,
    )


def _analysis(**overrides):
    students = [
        _student("a", 18, 5),
        _student("b", 12, 4),
        _student("c", 8, 3),
        _student("d", 8, 2),
    ]
    tasks = [_task("1"), _task("3", full=0, partial=2, zero=2, completion=25.5)]
    analytics = VprAnalyticsResult(
        protocol_id=1,
        subject="Биология",
        parallel=5,
        academic_year=2026,
        organization_name="Test",
        summary=_summary(),
        marks=VprMarksDistribution(vpr={"5": 1, "4": 1, "3": 1, "2": 1}),
        scores=VprScoresDistribution(counts={"8": 2, "12": 1, "18": 1}),
        tasks=tasks,
        topics=[],
        skills=[],
        students=students,
    )
    obj = VprObjectivityProfile(
        journal_comparison={"equal": 2, "lower": 1, "higher": 1},
        journal_comparison_percents={"equal": 50.0, "lower": 25.0, "higher": 25.0},
        compared_count=4,
        risk_level="medium",
    )
    base = SimpleNamespace(
        summary=analytics.summary,
        analytics=analytics,
        participant_groups=_groups(),
        objectivity=obj,
        deficits=SimpleNamespace(topics=[], skills=[], tasks=[], students=[]),
        task_rows=[],
        topic_rows=[],
        skill_rows=[],
        subject="Биология",
        parallel=5,
        academic_year=2026,
        organization_name="Test",
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def _minimal_report(**overrides) -> SubjectReport:
    report = SubjectReport(
        subject="Биология",
        parallel=5,
        academic_year=2026,
        quality_level="профиль повышенного риска",
        passport=[SimpleNamespace(label="N", value="4")],  # type: ignore[list-item]
        passport_assessment=["ok"],
        individual_groups=[],
        marks_rows=[],
        objectivity_cycle=AnalyticCycle(interpretation=["признаки риска расхождения"]),
        scores_rows=[],
        task_performance_rows=[
            TaskPerformanceRow(
                task_code="3",
                max_score=2,
                mean_score=0.5,
                completion_percent=25.5,
                full_score_count=0,
                partial_count=2,
                zero_score_count=2,
                answers_count=4,
                full_score_rate=0.0,
                partial_score_rate=50.0,
                zero_score_rate=50.0,
            )
        ],
        content_pipeline=[
            "Задание №3: полного выполнения не достиг ни один участник; "
            "при этом зафиксировано частичное выполнение у 2 чел."
        ],
        planned_results=[
            PlannedResultRow(
                result="PR1",
                status="not_achieved",
                status_label="не достигнут",
                average_percent=25.5,
                tasks_count=1,
                explanation="partial aware",
                linked_tasks=["3"],
                evidence="linked_tasks=3",
            )
        ],
        group_task_insights=[],
        deficit_items=[
            DeficitInsight(
                name="Тема X",
                kind="тема",
                priority="High",
                average_percent=40.0,
                impact_results="impact",
                impact_quality="q",
                impact_program="p",
                evidence="completion=40%",
                linked_tasks=["3"],
            )
        ],
        admin_director=["a"],
        smo_actions=["a"],
        teacher_deficits=["предполагаемая зона профессионального методического риска"],
        parent_actions=["a"],
        method_recommendations=["Дефицит «Тема X» (baseline 40%): еженедельно включать..."],
        action_plan=[
            PlanRow(
                action="Мониторинг",
                executor="Зам",
                deadline="месяц",
                expected_result="Рост выполнения 40% → 50%",
                efficiency_indicator="completion",
                kpi="completion приоритетного дефицита",
                baseline_value="40%",
                target_value="50%",
                problem="дефицит",
            )
        ],
        final_conclusion=["Профиль", "Доказанные проблемы", "KPI"],
    )
    # KpiItem-compatible passport
    from apps.vpr.expert_analysis.fioko_report import KpiItem

    report.passport = [KpiItem("Участники", "4")]
    for k, v in overrides.items():
        setattr(report, k, v)
    return report


class VprReportValidatorTests(SimpleTestCase):
    def setUp(self):
        self.validator = VprReportValidator()

    def test_valid_report(self):
        analysis = _analysis()
        report = _minimal_report()
        expert = SimpleNamespace(
            profile_code="elevated_risk",
            profile_label="профиль повышенного риска",
            profile_explanation=["evidence line"],
        )
        result = self.validator.validate(analysis, report, expert=expert)
        self.assertTrue(result.valid, result.errors)
        self.assertGreaterEqual(result.summary["checks_total"], 10)

    def test_group_sum_mismatch(self):
        analysis = _analysis(participant_groups=_groups(high=1, medium=1, risk=1))
        result = self.validator.validate(analysis, _minimal_report())
        self.assertFalse(result.valid)
        self.assertTrue(any("high+medium+risk" in e for e in result.errors))

    def test_task_count_mismatch(self):
        bad = _task("1", full=1, partial=1, zero=0, n=4)
        analysis = _analysis()
        analysis.analytics.tasks = [bad]
        result = self.validator.validate(analysis, _minimal_report())
        self.assertFalse(result.valid)
        self.assertTrue(any("full+partial+zero" in e for e in result.errors))

    def test_percentage_over_100(self):
        t = _task("1")
        t.full_score_rate = 120.0
        analysis = _analysis()
        analysis.analytics.tasks = [t]
        result = self.validator.validate(analysis, _minimal_report())
        self.assertFalse(result.valid)
        self.assertTrue(any("out of [0,100]" in e for e in result.errors))

    def test_percentage_under_0(self):
        t = _task("1")
        t.zero_score_rate = -1.0
        analysis = _analysis()
        analysis.analytics.tasks = [t]
        result = self.validator.validate(analysis, _minimal_report())
        self.assertFalse(result.valid)

    def test_marks_sum_mismatch(self):
        analysis = _analysis()
        analysis.analytics.marks = VprMarksDistribution(vpr={"5": 1, "4": 1, "3": 0, "2": 0})
        result = self.validator.validate(analysis, _minimal_report())
        self.assertFalse(result.valid)
        self.assertTrue(any("marks 2+3+4+5" in e for e in result.errors))

    def test_objectivity_mismatch(self):
        analysis = _analysis()
        analysis.objectivity = VprObjectivityProfile(
            journal_comparison={"equal": 1, "lower": 1, "higher": 0},
            journal_comparison_percents={"equal": 50.0, "lower": 50.0, "higher": 0.0},
            compared_count=4,
            risk_level="low",
        )
        result = self.validator.validate(analysis, _minimal_report())
        self.assertFalse(result.valid)
        self.assertTrue(any("equal+lower+higher" in e for e in result.errors))

    def test_missing_planned_result_warning(self):
        report = _minimal_report(planned_results=[])
        result = self.validator.validate(_analysis(), report)
        self.assertTrue(any(c.check_code == "planned.present" for c in result.checks))

    def test_deficit_without_evidence(self):
        report = _minimal_report(
            deficit_items=[
                DeficitInsight(
                    name="NoEvidence",
                    kind="тема",
                    priority="High",
                    average_percent=30.0,
                    impact_results="",
                    impact_quality="",
                    impact_program="",
                    evidence="",
                )
            ]
        )
        result = self.validator.validate(_analysis(), report)
        self.assertFalse(result.valid)
        self.assertTrue(any("without evidence" in e for e in result.errors))

    def test_missing_kpi(self):
        report = _minimal_report(
            action_plan=[
                PlanRow(
                    action="X",
                    executor="Y",
                    deadline="Z",
                    expected_result="R",
                    efficiency_indicator="",
                    kpi="",
                )
            ]
        )
        result = self.validator.validate(_analysis(), report)
        self.assertFalse(result.valid)
        self.assertTrue(any("without KPI" in e for e in result.errors))

    def test_invalid_profile(self):
        expert = SimpleNamespace(profile_code="unknown_profile", profile_explanation=["x"])
        result = self.validator.validate(_analysis(), _minimal_report(), expert=expert)
        self.assertFalse(result.valid)
        self.assertTrue(any("invalid profile" in e for e in result.errors))

    def test_missing_section(self):
        report = _minimal_report(final_conclusion=[])
        result = self.validator.validate(_analysis(), report)
        self.assertFalse(result.valid)
        self.assertTrue(any("16. Итоговое заключение" in e for e in result.errors))

    def test_partial_task_wording_conflict(self):
        report = _minimal_report(
            content_pipeline=["умение не сформировано по заданию 3"],
            planned_results=[
                PlannedResultRow(
                    result="PR",
                    status="not_achieved",
                    status_label="не достигнут",
                    average_percent=20.0,
                    tasks_count=1,
                    explanation="не сформированы ключевые знания",
                    linked_tasks=["3"],
                    evidence="x",
                )
            ],
        )
        result = self.validator.validate(_analysis(), report)
        self.assertFalse(result.valid)
        self.assertTrue(any(c.check_code == "wording.partial_not_formed" for c in result.checks if c.severity == "error"))

    def test_validate_or_raise(self):
        analysis = _analysis(participant_groups=_groups(high=2, medium=0, risk=0))
        with self.assertRaises(VprReportBlockedError):
            self.validator.validate_or_raise(analysis, _minimal_report())
