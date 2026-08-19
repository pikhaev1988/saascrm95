from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    EGE_LITERATURE_TASK_SKILLS,
    EGE_LITERATURE_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 11
PART2_TASKS = {11}


class LiteratureEge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_11_have_static_topics_and_skills(self):
        for number in range(1, 12):
            with self.subTest(task=number):
                self.assertIn(number, EGE_LITERATURE_TASK_TOPICS)
                self.assertIn(number, EGE_LITERATURE_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("Литература", number, "ege"),
                    EGE_LITERATURE_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Литература", number, "ege"),
                    EGE_LITERATURE_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(is_expanded_answer_task("ege", "literature", number), number)
        for number in PART2_TASKS:
            self.assertTrue(is_expanded_answer_task("ege", "literature", number), number)
        self.assertEqual(part2_start_task("ege", "literature"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("литература", 5, "ege"),
            EGE_LITERATURE_TASK_TOPICS[5],
        )
        self.assertEqual(
            skill_for_task("ЛИТЕРАТУРА", 11, "ege"),
            EGE_LITERATURE_TASK_SKILLS[11],
        )


class LiteratureEge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин LI")
        district = District.objects.create(ministry=ministry, code="LI", name="Район LI")
        school = School.objects.create(district=district, code="LI", name="Школа LI")
        exam = Exam.objects.create(
            exam_type="ege",
            code="LI01",
            subject="Литература",
            exam_date=date(2026, 6, 2),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="LI-1",
            full_name="Ученик LI",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=40,
            total_score=40,
            passed=True,
        )
        for task_number in range(1, 12):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, EGE_LITERATURE_TASK_TOPICS[1])
        self.assertEqual(by_number[5].topic, EGE_LITERATURE_TASK_TOPICS[5])
        self.assertEqual(by_number[11].topic, EGE_LITERATURE_TASK_TOPICS[11])
        self.assertEqual(by_number[5].skill_name, EGE_LITERATURE_TASK_SKILLS[5])
        self.assertEqual(by_number[10].exam_part, 1)
        self.assertEqual(by_number[11].exam_part, 2)
