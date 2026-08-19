from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

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
from apps.vpr.causes import VprCauseAnalysisEngine
from apps.vpr.causes.labels import (
    CAUSE_SKILL,
    CAUSE_THEMATIC,
    CAUSE_TYPE_COMPLEXITY,
    CAUSE_TYPE_SKILL,
    CAUSE_TYPE_THEMATIC,
    SCALE_LOCAL,
    SCALE_MASS,
    SCALE_NONE,
    SCALE_SYSTEMIC,
)
from apps.vpr.deficits import VprDeficitEngine
from apps.vpr.services.catalog_import import import_catalog_file
from apps.vpr.services.import_service import VprImportService
from organizations.models import District, Ministry, School

User = get_user_model()
PROTOCOL_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "Ф1_Индивидуальные_результаты.xlsx"
ALT_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "vpr_f1_sample.xlsx"
CATALOG_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "vpr_task_catalog_sample.json"


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
    difficulty: str = "",
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
        answers_count=20,
        topic=topic,
        program_section=section,
        checked_skill=skill,
        difficulty=difficulty,
        catalog_matched=bool(topic or skill),
    )


def _analytics(summary: VprSummaryMetrics, tasks: list[VprTaskAnalytics]) -> VprAnalyticsResult:
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
        organization_name="Тест",
        summary=summary,
        marks=VprMarksDistribution(),
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
        students=[],
    )


class VprCauseAnalysisUnitTests(TestCase):
    def setUp(self):
        self.cause_engine = VprCauseAnalysisEngine()
        self.deficit_engine = VprDeficitEngine()

    def test_high_results_no_significant_causes(self):
        tasks = [
            _task("1", pct=95, topic="Орфография", skill="Писать", difficulty="Б"),
            _task("2", pct=90, topic="Пунктуация", skill="Знаки", difficulty="Б", position=2),
            _task("3", pct=88, topic="Чтение", skill="Понимать", difficulty="П", position=3),
        ]
        analytics = _analytics(_summary(knowledge_quality_percent=85.0, avg_primary_score=18.0), tasks)
        deficits = self.deficit_engine.analyze(analytics)
        result = self.cause_engine.analyze(analytics, deficits)

        self.assertEqual(result.summary.significant_deficits_count, 0)
        self.assertEqual(result.summary.dominant_scale, SCALE_NONE)
        self.assertEqual(result.tasks, [])
        payload = result.to_dict()
        self.assertEqual(
            set(payload.keys()),
            {"protocol_id", "subject", "parallel", "academic_year", "summary", "tasks", "topics", "skills", "patterns"},
        )

    def test_thematic_deficit_cause(self):
        tasks = [
            _task("5", pct=25, topic="Правописание", skill="Правило А", section="Орфография", difficulty="Б"),
            _task("6", pct=30, topic="Правописание", skill="Правило Б", section="Орфография", difficulty="Б", position=2),
            _task("7", pct=85, topic="Чтение", skill="Понимать", difficulty="Б", position=3),
        ]
        analytics = _analytics(_summary(), tasks)
        deficits = self.deficit_engine.analyze(analytics)
        result = self.cause_engine.analyze(analytics, deficits)

        self.assertGreaterEqual(result.summary.significant_deficits_count, 2)
        thematic = [f for f in result.tasks if f.cause_type == CAUSE_TYPE_THEMATIC]
        self.assertTrue(thematic)
        finding = thematic[0]
        self.assertIn("5", finding.problem)
        self.assertIn("6", finding.problem)
        self.assertEqual(finding.cause, CAUSE_THEMATIC)
        self.assertIn(finding.scale, {SCALE_LOCAL, SCALE_MASS, SCALE_SYSTEMIC})
        self.assertEqual(finding.topic, "Правописание")

    def test_skill_deficit_cause(self):
        tasks = [
            _task("1", pct=20, topic="Тема A", skill="Применение правил правописания", difficulty="Б"),
            _task("2", pct=28, topic="Тема B", skill="Применение правил правописания", difficulty="П", position=2),
            _task("3", pct=80, topic="Тема C", skill="Другое умение", difficulty="Б", position=3),
        ]
        analytics = _analytics(_summary(), tasks)
        deficits = self.deficit_engine.analyze(analytics)
        result = self.cause_engine.analyze(analytics, deficits)

        skill_findings = [f for f in result.skills if f.cause_type == CAUSE_TYPE_SKILL]
        self.assertTrue(skill_findings or any(f.cause_type == CAUSE_TYPE_SKILL for f in result.tasks))
        joined = " ".join(f.cause for f in result.tasks + result.skills)
        self.assertTrue(CAUSE_SKILL in joined or "умения" in joined.lower())

    def test_complexity_pattern(self):
        tasks = [
            _task("1", pct=90, topic="База", skill="Знать", difficulty="базовый"),
            _task("2", pct=88, topic="База", skill="Знать", difficulty="базовый", position=2),
            _task("3", pct=25, topic="Применение", skill="Применять", difficulty="повышенный", position=3),
            _task("4", pct=30, topic="Анализ", skill="Анализировать", difficulty="повышенный", position=4),
        ]
        analytics = _analytics(_summary(), tasks)
        deficits = self.deficit_engine.analyze(analytics)
        result = self.cause_engine.analyze(analytics, deficits)

        complexity = [
            p for p in result.patterns if p.pattern_type == "complexity_gap"
        ] or [f for f in result.tasks if f.cause_type == CAUSE_TYPE_COMPLEXITY]
        self.assertTrue(complexity)
        text = " ".join(
            getattr(x, "cause", "") for x in complexity
        )
        self.assertIn("повышен", text.lower())

    def test_mixed_results(self):
        tasks = [
            _task("1", pct=92, topic="Сильная", skill="Умение 1", difficulty="Б"),
            _task("2", pct=35, topic="Слабая", skill="Умение 2", difficulty="П", position=2),
            _task("3", pct=40, topic="Слабая", skill="Умение 3", difficulty="Б", position=3),
            _task("4", pct=78, topic="Средняя", skill="Умение 4", difficulty="Б", position=4),
        ]
        analytics = _analytics(_summary(), tasks)
        deficits = self.deficit_engine.analyze(analytics)
        result = self.cause_engine.analyze(analytics, deficits)

        self.assertGreater(result.summary.significant_deficits_count, 0)
        self.assertGreater(result.summary.causes_count, 0)
        self.assertTrue(result.tasks or result.topics or result.skills)
        for finding in result.tasks:
            self.assertIn("cause", finding.to_dict())
            self.assertIn("scale", finding.to_dict())
            self.assertNotIn("рекоменд", finding.cause.lower())

    def test_missing_catalog_data(self):
        tasks = [
            _task("8", pct=20),
            _task("9", pct=25, position=2),
        ]
        analytics = _analytics(_summary(), tasks)
        deficits = self.deficit_engine.analyze(analytics)
        result = self.cause_engine.analyze(analytics, deficits)

        self.assertEqual(result.summary.catalog_coverage, "none")
        self.assertGreaterEqual(result.summary.significant_deficits_count, 1)
        # без справочника причина может быть unknown либо базовая классификация по приоритету
        if result.tasks:
            for finding in result.tasks:
                self.assertTrue(finding.cause)
                self.assertIn(finding.scale, {SCALE_LOCAL, SCALE_MASS, SCALE_SYSTEMIC})


class VprCauseAnalysisIntegrationTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Cause Ministry")
        district = District.objects.create(ministry=ministry, code="cs20", name="Cause District")
        self.school = School.objects.create(
            district=district,
            code="vpr-cs-school",
            name='МБОУ «СОШ №1 г.Урус-Мартан»',
        )
        self.user = User.objects.create_user(
            username="vpr_cs_user",
            password="pass12345",
            role="school",
            school=self.school,
        )
        import_catalog_file(CATALOG_FIXTURE)
        self.service = VprImportService()
        self.analytics_engine = VprAnalyticsEngine()
        self.deficit_engine = VprDeficitEngine()
        self.cause_engine = VprCauseAnalysisEngine()

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

    def test_real_protocol_with_catalog(self):
        protocol = self._import(PROTOCOL_FIXTURE, "real")
        analytics = self.analytics_engine.analyze(protocol)
        deficits = self.deficit_engine.analyze(analytics, protocol=protocol)
        result = self.cause_engine.analyze(analytics, deficits)

        self.assertEqual(result.protocol_id, protocol.id)
        self.assertIn(result.summary.catalog_coverage, {"full", "partial", "none"})
        payload = result.to_dict()
        self.assertIn("summary", payload)
        self.assertIn("patterns", payload)
        # нет рекомендаций
        blob = str(payload).lower()
        self.assertNotIn("рекоменд", blob)
        self.assertNotIn("мероприяти", blob)

    def test_multiple_protocols(self):
        first = self._import(PROTOCOL_FIXTURE, "p1")
        second = self._import(ALT_FIXTURE, "p2")
        results = []
        for protocol in (first, second):
            analytics = self.analytics_engine.analyze(protocol)
            deficits = self.deficit_engine.analyze(analytics, protocol=protocol)
            results.append(self.cause_engine.analyze(analytics, deficits))
        self.assertEqual(results[0].protocol_id, first.id)
        self.assertEqual(results[1].protocol_id, second.id)
        # структура одинакова
        for result in results:
            self.assertTrue(hasattr(result, "summary"))
            self.assertTrue(hasattr(result, "tasks"))
            self.assertTrue(hasattr(result, "topics"))
            self.assertTrue(hasattr(result, "skills"))
            self.assertTrue(hasattr(result, "patterns"))
