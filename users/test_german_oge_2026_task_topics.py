from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    OGE_GERMAN_TASK_SKILLS,
    OGE_GERMAN_TASK_TOPICS,
    OGE_FOREIGN_LANGUAGE_TASK_SKILLS,
    OGE_FOREIGN_LANGUAGE_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 35
PART2_TASKS = range(35, 39)


class GermanOge2026TaskTopicsTests(TestCase):
    def test_german_aliases_share_foreign_language_structure(self):
        self.assertIs(OGE_GERMAN_TASK_TOPICS, OGE_FOREIGN_LANGUAGE_TASK_TOPICS)
        self.assertIs(OGE_GERMAN_TASK_SKILLS, OGE_FOREIGN_LANGUAGE_TASK_SKILLS)

    def test_all_tasks_1_38_have_static_topics_and_skills(self):
        for number in range(1, 39):
            with self.subTest(task=number):
                self.assertEqual(
                    topic_for_task("Немецкий язык", number, "oge"),
                    OGE_GERMAN_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Немецкий язык", number, "oge"),
                    OGE_GERMAN_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(
                is_expanded_answer_task("oge", "german", number),
                number,
            )
        for number in PART2_TASKS:
            self.assertTrue(
                is_expanded_answer_task("oge", "german", number),
                number,
            )
        self.assertEqual(part2_start_task("oge", "german"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("немецкий язык", 5, "oge"),
            OGE_GERMAN_TASK_TOPICS[5],
        )
        self.assertEqual(
            skill_for_task("НЕМЕЦКИЙ ЯЗЫК", 37, "oge"),
            OGE_GERMAN_TASK_SKILLS[37],
        )

    def test_oge_topics_override_enriched_catalog(self):
        topic = topic_for_task("Немецкий язык", 35, "oge")
        self.assertEqual(topic, OGE_GERMAN_TASK_TOPICS[35])
        self.assertIn("письм", topic.lower())
        self.assertNotIn("эссе", topic.lower())


class GermanOge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин DE OGE")
        district = District.objects.create(ministry=ministry, code="DEO", name="Район DEO")
        school = School.objects.create(district=district, code="DEO", name="Школа DEO")
        exam = Exam.objects.create(
            exam_type="oge",
            code="DEO1",
            subject="Немецкий язык",
            exam_date=date(2026, 6, 6),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="DEO-1",
            full_name="Ученик DEO",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=4,
            total_score=4,
            passed=True,
        )
        for task_number in range(1, 39):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, OGE_GERMAN_TASK_TOPICS[1])
        self.assertEqual(by_number[12].topic, OGE_GERMAN_TASK_TOPICS[12])
        self.assertEqual(by_number[35].topic, OGE_GERMAN_TASK_TOPICS[35])
        self.assertEqual(by_number[38].skill_name, OGE_GERMAN_TASK_SKILLS[38])
        self.assertEqual(by_number[34].exam_part, 1)
        self.assertEqual(by_number[35].exam_part, 2)
