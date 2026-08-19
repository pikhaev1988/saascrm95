from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    OGE_LITERATURE_TASK_SKILLS,
    OGE_LITERATURE_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 5


class LiteratureOge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_5_have_static_topics_and_skills(self):
        for number in range(1, 6):
            with self.subTest(task=number):
                self.assertIn(number, OGE_LITERATURE_TASK_TOPICS)
                self.assertIn(number, OGE_LITERATURE_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("Литература", number, "oge"),
                    OGE_LITERATURE_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Литература", number, "oge"),
                    OGE_LITERATURE_TASK_SKILLS[number],
                )

    def test_part2_boundary(self):
        self.assertEqual(part2_start_task("oge", "literature"), EXPECTED_BOUNDARY)

    def test_all_performed_tasks_are_expanded_written_answers(self):
        for number in range(1, 6):
            self.assertTrue(
                is_expanded_answer_task("oge", "literature", number),
                number,
            )

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("литература", 3, "oge"),
            OGE_LITERATURE_TASK_TOPICS[3],
        )
        self.assertEqual(
            skill_for_task("ЛИТЕРАТУРА", 5, "oge"),
            OGE_LITERATURE_TASK_SKILLS[5],
        )

    def test_oge_topics_override_enriched_catalog(self):
        topic = topic_for_task("Литература", 1, "oge")
        self.assertEqual(topic, OGE_LITERATURE_TASK_TOPICS[1])
        self.assertNotEqual(topic, "Анализ текста")


class LiteratureOge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин LI OGE")
        district = District.objects.create(ministry=ministry, code="LIO", name="Район LIO")
        school = School.objects.create(district=district, code="LIO", name="Школа LIO")
        exam = Exam.objects.create(
            exam_type="oge",
            code="LIO1",
            subject="Литература",
            exam_date=date(2026, 6, 5),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="LIO-1",
            full_name="Ученик LIO",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=4,
            total_score=4,
            passed=True,
        )
        for task_number in range(1, 6):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, OGE_LITERATURE_TASK_TOPICS[1])
        self.assertEqual(by_number[4].topic, OGE_LITERATURE_TASK_TOPICS[4])
        self.assertEqual(by_number[5].topic, OGE_LITERATURE_TASK_TOPICS[5])
        self.assertEqual(by_number[3].skill_name, OGE_LITERATURE_TASK_SKILLS[3])
        self.assertEqual(by_number[4].exam_part, 1)
        self.assertEqual(by_number[5].exam_part, 2)
