from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    OGE_GEOGRAPHY_TASK_SKILLS,
    OGE_GEOGRAPHY_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 28
PART2_TASKS = range(28, 31)


class GeographyOge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_30_have_static_topics_and_skills(self):
        for number in range(1, 31):
            with self.subTest(task=number):
                self.assertIn(number, OGE_GEOGRAPHY_TASK_TOPICS)
                self.assertIn(number, OGE_GEOGRAPHY_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("География", number, "oge"),
                    OGE_GEOGRAPHY_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("География", number, "oge"),
                    OGE_GEOGRAPHY_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(
                is_expanded_answer_task("oge", "geography", number),
                number,
            )
        for number in PART2_TASKS:
            self.assertTrue(
                is_expanded_answer_task("oge", "geography", number),
                number,
            )
        self.assertEqual(part2_start_task("oge", "geography"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("география", 11, "oge"),
            OGE_GEOGRAPHY_TASK_TOPICS[11],
        )
        self.assertEqual(
            skill_for_task("ГЕОГРАФИЯ", 30, "oge"),
            OGE_GEOGRAPHY_TASK_SKILLS[30],
        )

    def test_oge_topics_override_enriched_catalog(self):
        topic = topic_for_task("География", 1, "oge")
        self.assertEqual(topic, OGE_GEOGRAPHY_TASK_TOPICS[1])
        self.assertNotIn("моделирован", topic.lower())


class GeographyOge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин GG OGE")
        district = District.objects.create(ministry=ministry, code="GGO", name="Район GGO")
        school = School.objects.create(district=district, code="GGO", name="Школа GGO")
        exam = Exam.objects.create(
            exam_type="oge",
            code="GGO1",
            subject="География",
            exam_date=date(2026, 6, 5),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="GGO-1",
            full_name="Ученик GGO",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=26,
            total_score=26,
            passed=True,
        )
        for task_number in range(1, 31):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, OGE_GEOGRAPHY_TASK_TOPICS[1])
        self.assertEqual(by_number[15].topic, OGE_GEOGRAPHY_TASK_TOPICS[15])
        self.assertEqual(by_number[30].topic, OGE_GEOGRAPHY_TASK_TOPICS[30])
        self.assertEqual(by_number[7].skill_name, OGE_GEOGRAPHY_TASK_SKILLS[7])
        self.assertEqual(by_number[29].skill_name, OGE_GEOGRAPHY_TASK_SKILLS[29])
        self.assertEqual(by_number[27].exam_part, 1)
        self.assertEqual(by_number[28].exam_part, 2)
