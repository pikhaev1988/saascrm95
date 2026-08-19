from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    OGE_RUSSIAN_TASK_SKILLS,
    OGE_RUSSIAN_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPANDED_TASKS = {1, 13}
PART2_START = 13


class RussianOge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_13_have_static_topics_and_skills(self):
        for number in range(1, 14):
            with self.subTest(task=number):
                self.assertIn(number, OGE_RUSSIAN_TASK_TOPICS)
                self.assertIn(number, OGE_RUSSIAN_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("Русский язык", number, "oge"),
                    OGE_RUSSIAN_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Русский язык", number, "oge"),
                    OGE_RUSSIAN_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(2, PART2_START):
            self.assertFalse(
                is_expanded_answer_task("oge", "russian", number),
                number,
            )
        for number in EXPANDED_TASKS:
            self.assertTrue(
                is_expanded_answer_task("oge", "russian", number),
                number,
            )
        self.assertEqual(part2_start_task("oge", "russian"), PART2_START)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("русский язык", 10, "oge"),
            OGE_RUSSIAN_TASK_TOPICS[10],
        )
        self.assertEqual(
            skill_for_task("РУССКИЙ ЯЗЫК", 13, "oge"),
            OGE_RUSSIAN_TASK_SKILLS[13],
        )

    def test_oge_topics_override_enriched_catalog(self):
        oge_topic = topic_for_task("Русский язык", 1, "oge")
        self.assertEqual(oge_topic, OGE_RUSSIAN_TASK_TOPICS[1])
        self.assertNotIn("5 класс,", oge_topic)
        self.assertNotEqual(
            topic_for_task("Русский язык", 1, "ege"),
            oge_topic,
        )


class RussianOge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин RU OGE")
        district = District.objects.create(ministry=ministry, code="RUO", name="Район RUO")
        school = School.objects.create(district=district, code="RUO", name="Школа RUO")
        exam = Exam.objects.create(
            exam_type="oge",
            code="RUO1",
            subject="Русский язык",
            exam_date=date(2026, 6, 2),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="RUO-1",
            full_name="Ученик RUO",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=20,
            total_score=20,
            passed=True,
        )
        for task_number in range(1, 14):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, OGE_RUSSIAN_TASK_TOPICS[1])
        self.assertEqual(by_number[6].topic, OGE_RUSSIAN_TASK_TOPICS[6])
        self.assertEqual(by_number[13].topic, OGE_RUSSIAN_TASK_TOPICS[13])
        self.assertEqual(by_number[10].skill_name, OGE_RUSSIAN_TASK_SKILLS[10])
        self.assertEqual(by_number[13].skill_name, OGE_RUSSIAN_TASK_SKILLS[13])
        self.assertEqual(by_number[12].exam_part, 1)
        self.assertEqual(by_number[13].exam_part, 2)
