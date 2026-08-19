from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.vpr.analytics import VprAnalyticsEngine
from apps.vpr.analytics.result import (
    VprAnalyticsResult,
    VprMarksDistribution,
    VprScoresDistribution,
    VprSkillAnalytics,
    VprSummaryMetrics,
    VprTaskAnalytics,
    VprTopicAnalytics,
)
from apps.vpr.conclusion import VprConclusionEngine
from apps.vpr.deficits import VprDeficitEngine
from apps.vpr.deficits.result import VprDeficitResult, VprDeficitSummary
from apps.vpr.services.catalog_import import import_catalog_file
from apps.vpr.services.import_service import VprImportService
from organizations.models import District, Ministry, School

User = get_user_model()
PROTOCOL_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "Ф1_Индивидуальные_результаты.xlsx"
ALT_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "vpr_f1_sample.xlsx"
CATALOG_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "vpr_task_catalog_sample.json"

# маркеры «сырых» цифр, которых не должно быть в экспертном тексте
RAW_METRIC_PATTERNS = (
    "средний первичный балл составил",
    "качество знаний составило",
    "абсолютная успеваемость —",
    "выявлено:",
    "критических дефицитов —",
    "коэффициент вариации равен",
)


def _summary(**overrides) -> VprSummaryMetrics:
    base = dict(
        participants_count=10,
        max_primary_score=20,
        avg_primary_score=16.0,
        min_primary_score=10.0,
        max_primary_result=20.0,
        avg_mark_vpr=4.2,
        avg_mark_journal=4.0,
        knowledge_quality_percent=80.0,
        absolute_achievement_percent=100.0,
        median_primary_score=16.0,
        mode_primary_score=16.0,
        stdev_primary_score=2.0,
        cv_primary_score_percent=12.5,
    )
    base.update(overrides)
    return VprSummaryMetrics(**base)


def _task(
    code: str,
    *,
    pct: float,
    topic: str,
    skill: str,
    difficulty: str = "базовый",
    position: int = 1,
) -> VprTaskAnalytics:
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
        answers_count=10,
        topic=topic,
        checked_skill=skill,
        program_section="Раздел",
        difficulty=difficulty,
    )


def _analytics(
    summary: VprSummaryMetrics,
    tasks: list[VprTaskAnalytics],
    *,
    marks: dict[str, int] | None = None,
) -> VprAnalyticsResult:
    mark_counts = marks or {"5": 4, "4": 4, "3": 2, "2": 0}
    total = sum(mark_counts.values()) or 1
    return VprAnalyticsResult(
        protocol_id=1,
        subject="Русский язык",
        parallel=4,
        academic_year=2026,
        organization_name="Тестовая школа",
        summary=summary,
        marks=VprMarksDistribution(
            vpr=mark_counts,
            vpr_percents={k: round(v / total * 100, 2) for k, v in mark_counts.items()},
        ),
        scores=VprScoresDistribution(),
        tasks=tasks,
        topics=[
            VprTopicAnalytics(
                topic=t.topic or "Тема",
                tasks_count=1,
                avg_completion_percent=t.completion_percent,
                avg_score=t.avg_score,
                errors_count=0,
                task_codes=[t.task_code],
            )
            for t in tasks
        ],
        skills=[
            VprSkillAnalytics(
                checked_skill=t.checked_skill or "Умение",
                tasks_count=1,
                avg_completion_percent=t.completion_percent,
                avg_score=t.avg_score,
                task_codes=[t.task_code],
            )
            for t in tasks
        ],
        students=[],
    )


def _full_text(conclusion) -> str:
    return " ".join(p for section in conclusion.sections for p in section.paragraphs)


class VprConclusionInterpretationTests(TestCase):
    def setUp(self):
        self.engine = VprConclusionEngine()

    def test_high_results_are_interpretive_not_numeric(self):
        tasks = [
            _task("1", pct=95, topic="Орфография", skill="Применять правила", difficulty="базовый"),
            _task("2", pct=90, topic="Пунктуация", skill="Расставлять знаки", difficulty="базовый", position=2),
            _task("3", pct=85, topic="Чтение", skill="Понимать текст", difficulty="повышенный", position=3),
        ]
        analytics = _analytics(_summary(), tasks)
        deficits = VprDeficitEngine().analyze(analytics)
        conclusion = self.engine.build(analytics, deficits)
        text = _full_text(conclusion).lower()

        self.assertIn("достаточн", text)
        self.assertIn("однород", text)
        self.assertTrue(
            "стабильн" in text or "системных дефицитов не выявлено" in text
        )
        for pattern in RAW_METRIC_PATTERNS:
            self.assertNotIn(pattern, text)
        # не перечисляет "задание 1" как отчёт обзора
        self.assertNotIn("средний первичный балл составил", text)

    def test_low_results_differ_from_high(self):
        high_tasks = [
            _task("1", pct=92, topic="Орфография", skill="Применять правила"),
            _task("2", pct=88, topic="Пунктуация", skill="Расставлять знаки", position=2),
        ]
        low_tasks = [
            _task("3", pct=22, topic="Синтаксис", skill="Анализировать предложение", difficulty="повышенный"),
            _task("4", pct=35, topic="Лексика", skill="Определять значение", difficulty="повышенный", position=2),
            _task("5", pct=40, topic="Морфология", skill="Определять части речи", difficulty="базовый", position=3),
        ]
        high = self.engine.build(
            _analytics(_summary(), high_tasks),
            VprDeficitEngine().analyze(_analytics(_summary(), high_tasks)),
        )
        low_summary = _summary(
            avg_primary_score=6.0,
            knowledge_quality_percent=22.0,
            absolute_achievement_percent=40.0,
            median_primary_score=5.0,
            cv_primary_score_percent=48.0,
            stdev_primary_score=4.5,
        )
        low_analytics = _analytics(
            low_summary,
            low_tasks,
            marks={"5": 0, "4": 1, "3": 3, "2": 6},
        )
        low = self.engine.build(low_analytics, VprDeficitEngine().analyze(low_analytics))

        high_text = _full_text(high)
        low_text = _full_text(low)
        self.assertNotEqual(high_text, low_text)
        low_l = low_text.lower()
        self.assertTrue(
            "ниже ожидаемого" in low_l
            or "критически низк" in low_l
            or "выраженные затруднения" in low_l
            or "недостаточн" in low_l
        )
        self.assertTrue("системн" in low_l or "массовый" in low_l or "недостаточн" in low_l)
        self.assertIn("Синтаксис", low_text)
        self.assertNotIn("Синтаксис", high_text)

    def test_section_titles_match_expert_structure(self):
        analytics = _analytics(_summary(), [_task("1", pct=70, topic="Тема", skill="Умение")])
        conclusion = self.engine.build(analytics, VprDeficitEngine().analyze(analytics))
        titles = [s.title for s in conclusion.sections]
        self.assertEqual(
            titles,
            [
                "Общая оценка результатов",
                "Анализ статистических показателей",
                "Анализ качества подготовки",
                "Анализ выполнения заданий",
                "Анализ тем",
                "Анализ проверяемых умений",
                "Анализ образовательных дефицитов",
                "Итоговая аналитическая оценка",
            ],
        )

    def test_no_recommendations(self):
        tasks = [_task("1", pct=30, topic="Тема A", skill="Умение A", difficulty="повышенный")]
        analytics = _analytics(
            _summary(knowledge_quality_percent=30.0, avg_primary_score=5.0, cv_primary_score_percent=40.0),
            tasks,
            marks={"2": 7, "3": 2, "4": 1, "5": 0},
        )
        conclusion = self.engine.build(analytics, VprDeficitEngine().analyze(analytics))
        text = _full_text(conclusion).lower()
        for word in ("рекоменд", "следует", "необходимо провести", "план мероприятий", "предлагается"):
            self.assertNotIn(word, text)

    def test_quality_and_spread_interpretation_change_with_cv(self):
        tasks = [_task("1", pct=70, topic="Тема", skill="Умение")]
        homogeneous = self.engine.build(
            _analytics(_summary(cv_primary_score_percent=10.0), tasks),
            VprDeficitEngine().analyze(_analytics(_summary(cv_primary_score_percent=10.0), tasks)),
        )
        heterogeneous = self.engine.build(
            _analytics(_summary(cv_primary_score_percent=45.0), tasks),
            VprDeficitEngine().analyze(_analytics(_summary(cv_primary_score_percent=45.0), tasks)),
        )
        self.assertIn("однород", _full_text(homogeneous).lower())
        self.assertIn("дифференцир", _full_text(heterogeneous).lower())
        self.assertNotEqual(_full_text(homogeneous), _full_text(heterogeneous))


class VprConclusionScreenTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Conclusion Ministry")
        district = District.objects.create(ministry=ministry, code="cn20", name="Conclusion District")
        self.school = School.objects.create(
            district=district,
            code="vpr-cn-school",
            name='МБОУ «СОШ №1 г.Урус-Мартан»',
        )
        self.user = User.objects.create_user(
            username="vpr_cn_user",
            password="pass12345",
            role="school",
            school=self.school,
        )
        import_catalog_file(CATALOG_FIXTURE)
        self.service = VprImportService()
        self.client = Client()
        self.client.login(username="vpr_cn_user", password="pass12345")

    def _import(self, fixture: Path, suffix: str):
        uploaded = SimpleUploadedFile(
            f"f1_{suffix}.xlsx",
            fixture.read_bytes(),
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

    def test_page_shows_interpretation_not_overview_tables(self):
        protocol = self._import(PROTOCOL_FIXTURE, "page")
        response = self.client.get(
            reverse("vpr-protocol-conclusion", kwargs={"protocol_id": protocol.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("analysis", response.context)
        self.assertContains(response, "Экспертная интерпретация результатов")
        self.assertContains(response, "Общая оценка результатов")
        self.assertContains(response, "Итоговая аналитическая оценка")
        self.assertContains(response, "Анализ качества подготовки")
        self.assertContains(response, "единого комплексного анализа ВПР")
        self.assertNotContains(response, "Средний первичный балл составил")
        # таблицы обзора не дублируются
        self.assertNotContains(response, "Количество критических заданий")

    def test_multiple_protocols_produce_conclusion(self):
        first = self._import(PROTOCOL_FIXTURE, "a")
        second = self._import(ALT_FIXTURE, "b")
        texts = []
        for protocol in (first, second):
            response = self.client.get(
                reverse("vpr-protocol-conclusion", kwargs={"protocol_id": protocol.id})
            )
            self.assertEqual(response.status_code, 200)
            conclusion = response.context["analysis"].conclusion
            self.assertEqual(conclusion.protocol_id, protocol.id)
            texts.append(_full_text(conclusion))
            self.assertTrue(len(conclusion.overview.paragraphs) >= 2)
        # оба текста непустые и содержат интерпретацию
        for text in texts:
            self.assertIn("уровн", text.lower())

    def test_matches_engine_output(self):
        protocol = self._import(PROTOCOL_FIXTURE, "match")
        analytics = VprAnalyticsEngine().analyze(protocol)
        deficits = VprDeficitEngine().analyze(analytics, protocol=protocol)
        expected = VprConclusionEngine().build(analytics, deficits)
        response = self.client.get(
            reverse("vpr-protocol-conclusion", kwargs={"protocol_id": protocol.id})
        )
        actual = response.context["analysis"].conclusion
        self.assertEqual(actual.overview.paragraphs, expected.overview.paragraphs)
        self.assertEqual(actual.final_conclusion.paragraphs, expected.final_conclusion.paragraphs)
