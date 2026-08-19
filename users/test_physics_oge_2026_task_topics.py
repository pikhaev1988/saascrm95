from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    OGE_PHYSICS_TASK_SKILLS,
    OGE_PHYSICS_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 17
PART2_TASKS = range(17, 23)


class PhysicsOge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_22_have_static_topics_and_skills(self):
        for number in range(1, 23):
            with self.subTest(task=number):
                self.assertIn(number, OGE_PHYSICS_TASK_TOPICS)
                self.assertIn(number, OGE_PHYSICS_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("Физика", number, "oge"),
                    OGE_PHYSICS_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Физика", number, "oge"),
                    OGE_PHYSICS_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(
                is_expanded_answer_task("oge", "physics", number),
                number,
            )
        for number in PART2_TASKS:
            self.assertTrue(
                is_expanded_answer_task("oge", "physics", number),
                number,
            )
        self.assertEqual(part2_start_task("oge", "physics"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("физика", 9, "oge"),
            OGE_PHYSICS_TASK_TOPICS[9],
        )
        self.assertEqual(
            skill_for_task("ФИЗИКА", 22, "oge"),
            OGE_PHYSICS_TASK_SKILLS[22],
        )

    def test_oge_topics_override_enriched_catalog(self):
        topic = topic_for_task("Физика", 1, "oge")
        self.assertEqual(topic, OGE_PHYSICS_TASK_TOPICS[1])
        self.assertNotEqual(topic, "Кинематика")
        self.assertNotIn("теория относительности", topic.lower())


class PhysicsOge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин FI OGE")
        district = District.objects.create(ministry=ministry, code="FIO", name="Район FIO")
        school = School.objects.create(district=district, code="FIO", name="Школа FIO")
        exam = Exam.objects.create(
            exam_type="oge",
            code="FIO1",
            subject="Физика",
            exam_date=date(2026, 6, 5),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="FIO-1",
            full_name="Ученик FIO",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=30,
            total_score=30,
            passed=True,
        )
        for task_number in range(1, 23):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, OGE_PHYSICS_TASK_TOPICS[1])
        self.assertEqual(by_number[8].topic, OGE_PHYSICS_TASK_TOPICS[8])
        self.assertEqual(by_number[17].topic, OGE_PHYSICS_TASK_TOPICS[17])
        self.assertEqual(by_number[5].skill_name, OGE_PHYSICS_TASK_SKILLS[5])
        self.assertEqual(by_number[22].skill_name, OGE_PHYSICS_TASK_SKILLS[22])
        self.assertEqual(by_number[16].exam_part, 1)
        self.assertEqual(by_number[17].exam_part, 2)
