"""Тесты комплексного аналитического профиля ВПР."""

from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

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
from apps.vpr.comprehensive_analysis import VprComprehensiveAnalysisEngine
from apps.vpr.comprehensive_analysis.school_profile import (
    CLASS_HIGH,
    CLASS_LOW,
    CLASS_OBJECTIVITY,
)
from apps.vpr.comprehensive_analysis.serializers import serialize_comprehensive_result
from apps.vpr.comprehensive_analysis.tasks import STATUS_CRITICAL, STATUS_HIGH
from apps.vpr.deficits import VprDeficitEngine
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


def _task(
    code: str,
    *,
    pct: float,
    topic: str = "",
    skill: str = "",
    section: str = "",
    difficulty: str = "Базовый",
    position: int = 1,
    catalog_matched: bool | None = None,
) -> VprTaskAnalytics:
    matched = bool(topic or skill) if catalog_matched is None else catalog_matched
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
        program_section=section,
        checked_skill=skill,
        difficulty=difficulty,
        catalog_matched=matched,
    )


def _student(
    code: str,
    *,
    pct: float,
    mark_vpr: int | None = 4,
    mark_journal: int | None = 4,
    primary: float | None = None,
) -> VprStudentAnalytics:
    return VprStudentAnalytics(
        participant_code=code,
        full_name=f"Ученик {code}",
        class_group="4А",
        gender="",
        primary_score=primary if primary is not None else pct / 5.0,
        mark_vpr=mark_vpr,
        mark_journal=mark_journal,
        completion_percent=pct,
        avg_task_score=None,
        place_overall=None,
        place_in_class=None,
    )


def _analytics(
    summary: VprSummaryMetrics,
    tasks: list[VprTaskAnalytics],
    *,
    students: list[VprStudentAnalytics] | None = None,
    marks: VprMarksDistribution | None = None,
) -> VprAnalyticsResult:
    topics_map: dict[str, list[VprTaskAnalytics]] = {}
    skills_map: dict[str, list[VprTaskAnalytics]] = {}
    for task in tasks:
        topics_map.setdefault(task.topic or "Без темы в справочнике", []).append(task)
        skills_map.setdefault(task.checked_skill or "Без умения в справочнике", []).append(task)

    return VprAnalyticsResult(
        protocol_id=1,
        subject="Русский язык",
        parallel=4,
        academic_year=2026,
        organization_name="Тест ОО",
        summary=summary,
        marks=marks or VprMarksDistribution(vpr={"2": 2, "3": 6, "4": 8, "5": 4}),
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
        students=students or [],
    )


class VprComprehensiveUnitTests(TestCase):
    def setUp(self):
        self.engine = VprComprehensiveAnalysisEngine()

    def test_high_results_profile(self):
        students = [
            _student(f"H{i}", pct=90, mark_vpr=5, mark_journal=5) for i in range(8)
        ] + [_student(f"M{i}", pct=70, mark_vpr=4, mark_journal=4) for i in range(2)]
        analytics = _analytics(
            _summary(
                avg_primary_score=17.0,
                median_primary_score=17.0,
                knowledge_quality_percent=80.0,
                cv_primary_score_percent=10.0,
                participants_count=10,
            ),
            [
                _task("1", pct=92, topic="Орфография", skill="Правописание", position=1),
                _task("2", pct=88, topic="Пунктуация", skill="Знаки препинания", position=2),
            ],
            students=students,
            marks=VprMarksDistribution(vpr={"4": 4, "5": 6}),
        )
        result = self.engine.analyze_from_parts(analytics)
        self.assertEqual(result.achievement.heterogeneity, "low")
        self.assertEqual(result.school_profile.classification, CLASS_HIGH)
        self.assertTrue(all(item.status == STATUS_HIGH for item in result.task_analysis.items))
        self.assertGreaterEqual(result.participant_groups.groups["high"].count, 8)

    def test_low_results_profile(self):
        students = [_student(f"R{i}", pct=30, mark_vpr=2, mark_journal=2) for i in range(12)]
        analytics = _analytics(
            _summary(
                avg_primary_score=7.0,
                knowledge_quality_percent=20.0,
                cv_primary_score_percent=35.0,
                participants_count=12,
            ),
            [
                _task("1", pct=25, topic="Орфография", skill="Правописание", position=1),
                _task("2", pct=30, topic="Орфография", skill="Правописание", position=2),
                _task("3", pct=28, topic="Состав слова", skill="Морфемный анализ", position=3),
            ],
            students=students,
            marks=VprMarksDistribution(vpr={"2": 8, "3": 4}),
        )
        result = self.engine.analyze_from_parts(analytics)
        self.assertEqual(result.achievement.heterogeneity, "high")
        self.assertEqual(result.school_profile.classification, CLASS_LOW)
        self.assertGreaterEqual(result.participant_groups.groups["risk"].count, 10)
        self.assertTrue(any(i.status == STATUS_CRITICAL for i in result.task_analysis.items))

    def test_mass_topic_deficit(self):
        analytics = _analytics(
            _summary(avg_primary_score=10.0, knowledge_quality_percent=30.0),
            [
                _task("3", pct=35, topic="Орфография", skill="Правописание", position=1),
                _task("4", pct=38, topic="Орфография", skill="Правописание", position=2),
                _task("5", pct=40, topic="Орфография", skill="Правописание", position=3),
            ],
            students=[_student("1", pct=40)],
        )
        result = self.engine.analyze_from_parts(analytics)
        topic = next(i for i in result.topic_analysis.items if i.topic == "Орфография")
        self.assertEqual(topic.deficit_type, "mass")
        self.assertIn("Орфография", result.topic_analysis.mass_deficits)

    def test_local_topic_deficit(self):
        analytics = _analytics(
            _summary(),
            [
                _task("1", pct=85, topic="Орфография", skill="Правописание", position=1),
                _task("2", pct=35, topic="Пунктуация", skill="Знаки препинания", position=2),
                _task("3", pct=80, topic="Лексика", skill="Значение слова", position=3),
            ],
            students=[_student("1", pct=70)],
        )
        result = self.engine.analyze_from_parts(analytics)
        punct = next(i for i in result.topic_analysis.items if i.topic == "Пунктуация")
        self.assertEqual(punct.deficit_type, "local")
        self.assertIn("Пунктуация", result.topic_analysis.local_deficits)
        ortho = next(i for i in result.topic_analysis.items if i.topic == "Орфография")
        self.assertEqual(ortho.deficit_type, "none")

    def test_missing_catalog(self):
        analytics = _analytics(
            _summary(),
            [
                _task("1", pct=40, topic="", skill="", catalog_matched=False, position=1),
                _task("2", pct=55, topic="", skill="", catalog_matched=False, position=2),
            ],
            students=[_student("1", pct=50)],
        )
        result = self.engine.analyze_from_parts(analytics)
        self.assertEqual(result.task_analysis.catalog_coverage, "none")
        self.assertTrue(all(i.topic == "Без темы в справочнике" for i in result.task_analysis.items))
        self.assertTrue(result.recommendations.actions)

    def test_topics_and_skills_correct(self):
        analytics = _analytics(
            _summary(),
            [
                _task(
                    "6",
                    pct=45,
                    topic="Работа с текстом",
                    skill="Поиск информации в тексте",
                    section="Развитие речи",
                    position=1,
                ),
                _task(
                    "7",
                    pct=42,
                    topic="Работа с текстом",
                    skill="Поиск информации в тексте",
                    section="Развитие речи",
                    position=2,
                ),
            ],
            students=[_student("1", pct=45)],
        )
        result = self.engine.analyze_from_parts(analytics)
        self.assertEqual(result.task_analysis.items[0].topic, "Работа с текстом")
        self.assertEqual(result.task_analysis.items[0].skill, "Поиск информации в тексте")
        skill = next(i for i in result.skill_analysis.items if "Поиск информации" in i.skill)
        self.assertEqual(skill.level, "low")
        self.assertIn("Поиск информации в тексте", result.skill_analysis.underformed)

    def test_recommendations_link_deficit_to_actions(self):
        analytics = _analytics(
            _summary(avg_primary_score=9.0, knowledge_quality_percent=25.0),
            [
                _task("3", pct=30, topic="Орфография", skill="Правописание", position=1),
                _task("4", pct=32, topic="Орфография", skill="Правописание", position=2),
            ],
            students=[_student("1", pct=30)],
        )
        result = self.engine.analyze_from_parts(analytics)
        self.assertTrue(result.recommendations.items)
        joined = " ".join(result.recommendations.actions)
        self.assertIn("Орфография", joined)
        self.assertIn("методического объединения", joined)

    def test_objectivity_risk(self):
        students = [
            _student(f"L{i}", pct=50, mark_vpr=3, mark_journal=5) for i in range(8)
        ] + [_student(f"E{i}", pct=60, mark_vpr=4, mark_journal=4) for i in range(2)]
        analytics = _analytics(
            _summary(avg_primary_score=12.0, knowledge_quality_percent=55.0),
            [_task("1", pct=70, topic="Тема", skill="Умение", position=1)],
            students=students,
        )
        result = self.engine.analyze_from_parts(analytics)
        self.assertEqual(result.objectivity.journal_comparison["lower"], 8)
        self.assertIn(result.objectivity.risk_level, {"medium", "high"})
        self.assertIn(
            result.school_profile.classification,
            {CLASS_OBJECTIVITY, CLASS_LOW, "ATTENTION_REQUIRED"},
        )

    def test_serialize_shape(self):
        analytics = _analytics(
            _summary(),
            [_task("1", pct=80, topic="Тема", skill="Умение")],
            students=[_student("1", pct=80)],
        )
        result = self.engine.analyze_from_parts(analytics)
        payload = serialize_comprehensive_result(result)
        for key in (
            "protocol",
            "achievement",
            "task_analysis",
            "topic_analysis",
            "skill_analysis",
            "participant_groups",
            "objectivity",
            "school_profile",
            "deficits",
            "causes",
            "recommendations",
            "conclusion",
        ):
            self.assertIn(key, payload)


class VprComprehensiveIntegrationTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Мин")
        district = District.objects.create(name="Район", ministry=ministry, code="comp20")
        self.school = School.objects.create(
            name='МБОУ «СОШ №1 г.Урус-Мартан»',
            code="vpr-comp-school",
            district=district,
        )
        self.user = User.objects.create_user(
            username="vpr_comp",
            password="pass12345",
            role="school",
            school=self.school,
        )
        if CATALOG_FIXTURE.exists():
            import_catalog_file(CATALOG_FIXTURE)
        self.service = VprImportService()

    def _import_protocol(self):
        if not PROTOCOL_FIXTURE.exists():
            self.skipTest("Нет фикстуры протокола ВПР")
        uploaded = SimpleUploadedFile(
            "f1_comp.xlsx",
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

    def test_full_pipeline_on_fixture(self):
        from apps.vpr.analytics import VprAnalyticsEngine

        protocol = self._import_protocol()
        result = VprComprehensiveAnalysisEngine().analyze(protocol)
        self.assertEqual(result.protocol.protocol_id, protocol.pk)
        self.assertGreater(result.achievement.participants, 0)
        self.assertTrue(result.task_analysis.items)
        self.assertIn("classification", result.school_profile.to_dict())
        self.assertTrue(result.conclusion.overview.paragraphs)
        deficits = VprDeficitEngine().analyze(
            VprAnalyticsEngine().analyze(protocol),
            protocol=protocol,
        )
        self.assertEqual(deficits.protocol_id, protocol.pk)
