from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.vpr.analytics import VprAnalyticsEngine
from apps.vpr.analytics.stats import (
    coefficient_of_variation,
    degree_of_learning,
    percent,
    population_stdev,
    safe_mean,
    safe_median,
    safe_mode,
)
from apps.vpr.models import VprProtocol
from apps.vpr.services.catalog_import import import_catalog_file
from apps.vpr.services.import_service import VprImportService
from organizations.models import District, Ministry, School

User = get_user_model()
PROTOCOL_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "Ф1_Индивидуальные_результаты.xlsx"
CATALOG_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "vpr_task_catalog_sample.json"


class VprStatsHelpersTests(TestCase):
    def test_basic_stats(self):
        values = [2, 3, 3, 4, 5]
        self.assertEqual(safe_mean(values), 3.4)
        self.assertEqual(safe_median(values), 3.0)
        self.assertEqual(safe_mode(values), 3.0)
        self.assertAlmostEqual(population_stdev(values), 1.0198, places=3)
        self.assertIsNotNone(coefficient_of_variation(values))
        self.assertEqual(percent(2, 4), 50.0)

    def test_degree_of_learning_sou(self):
        # (1*100 + 1*64 + 1*36 + 1*16) / 4 = 54
        self.assertEqual(degree_of_learning([5, 4, 3, 2]), 54.0)
        self.assertIsNone(degree_of_learning([]))
        self.assertEqual(degree_of_learning([5, 5, 5, 5]), 100.0)


class VprAnalyticsEngineTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Analytics Ministry")
        district = District.objects.create(ministry=ministry, code="an20", name="Analytics District")
        self.school = School.objects.create(
            district=district,
            code="vpr-an-school",
            name='МБОУ «СОШ №1 г.Урус-Мартан»',
        )
        self.user = User.objects.create_user(
            username="vpr_an_user",
            password="pass12345",
            role="school",
            school=self.school,
        )
        import_catalog_file(CATALOG_FIXTURE)
        self.service = VprImportService()
        self.engine = VprAnalyticsEngine()

    def _import_protocol(self, suffix: str = "a") -> VprProtocol:
        uploaded = SimpleUploadedFile(
            f"f1_{suffix}.xlsx",
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

    def test_summary_metrics(self):
        protocol = self._import_protocol("sum")
        result = self.engine.analyze(protocol)
        summary = result.summary

        self.assertEqual(summary.participants_count, 89)
        self.assertEqual(summary.max_primary_score, 24)
        self.assertIsNotNone(summary.avg_primary_score)
        self.assertIsNotNone(summary.min_primary_score)
        self.assertIsNotNone(summary.max_primary_result)
        self.assertIsNotNone(summary.avg_mark_vpr)
        self.assertIsNotNone(summary.avg_mark_journal)
        self.assertIsNotNone(summary.knowledge_quality_percent)
        self.assertIsNotNone(summary.absolute_achievement_percent)
        self.assertIsNotNone(summary.sou_percent)
        self.assertIsNotNone(summary.median_primary_score)
        self.assertIsNotNone(summary.mode_primary_score)
        self.assertIsNotNone(summary.stdev_primary_score)
        self.assertIsNotNone(summary.cv_primary_score_percent)

        # математическая согласованность
        self.assertGreaterEqual(summary.max_primary_result, summary.min_primary_score)
        self.assertGreaterEqual(summary.absolute_achievement_percent, summary.knowledge_quality_percent)
        self.assertGreaterEqual(summary.absolute_achievement_percent, 0)
        self.assertLessEqual(summary.absolute_achievement_percent, 100)
        self.assertGreaterEqual(summary.sou_percent, 0)
        self.assertLessEqual(summary.sou_percent, 100)

        marks = list(
            protocol.student_results.exclude(mark_vpr=None).values_list("mark_vpr", flat=True)
        )
        self.assertEqual(summary.sou_percent, degree_of_learning(marks))

        # ручная проверка среднего
        scores = list(
            protocol.student_results.exclude(primary_score=None).values_list("primary_score", flat=True)
        )
        expected_avg = round(sum(float(s) for s in scores) / len(scores), 4)
        self.assertEqual(summary.avg_primary_score, expected_avg)

    def test_marks_and_scores_distribution(self):
        protocol = self._import_protocol("dist")
        result = self.engine.analyze(protocol)
        self.assertTrue(result.marks.vpr)
        self.assertTrue(result.marks.journal)
        self.assertAlmostEqual(sum(result.marks.vpr_percents.values()), 100.0, places=1)
        self.assertTrue(result.scores.counts)
        self.assertAlmostEqual(sum(result.scores.percents.values()), 100.0, places=1)

    def test_tasks_with_catalog(self):
        protocol = self._import_protocol("tasks")
        result = self.engine.analyze(protocol)
        self.assertEqual(len(result.tasks), 15)

        for task in result.tasks:
            self.assertEqual(task.full_count + task.partial_count + task.zero_count, 89)
            self.assertEqual(task.correct_count, task.full_count)
            self.assertEqual(task.incorrect_count, task.zero_count)
            self.assertIsNotNone(task.avg_score)
            self.assertIsNotNone(task.completion_percent)
            self.assertGreaterEqual(task.completion_percent, 0)
            self.assertLessEqual(task.completion_percent, 100)

        matched = [t for t in result.tasks if t.catalog_matched]
        self.assertGreaterEqual(len(matched), 1)
        task7 = next(t for t in result.tasks if t.task_code == "7")
        self.assertTrue(task7.catalog_matched)
        self.assertEqual(task7.topic, "Синонимы")
        self.assertTrue(task7.checked_skill)

    def test_topics_and_skills(self):
        protocol = self._import_protocol("topics")
        result = self.engine.analyze(protocol)
        self.assertTrue(result.topics)
        self.assertTrue(result.skills)

        # сумма заданий по темам >= числа заданий (тема "без справочника" тоже есть)
        total_topic_tasks = sum(t.tasks_count for t in result.topics)
        self.assertEqual(total_topic_tasks, len(result.tasks))

        total_skill_tasks = sum(s.tasks_count for s in result.skills)
        self.assertEqual(total_skill_tasks, len(result.tasks))

        for topic in result.topics:
            self.assertGreaterEqual(topic.errors_count, 0)
            if topic.avg_completion_percent is not None:
                self.assertGreaterEqual(topic.avg_completion_percent, 0)
                self.assertLessEqual(topic.avg_completion_percent, 100)

    def test_students_ranking(self):
        protocol = self._import_protocol("stud")
        result = self.engine.analyze(protocol)
        self.assertEqual(len(result.students), 89)

        places = [s.place_overall for s in result.students]
        self.assertEqual(min(places), 1)
        # при ничьих максимальное место < N (competition ranking)
        self.assertLessEqual(max(places), 89)
        self.assertEqual(len(places), 89)

        top = result.students[0]
        self.assertEqual(top.place_overall, 1)
        self.assertIsNotNone(top.completion_percent)
        self.assertIsNotNone(top.avg_task_score)

        # одинаковые баллы — одинаковые места
        by_score: dict[float, set[int]] = {}
        for student in result.students:
            if student.primary_score is None:
                continue
            by_score.setdefault(student.primary_score, set()).add(student.place_overall)
        for places_set in by_score.values():
            self.assertEqual(len(places_set), 1)

        # место в классе заполнено
        self.assertTrue(any(s.place_in_class for s in result.students))

    def test_analyze_by_id_and_to_dict(self):
        protocol = self._import_protocol("dict")
        result = self.engine.analyze(protocol.id)
        payload = result.to_dict()
        self.assertEqual(payload["protocol_id"], protocol.id)
        self.assertIn("summary", payload)
        self.assertIn("marks", payload)
        self.assertIn("scores", payload)
        self.assertIn("tasks", payload)
        self.assertIn("topics", payload)
        self.assertIn("skills", payload)
        self.assertIn("students", payload)
        self.assertEqual(len(payload["tasks"]), 15)
        self.assertEqual(len(payload["students"]), 89)

    def test_multiple_protocols(self):
        p1 = self._import_protocol("m1")
        p2 = self._import_protocol("m2")
        r1 = self.engine.analyze(p1)
        r2 = self.engine.analyze(p2)
        self.assertEqual(r1.summary.participants_count, r2.summary.participants_count)
        self.assertEqual(r1.summary.avg_primary_score, r2.summary.avg_primary_score)
        self.assertEqual(len(r1.tasks), len(r2.tasks))
