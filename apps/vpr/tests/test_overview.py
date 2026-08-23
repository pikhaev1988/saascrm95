from __future__ import annotations

from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.vpr.analytics import VprAnalyticsEngine
from apps.vpr.comprehensive_analysis import VprComprehensiveAnalysisEngine, get_protocol_analysis
from apps.vpr.comprehensive_analysis.cache import invalidate_protocol_analysis
from apps.vpr.deficits import VprDeficitEngine
from apps.vpr.services.catalog_import import import_catalog_file
from apps.vpr.services.import_service import VprImportService
from organizations.models import District, Ministry, School

User = get_user_model()
PROTOCOL_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "Ф1_Индивидуальные_результаты.xlsx"
ALT_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "vpr_f1_sample.xlsx"
CATALOG_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "vpr_task_catalog_sample.json"


class VprOverviewScreenTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Overview Ministry")
        district = District.objects.create(ministry=ministry, code="ov20", name="Overview District")
        self.school = School.objects.create(
            district=district,
            code="vpr-ov-school",
            name='МБОУ «СОШ №1 г.Урус-Мартан»',
        )
        self.user = User.objects.create_user(
            username="vpr_ov_user",
            password="pass12345",
            role="school",
            school=self.school,
        )
        import_catalog_file(CATALOG_FIXTURE)
        self.service = VprImportService()
        self.client = Client()
        self.client.login(username="vpr_ov_user", password="pass12345")
        self.analytics_engine = VprAnalyticsEngine()
        self.deficit_engine = VprDeficitEngine()

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

    def test_views_do_not_call_engines_directly(self):
        import apps.vpr.views_conclusion as cn
        import apps.vpr.views_overview as ov

        ov_text = Path(ov.__file__).read_text(encoding="utf-8")
        cn_text = Path(cn.__file__).read_text(encoding="utf-8")
        for name in ("VprAnalyticsEngine", "VprDeficitEngine", "VprCauseAnalysisEngine", "VprConclusionEngine"):
            self.assertNotIn(name, ov_text)
            self.assertNotIn(name, cn_text)
        self.assertIn("get_protocol_analysis", ov_text)
        self.assertIn("get_protocol_analysis", cn_text)
        self.assertIn("build_subject_report", ov_text)

    def test_overview_tab_on_protocol_and_page_loads(self):
        protocol = self._import(PROTOCOL_FIXTURE, "tab")
        detail = self.client.get(reverse("vpr-protocol-detail", kwargs={"protocol_id": protocol.id}))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Обзор")
        self.assertContains(detail, reverse("vpr-protocol-overview", kwargs={"protocol_id": protocol.id}))

        overview = self.client.get(
            reverse("vpr-protocol-overview", kwargs={"protocol_id": protocol.id})
        )
        self.assertEqual(overview.status_code, 200)
        self.assertContains(overview, "Аналитическая справка по методологии ФИОКО")
        self.assertContains(overview, "Паспорт анализа")
        self.assertContains(overview, "Анализ индивидуальных результатов")
        self.assertContains(overview, "Анализ статистики отметок")
        self.assertContains(overview, "Сравнение отметок ВПР и журнала")
        self.assertContains(overview, "Анализ распределения первичных баллов")
        self.assertContains(overview, "Анализ выполнения заданий")
        self.assertContains(overview, "Анализ достижения планируемых результатов")
        self.assertContains(overview, "Анализ выполнения заданий различными группами участников")
        self.assertContains(overview, "Образовательные дефициты")
        self.assertContains(overview, "Работа администрации")
        self.assertContains(overview, "Работа школьных методических объединений")
        self.assertContains(overview, "Работа с педагогами")
        self.assertContains(overview, "Работа с родителями")
        self.assertContains(overview, "Методические рекомендации")
        self.assertContains(overview, "План мероприятий")
        self.assertContains(overview, "Итоговое экспертное заключение")
        self.assertContains(overview, "Организационно-управленческие решения")
        self.assertContains(overview, "Ожидаемый результат реализации мероприятий")
        self.assertContains(overview, "Скачать справку")
        self.assertContains(
            overview,
            reverse("vpr-protocol-overview-docx", kwargs={"protocol_id": protocol.id}),
        )
        self.assertIn("analysis", overview.context)
        self.assertIn("report", overview.context)
        report = overview.context["report"]
        self.assertTrue(report.passport)
        self.assertTrue(report.action_plan)
        self.assertGreaterEqual(len(report.final_conclusion), 5)
        self.assertTrue(report.individual_cycle.org_decisions)
        self.assertTrue(report.marks_cycle.expected_effect)

    def test_overview_docx_download(self):
        protocol = self._import(PROTOCOL_FIXTURE, "docx")
        url = reverse("vpr-protocol-overview-docx", kwargs={"protocol_id": protocol.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            response["Content-Type"],
        )
        self.assertIn(".docx", response["Content-Disposition"])
        content = b"".join(response.streaming_content)
        self.assertTrue(content[:2] == b"PK")
        # справка не должна опираться на блок 9 — проверяем заголовки разделов в docx zip xml
        from io import BytesIO
        from zipfile import ZipFile

        with ZipFile(BytesIO(content)) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", "ignore")
            media = [n for n in zf.namelist() if n.startswith("word/media/")]
        self.assertIn("Анализ результатов ВПР на уровне общеобразовательной организации", xml)
        self.assertIn("Паспорт анализа", xml)
        self.assertIn("Итоговое экспертное заключение", xml)
        self.assertIn("План мероприятий", xml)
        self.assertNotIn("Количество критических заданий", xml)
        # Диаграммы (отметки, баллы, задания, группы, объективность)
        self.assertGreaterEqual(len(media), 3)

    def test_overview_matches_engines_without_recalculation(self):
        protocol = self._import(PROTOCOL_FIXTURE, "match")
        expected_analytics = self.analytics_engine.analyze(protocol)
        expected_deficits = self.deficit_engine.analyze(expected_analytics, protocol=protocol)

        response = self.client.get(
            reverse("vpr-protocol-overview", kwargs={"protocol_id": protocol.id})
        )
        self.assertEqual(response.status_code, 200)
        analysis = response.context["analysis"]
        summary = analysis.summary

        self.assertEqual(summary.participants_count, expected_analytics.summary.participants_count)
        self.assertEqual(summary.avg_primary_score, expected_analytics.summary.avg_primary_score)
        self.assertEqual(summary.min_primary_score, expected_analytics.summary.min_primary_score)
        self.assertEqual(summary.max_primary_result, expected_analytics.summary.max_primary_result)
        self.assertEqual(summary.avg_mark_vpr, expected_analytics.summary.avg_mark_vpr)
        self.assertEqual(summary.avg_mark_journal, expected_analytics.summary.avg_mark_journal)
        self.assertEqual(
            summary.knowledge_quality_percent,
            expected_analytics.summary.knowledge_quality_percent,
        )
        self.assertEqual(
            summary.absolute_achievement_percent,
            expected_analytics.summary.absolute_achievement_percent,
        )
        self.assertEqual(summary.sou_percent, expected_analytics.summary.sou_percent)
        self.assertEqual(summary.median_primary_score, expected_analytics.summary.median_primary_score)
        self.assertEqual(summary.mode_primary_score, expected_analytics.summary.mode_primary_score)
        self.assertEqual(summary.stdev_primary_score, expected_analytics.summary.stdev_primary_score)
        self.assertEqual(
            summary.cv_primary_score_percent,
            expected_analytics.summary.cv_primary_score_percent,
        )

        self.assertEqual(len(analysis.task_rows), len(expected_analytics.tasks))
        by_code = {t.task_code: t for t in expected_analytics.tasks}
        deficit_by_code = {t.task_code: t for t in expected_deficits.tasks}
        for row in analysis.task_rows:
            src = by_code[row["task_code"]]
            deficit = deficit_by_code[row["task_code"]]
            self.assertEqual(row["completion_percent"], src.completion_percent)
            self.assertEqual(row["avg_score"], src.avg_score)
            self.assertEqual(row["max_score"], src.max_score)
            self.assertEqual(row["topic"], src.topic)
            self.assertEqual(row["checked_skill"], src.checked_skill)
            self.assertEqual(row["correct_count"], src.correct_count or src.full_count)
            self.assertEqual(
                row["incorrect_count"],
                max(0, int(src.answers_count or 0) - int(src.correct_count or src.full_count or 0)),
            )
            self.assertEqual(row["plus"] + row["minus"], row["total"])
            self.assertEqual(row["partial_count"], src.partial_count)
            self.assertEqual(row["answers_count"], src.answers_count)
            self.assertEqual(row["priority"], deficit.priority)
            self.assertEqual(row["status"], deficit.status)

        self.assertEqual(len(analysis.topic_rows), len(expected_deficits.topics))
        self.assertEqual(len(analysis.skill_rows), len(expected_deficits.skills))
        self.assertEqual(len(analysis.student_rows), len(expected_analytics.students))

        marks_total = sum(row["count"] for row in analysis.marks_rows)
        self.assertEqual(marks_total, sum(expected_analytics.marks.vpr.values()))

        priority_map = {item["code"]: item["count"] for item in analysis.priority_summary}
        expected_priority = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for task in expected_deficits.tasks:
            expected_priority[task.priority] = expected_priority.get(task.priority, 0) + 1
        self.assertEqual(priority_map, expected_priority)

    def test_overview_single_engine_pipeline_call(self):
        protocol = self._import(PROTOCOL_FIXTURE, "once")
        calls: list = []
        orig = VprComprehensiveAnalysisEngine.analyze

        def tracked(self, protocol_arg):
            calls.append(protocol_arg)
            return orig(self, protocol_arg)

        with mock.patch.object(VprComprehensiveAnalysisEngine, "analyze", tracked):
            response = self.client.get(
                reverse("vpr-protocol-overview", kwargs={"protocol_id": protocol.id})
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(calls), 1)

    def test_multiple_protocols_overview(self):
        first = self._import(PROTOCOL_FIXTURE, "p1")
        second = self._import(ALT_FIXTURE, "p2")
        for protocol in (first, second):
            response = self.client.get(
                reverse("vpr-protocol-overview", kwargs={"protocol_id": protocol.id})
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["protocol"].id, protocol.id)
            self.assertEqual(
                response.context["analysis"].summary.participants_count,
                protocol.participants_count,
            )
            self.assertContains(response, protocol.subject)

    def test_empty_values_render_dash(self):
        protocol = self._import(PROTOCOL_FIXTURE, "empty")
        protocol.exam_date = None
        protocol.save(update_fields=["exam_date"])
        response = self.client.get(
            reverse("vpr-protocol-overview", kwargs={"protocol_id": protocol.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Дата проведения")
        self.assertContains(response, "—")

    def test_access_denied_for_other_school(self):
        protocol = self._import(PROTOCOL_FIXTURE, "acl")
        other = User.objects.create_user(
            username="vpr_ov_other",
            password="pass12345",
            role="school",
            school=School.objects.create(
                district=self.school.district,
                code="vpr-ov-other",
                name="Другая школа",
            ),
        )
        self.client.login(username="vpr_ov_other", password="pass12345")
        response = self.client.get(
            reverse("vpr-protocol-overview", kwargs={"protocol_id": protocol.id})
        )
        self.assertEqual(response.status_code, 302)


@override_settings(VPR_ANALYSIS_CACHE_ENABLED=False)
class VprAnalysisCacheOffTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Cache Off Ministry")
        district = District.objects.create(ministry=ministry, code="c0", name="Cache Off District")
        self.school = School.objects.create(
            district=district,
            code="vpr-c0-school",
            name='МБОУ «СОШ №1 г.Урус-Мартан»',
        )
        self.user = User.objects.create_user(
            username="vpr_c0_user",
            password="pass12345",
            role="school",
            school=self.school,
        )
        import_catalog_file(CATALOG_FIXTURE)
        self.service = VprImportService()
        uploaded = SimpleUploadedFile(
            "f1_c0.xlsx",
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
        self.protocol = upload.protocol

    def test_works_without_cache(self):
        with mock.patch(
            "apps.vpr.comprehensive_analysis.service.set_cached_analysis"
        ) as set_cache:
            analysis = get_protocol_analysis(self.protocol, use_cache=False)
            self.assertGreater(analysis.achievement.participants, 0)
            set_cache.assert_not_called()


@override_settings(
    VPR_ANALYSIS_CACHE_ENABLED=True,
    VPR_ANALYSIS_CACHE_TIMEOUT=300,
)
class VprAnalysisCacheOnTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Cache On Ministry")
        district = District.objects.create(ministry=ministry, code="c1", name="Cache On District")
        self.school = School.objects.create(
            district=district,
            code="vpr-c1-school",
            name='МБОУ «СОШ №1 г.Урус-Мартан»',
        )
        self.user = User.objects.create_user(
            username="vpr_c1_user",
            password="pass12345",
            role="school",
            school=self.school,
        )
        import_catalog_file(CATALOG_FIXTURE)
        self.service = VprImportService()
        uploaded = SimpleUploadedFile(
            "f1_c1.xlsx",
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
        self.protocol = upload.protocol
        invalidate_protocol_analysis(self.protocol.id)

    def test_second_call_uses_cache(self):
        calls: list = []
        orig = VprComprehensiveAnalysisEngine.analyze

        def tracked(self, protocol_arg):
            calls.append(protocol_arg)
            return orig(self, protocol_arg)

        with mock.patch.object(VprComprehensiveAnalysisEngine, "analyze", tracked):
            first = get_protocol_analysis(self.protocol)
            second = get_protocol_analysis(self.protocol)
            self.assertEqual(len(calls), 1)
            self.assertEqual(first.protocol.protocol_id, second.protocol.protocol_id)
            self.assertEqual(first.summary.avg_primary_score, second.summary.avg_primary_score)
