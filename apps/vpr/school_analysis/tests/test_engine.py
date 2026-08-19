"""Тесты комплексной аналитики школы по ВПР."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.vpr.analytics.result import (
    VprAnalyticsResult,
    VprMarksDistribution,
    VprScoresDistribution,
    VprSkillAnalytics,
    VprStudentAnalytics,
    VprSummaryMetrics,
    VprTaskAnalytics,
    VprTopicAnalytics,
)
from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
from apps.vpr.deficits import VprDeficitEngine
from apps.vpr.school_analysis import VprSchoolAnalysisEngine
from apps.vpr.school_analysis.dynamics import INSUFFICIENT, SchoolDynamicsAnalyzer
from apps.vpr.school_analysis.risk import CLASS_HIGH, CLASS_STABLE
from apps.vpr.school_analysis.serializers import serialize_school_analysis
from apps.vpr.services.catalog_import import import_catalog_file
from apps.vpr.services.import_service import VprImportService
from organizations.models import District, Ministry, School

User = get_user_model()
PROTOCOL_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "Ф1_Индивидуальные_результаты.xlsx"
CATALOG_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "vpr_task_catalog_sample.json"


def _summary(**overrides) -> VprSummaryMetrics:
    base = dict(
        participants_count=20,
        max_primary_score=20,
        avg_primary_score=14.0,
        min_primary_score=5.0,
        max_primary_result=20.0,
        avg_mark_vpr=3.5,
        avg_mark_journal=3.6,
        knowledge_quality_percent=50.0,
        absolute_achievement_percent=80.0,
        median_primary_score=14.0,
        mode_primary_score=14.0,
        stdev_primary_score=3.0,
        cv_primary_score_percent=20.0,
    )
    base.update(overrides)
    return VprSummaryMetrics(**base)


def _task(code: str, *, pct: float, topic: str, skill: str, position: int = 1) -> VprTaskAnalytics:
    return VprTaskAnalytics(
        task_code=code,
        task_number=code,
        position=position,
        max_score=2,
        avg_score=round(2 * pct / 100, 2),
        completion_percent=pct,
        full_count=0,
        partial_count=0,
        zero_count=0,
        answers_count=20,
        topic=topic,
        program_section="Раздел",
        checked_skill=skill,
        difficulty="Базовый",
        catalog_matched=True,
    )


def _analytics(
    *,
    subject: str,
    parallel: int,
    year: int,
    summary: VprSummaryMetrics,
    tasks: list[VprTaskAnalytics],
    students: list[VprStudentAnalytics] | None = None,
) -> VprAnalyticsResult:
    topics_map: dict[str, list[VprTaskAnalytics]] = {}
    skills_map: dict[str, list[VprTaskAnalytics]] = {}
    for task in tasks:
        topics_map.setdefault(task.topic, []).append(task)
        skills_map.setdefault(task.checked_skill, []).append(task)
    return VprAnalyticsResult(
        protocol_id=1,
        subject=subject,
        parallel=parallel,
        academic_year=year,
        organization_name="Тест ОО",
        summary=summary,
        marks=VprMarksDistribution(vpr={"2": 2, "3": 6, "4": 8, "5": 4}),
        scores=VprScoresDistribution(),
        tasks=tasks,
        topics=[
            VprTopicAnalytics(
                topic=name,
                tasks_count=len(items),
                avg_completion_percent=sum(t.completion_percent or 0 for t in items) / len(items),
                avg_score=None,
                errors_count=0,
                task_codes=[t.task_code for t in items],
            )
            for name, items in topics_map.items()
        ],
        skills=[
            VprSkillAnalytics(
                checked_skill=name,
                tasks_count=len(items),
                avg_completion_percent=sum(t.completion_percent or 0 for t in items) / len(items),
                avg_score=None,
                task_codes=[t.task_code for t in items],
            )
            for name, items in skills_map.items()
        ],
        students=students
        or [
            VprStudentAnalytics(
                participant_code="1",
                full_name="Ученик",
                class_group=f"{parallel}А",
                gender="",
                primary_score=summary.avg_primary_score,
                mark_vpr=4,
                mark_journal=4,
                completion_percent=70.0,
                avg_task_score=None,
                place_overall=1,
                place_in_class=1,
            )
        ],
    )


def _comprehensive(analytics: VprAnalyticsResult):
    deficits = VprDeficitEngine().analyze(analytics)
    return VprComprehensiveAnalysisEngine().analyze_from_parts(analytics, deficits=deficits)


class SchoolAnalysisUnitTests(TestCase):
    def test_empty_data(self):
        school = School.objects.create(
            district=District.objects.create(
                ministry=Ministry.objects.create(name="M"),
                code="sa0",
                name="D",
            ),
            code="empty-school",
            name="Пустая школа",
        )
        result = VprSchoolAnalysisEngine(use_cache=False).analyze(school, 2026)
        self.assertFalse(result.overview.has_data)
        self.assertEqual(result.overview.protocols_count, 0)
        self.assertFalse(result.dynamics.available)
        self.assertEqual(result.dynamics.message, INSUFFICIENT)

    def test_one_protocol_aggregation(self):
        analytics = _analytics(
            subject="Русский язык",
            parallel=4,
            year=2026,
            summary=_summary(avg_primary_score=16, knowledge_quality_percent=70),
            tasks=[
                _task("1", pct=90, topic="Орфоэпия", skill="Ударение"),
                _task("2", pct=40, topic="Орфография", skill="Правописание", position=2),
            ],
        )
        analyses = [_comprehensive(analytics)]
        engine = VprSchoolAnalysisEngine(use_cache=False)
        # inject via private assembly path: mock protocols
        school = School.objects.create(
            district=District.objects.create(
                ministry=Ministry.objects.create(name="M2"),
                code="sa1",
                name="D2",
            ),
            code="one-school",
            name="Одна школа",
        )
        with mock.patch.object(engine, "_protocols_for_year", return_value=[object()]):
            with mock.patch.object(engine, "_analyze_protocol", return_value=analyses[0]):
                with mock.patch.object(
                    engine,
                    "_build_dynamics",
                    return_value=SchoolDynamicsAnalyzer().analyze({2026: analyses}),
                ):
                    result = engine.analyze(school, 2026)

        self.assertTrue(result.overview.has_data)
        self.assertEqual(result.overview.protocols_count, 1)
        self.assertEqual(result.overview.subjects_count, 1)
        self.assertEqual(len(result.subjects), 1)
        self.assertEqual(result.subjects[0].subject, "Русский язык")
        self.assertEqual(result.grades[0].parallel, 4)
        self.assertTrue(result.weaknesses.topics)
        self.assertIn(result.risk_profile.classification, {CLASS_HIGH, "MEDIUM_RISK", "LOW_RISK", CLASS_STABLE})
        self.assertTrue(result.recommendations.actions or result.recommendations.by_subject)
        self.assertFalse(result.dynamics.available)

    def test_multiple_subjects_and_grades(self):
        a1 = _comprehensive(
            _analytics(
                subject="Русский язык",
                parallel=4,
                year=2026,
                summary=_summary(avg_primary_score=16, knowledge_quality_percent=72),
                tasks=[_task("1", pct=85, topic="Тема А", skill="Умение А")],
            )
        )
        a2 = _comprehensive(
            _analytics(
                subject="Математика",
                parallel=5,
                year=2026,
                summary=_summary(avg_primary_score=10, knowledge_quality_percent=35, participants_count=15),
                tasks=[
                    _task("1", pct=30, topic="Дроби", skill="Вычисления"),
                    _task("2", pct=25, topic="Дроби", skill="Вычисления", position=2),
                ],
            )
        )
        from apps.vpr.school_analysis.subjects import SchoolSubjectsAnalyzer
        from apps.vpr.school_analysis.grades import SchoolGradesAnalyzer

        subjects = SchoolSubjectsAnalyzer().analyze([a1, a2])
        grades = SchoolGradesAnalyzer().analyze([a1, a2])
        self.assertEqual(len(subjects), 2)
        self.assertEqual({s.subject for s in subjects}, {"Русский язык", "Математика"})
        self.assertEqual(subjects[0].rank, 1)
        self.assertEqual({g.parallel for g in grades}, {4, 5})

    def test_dynamics_multiple_years(self):
        y2025 = [
            _comprehensive(
                _analytics(
                    subject="Русский язык",
                    parallel=4,
                    year=2025,
                    summary=_summary(avg_primary_score=10, knowledge_quality_percent=40),
                    tasks=[_task("1", pct=50, topic="Т", skill="У")],
                )
            )
        ]
        y2026 = [
            _comprehensive(
                _analytics(
                    subject="Русский язык",
                    parallel=4,
                    year=2026,
                    summary=_summary(avg_primary_score=16, knowledge_quality_percent=70),
                    tasks=[_task("1", pct=80, topic="Т", skill="У")],
                )
            )
        ]
        dyn = SchoolDynamicsAnalyzer().analyze({2025: y2025, 2026: y2026})
        self.assertTrue(dyn.available)
        self.assertEqual(len(dyn.points), 2)
        self.assertEqual(dyn.points[0].trend, "baseline")
        self.assertEqual(dyn.points[1].trend, "up")

    def test_overview_weighted_metrics_and_unique_participants(self):
        a_heavy = _comprehensive(
            _analytics(
                subject="Математика",
                parallel=4,
                year=2026,
                summary=_summary(
                    participants_count=100,
                    avg_primary_score=20,
                    knowledge_quality_percent=60,
                    absolute_achievement_percent=90,
                ),
                tasks=[_task("1", pct=80, topic="Тема А", skill="Умение А")],
            )
        )
        a_light = _comprehensive(
            _analytics(
                subject="История",
                parallel=5,
                year=2026,
                summary=_summary(
                    participants_count=10,
                    avg_primary_score=5,
                    knowledge_quality_percent=20,
                    absolute_achievement_percent=50,
                ),
                tasks=[_task("1", pct=30, topic="Тема Б", skill="Умение Б")],
            )
        )
        from apps.vpr.school_analysis.overview import SchoolOverviewBuilder

        overview = SchoolOverviewBuilder().build(
            [a_heavy, a_light],
            organization_name="Школа",
            academic_year=2026,
        )
        # 100 участников @ 80% vs 10 @ 30% => взвешенное ~75.45%, не простое 55%
        self.assertGreater(overview.avg_completion_percent or 0, 70)
        self.assertAlmostEqual(overview.avg_quality_percent or 0, 56.36, places=1)
        self.assertAlmostEqual(overview.avg_absolute_percent or 0, 86.36, places=1)

    def test_risk_high_classification(self):
        analyses = [
            _comprehensive(
                _analytics(
                    subject="История",
                    parallel=6,
                    year=2026,
                    summary=_summary(
                        avg_primary_score=6,
                        knowledge_quality_percent=25,
                        participants_count=30,
                    ),
                    tasks=[
                        _task("1", pct=20, topic="Даты", skill="Хронология"),
                        _task("2", pct=15, topic="Даты", skill="Хронология", position=2),
                        _task("3", pct=18, topic="Карты", skill="Анализ", position=3),
                    ],
                    students=[
                        VprStudentAnalytics(
                            participant_code=str(i),
                            full_name="",
                            class_group="6А",
                            gender="",
                            primary_score=6,
                            mark_vpr=2,
                            mark_journal=3,
                            completion_percent=30.0,
                            avg_task_score=None,
                            place_overall=i,
                            place_in_class=i,
                        )
                        for i in range(20)
                    ],
                )
            )
        ]
        from apps.vpr.school_analysis.deficits import SchoolDeficitsAggregator
        from apps.vpr.school_analysis.overview import SchoolOverviewBuilder
        from apps.vpr.school_analysis.risk import SchoolRiskClassifier

        overview = SchoolOverviewBuilder().build(
            analyses, organization_name="Школа", academic_year=2026
        )
        deficits = SchoolDeficitsAggregator().analyze(analyses)
        risk = SchoolRiskClassifier().classify(
            overview=overview, deficits=deficits, analyses=analyses
        )
        self.assertEqual(risk.classification, CLASS_HIGH)

    def test_serialize_shape(self):
        analyses = [
            _comprehensive(
                _analytics(
                    subject="Биология",
                    parallel=7,
                    year=2026,
                    summary=_summary(),
                    tasks=[_task("1", pct=70, topic="Клетка", skill="Строение")],
                )
            )
        ]
        school = School.objects.create(
            district=District.objects.create(
                ministry=Ministry.objects.create(name="M3"),
                code="sa3",
                name="D3",
            ),
            code="ser-school",
            name="Сериализация",
        )
        engine = VprSchoolAnalysisEngine(use_cache=False)
        with mock.patch.object(engine, "_protocols_for_year", return_value=[object()]):
            with mock.patch.object(engine, "_analyze_protocol", return_value=analyses[0]):
                with mock.patch.object(
                    engine,
                    "_build_dynamics",
                    return_value=SchoolDynamicsAnalyzer().analyze({2026: analyses}),
                ):
                    result = engine.analyze(school, 2026)
        payload = serialize_school_analysis(result)
        for key in (
            "overview",
            "subjects",
            "grades",
            "strengths",
            "weaknesses",
            "deficits",
            "risk_profile",
            "recommendations",
            "dynamics",
        ):
            self.assertIn(key, payload)


class SchoolAnalysisIntegrationTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="School Analysis Ministry")
        district = District.objects.create(ministry=ministry, code="sax", name="SA District")
        self.school = School.objects.create(
            district=district,
            code="vpr-sa-school",
            name='МБОУ «СОШ №1 г.Урус-Мартан»',
        )
        self.user = User.objects.create_user(
            username="vpr_sa_user",
            password="pass12345",
            role="school",
            school=self.school,
        )
        if CATALOG_FIXTURE.exists():
            import_catalog_file(CATALOG_FIXTURE)
        self.service = VprImportService()
        self.client = Client()
        self.client.login(username="vpr_sa_user", password="pass12345")

    def _import(self, suffix: str):
        uploaded = SimpleUploadedFile(
            f"f1_sa_{suffix}.xlsx",
            PROTOCOL_FIXTURE.read_bytes(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        upload = self.service.create_upload(
            user=self.user,
            uploaded_file=uploaded,
            school=self.school,
        )
        self.service.validate_and_preview(upload)
        self.service.confirm_import(upload)
        upload.refresh_from_db()
        return upload.protocol

    def test_engine_on_real_protocol(self):
        protocol = self._import("one")
        result = VprSchoolAnalysisEngine(use_cache=False).analyze(self.school, protocol.academic_year)
        self.assertTrue(result.overview.has_data)
        self.assertGreaterEqual(result.overview.protocols_count, 1)
        self.assertGreater(result.overview.participants_total, 0)
        self.assertTrue(result.subjects)
        self.assertTrue(result.grades)

    def test_multiple_protocols_subjects_years(self):
        p1 = self._import("a")
        p2 = self._import("b")
        p2.subject = "Математика"
        p2.parallel = 5
        p2.academic_year = p1.academic_year
        p2.save(update_fields=["subject", "parallel", "academic_year"])
        p3 = self._import("c")
        p3.subject = "История"
        p3.academic_year = p1.academic_year - 1
        p3.save(update_fields=["subject", "academic_year"])

        result = VprSchoolAnalysisEngine(use_cache=False).analyze(self.school, p1.academic_year)
        self.assertGreaterEqual(result.overview.subjects_count, 2)
        names = {row.subject for row in result.subjects}
        self.assertIn("Русский язык", names)
        self.assertIn("Математика", names)
        self.assertTrue(result.dynamics.available)
        years = {point.academic_year for point in result.dynamics.points}
        self.assertIn(p1.academic_year, years)
        self.assertIn(p3.academic_year, years)

    def test_school_page_loads(self):
        self._import("page")
        response = self.client.get(reverse("vpr-school-analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("analysis", response.context)
        self.assertContains(response, "Аналитика школы")
        self.assertContains(response, "Общая характеристика")
        self.assertContains(response, "Предметы")
        self.assertContains(response, "Профиль риска")
        self.assertContains(response, "Динамика")
        self.assertContains(response, "Скачать в Word")

    def test_docx_download(self):
        protocol = self._import("docx")
        url = reverse("vpr-school-analytics-docx")
        response = self.client.get(url, {"year": protocol.academic_year})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertIn(".docx", response["Content-Disposition"])
        # FileResponse may stream; collect content
        content = b"".join(response.streaming_content)
        self.assertGreater(len(content), 1000)
        self.assertTrue(content[:2] == b"PK")  # zip/docx signature
