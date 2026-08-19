from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    OGE_INFORMATICS_TASK_SKILLS,
    OGE_INFORMATICS_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 13
PART2_TASKS = range(13, 17)


class InformaticsOge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_16_have_static_topics_and_skills(self):
        for number in range(1, 17):
            with self.subTest(task=number):
                self.assertIn(number, OGE_INFORMATICS_TASK_TOPICS)
                self.assertIn(number, OGE_INFORMATICS_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("Информатика", number, "oge"),
                    OGE_INFORMATICS_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Информатика", number, "oge"),
                    OGE_INFORMATICS_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(
                is_expanded_answer_task("oge", "informatics", number),
                number,
            )
        for number in PART2_TASKS:
            self.assertTrue(
                is_expanded_answer_task("oge", "informatics", number),
                number,
            )
        self.assertEqual(part2_start_task("oge", "informatics"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("информатика", 10, "oge"),
            OGE_INFORMATICS_TASK_TOPICS[10],
        )
        self.assertEqual(
            skill_for_task("ИНФОРМАТИКА", 16, "oge"),
            OGE_INFORMATICS_TASK_SKILLS[16],
        )

    def test_oge_topics_override_enriched_catalog(self):
        topic = topic_for_task("Информатика", 1, "oge")
        self.assertEqual(topic, OGE_INFORMATICS_TASK_TOPICS[1])
        self.assertNotIn("моделирован", topic.lower())


class InformaticsOge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин INF OGE")
        district = District.objects.create(ministry=ministry, code="INO", name="Район INO")
        school = School.objects.create(district=district, code="INO", name="Школа INO")
        exam = Exam.objects.create(
            exam_type="oge",
            code="INO1",
            subject="Информатика",
            exam_date=date(2026, 6, 6),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="INO-1",
            full_name="Ученик INO",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=18,
            total_score=18,
            passed=True,
        )
        for task_number in range(1, 17):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, OGE_INFORMATICS_TASK_TOPICS[1])
        self.assertEqual(by_number[8].topic, OGE_INFORMATICS_TASK_TOPICS[8])
        self.assertEqual(by_number[16].topic, OGE_INFORMATICS_TASK_TOPICS[16])
        self.assertEqual(by_number[5].skill_name, OGE_INFORMATICS_TASK_SKILLS[5])
        self.assertEqual(by_number[14].skill_name, OGE_INFORMATICS_TASK_SKILLS[14])
        self.assertEqual(by_number[12].exam_part, 1)
        self.assertEqual(by_number[13].exam_part, 2)
