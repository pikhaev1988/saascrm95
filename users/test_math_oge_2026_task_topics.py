from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    OGE_MATH_TASK_SKILLS,
    OGE_MATH_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 20
PART2_TASKS = range(20, 26)


class MathOge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_25_have_static_topics_and_skills(self):
        for number in range(1, 26):
            with self.subTest(task=number):
                self.assertIn(number, OGE_MATH_TASK_TOPICS)
                self.assertIn(number, OGE_MATH_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("Математика", number, "oge"),
                    OGE_MATH_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Математика", number, "oge"),
                    OGE_MATH_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(
                is_expanded_answer_task("oge", "math_basic", number),
                number,
            )
        for number in PART2_TASKS:
            self.assertTrue(
                is_expanded_answer_task("oge", "math_basic", number),
                number,
            )
        self.assertEqual(part2_start_task("oge", "math_basic"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("математика", 9, "oge"),
            OGE_MATH_TASK_TOPICS[9],
        )
        self.assertEqual(
            skill_for_task("МАТЕМАТИКА", 22, "oge"),
            OGE_MATH_TASK_SKILLS[22],
        )

    def test_oge_topics_override_enriched_catalog(self):
        topic = topic_for_task("Математика", 1, "oge")
        self.assertEqual(topic, OGE_MATH_TASK_TOPICS[1])
        self.assertNotIn("класс:", topic.lower())


class MathOge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин MA OGE")
        district = District.objects.create(ministry=ministry, code="MAO", name="Район MAO")
        school = School.objects.create(district=district, code="MAO", name="Школа MAO")
        exam = Exam.objects.create(
            exam_type="oge",
            code="MAO1",
            subject="Математика",
            exam_date=date(2026, 6, 2),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="MAO-1",
            full_name="Ученик MAO",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=20,
            total_score=20,
            passed=True,
        )
        for task_number in range(1, 26):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, OGE_MATH_TASK_TOPICS[1])
        self.assertEqual(by_number[10].topic, OGE_MATH_TASK_TOPICS[10])
        self.assertEqual(by_number[20].topic, OGE_MATH_TASK_TOPICS[20])
        self.assertEqual(by_number[5].skill_name, OGE_MATH_TASK_SKILLS[5])
        self.assertEqual(by_number[25].skill_name, OGE_MATH_TASK_SKILLS[25])
        self.assertEqual(by_number[19].exam_part, 1)
        self.assertEqual(by_number[20].exam_part, 2)
