from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    EGE_GERMAN_TASK_SKILLS,
    EGE_GERMAN_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 37
PART2_TASKS = range(37, 43)


class GermanEge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_42_have_static_topics_and_skills(self):
        for number in range(1, 43):
            with self.subTest(task=number):
                self.assertIn(number, EGE_GERMAN_TASK_TOPICS)
                self.assertIn(number, EGE_GERMAN_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("Немецкий язык", number, "ege"),
                    EGE_GERMAN_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Немецкий язык", number, "ege"),
                    EGE_GERMAN_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(
                is_expanded_answer_task("ege", "german", number),
                number,
            )
        for number in PART2_TASKS:
            self.assertTrue(
                is_expanded_answer_task("ege", "german", number),
                number,
            )
        self.assertEqual(part2_start_task("ege", "german"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("немецкий язык", 10, "ege"),
            EGE_GERMAN_TASK_TOPICS[10],
        )
        self.assertEqual(
            skill_for_task("НЕМЕЦКИЙ ЯЗЫК", 38, "ege"),
            EGE_GERMAN_TASK_SKILLS[38],
        )


class GermanEge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин DE")
        district = District.objects.create(ministry=ministry, code="DE", name="Район DE")
        school = School.objects.create(district=district, code="DE", name="Школа DE")
        exam = Exam.objects.create(
            exam_type="ege",
            code="DE01",
            subject="Немецкий язык",
            exam_date=date(2026, 6, 2),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="DE-1",
            full_name="Ученик DE",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=40,
            total_score=40,
            passed=True,
        )
        for task_number in range(1, 43):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, EGE_GERMAN_TASK_TOPICS[1])
        self.assertEqual(by_number[19].topic, EGE_GERMAN_TASK_TOPICS[19])
        self.assertEqual(by_number[37].topic, EGE_GERMAN_TASK_TOPICS[37])
        self.assertEqual(by_number[42].topic, EGE_GERMAN_TASK_TOPICS[42])
        self.assertEqual(by_number[10].skill_name, EGE_GERMAN_TASK_SKILLS[10])
        self.assertEqual(by_number[38].skill_name, EGE_GERMAN_TASK_SKILLS[38])
        self.assertEqual(by_number[36].exam_part, 1)
        self.assertEqual(by_number[37].exam_part, 2)
        self.assertEqual(by_number[42].exam_part, 2)
