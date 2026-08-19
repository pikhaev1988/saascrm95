from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    OGE_CHEMISTRY_TASK_SKILLS,
    OGE_CHEMISTRY_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 20
PART2_TASKS = range(20, 24)


class ChemistryOge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_23_have_static_topics_and_skills(self):
        for number in range(1, 24):
            with self.subTest(task=number):
                self.assertIn(number, OGE_CHEMISTRY_TASK_TOPICS)
                self.assertIn(number, OGE_CHEMISTRY_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("Химия", number, "oge"),
                    OGE_CHEMISTRY_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Химия", number, "oge"),
                    OGE_CHEMISTRY_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(
                is_expanded_answer_task("oge", "chemistry", number),
                number,
            )
        for number in PART2_TASKS:
            self.assertTrue(
                is_expanded_answer_task("oge", "chemistry", number),
                number,
            )
        self.assertEqual(part2_start_task("oge", "chemistry"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("химия", 14, "oge"),
            OGE_CHEMISTRY_TASK_TOPICS[14],
        )
        self.assertEqual(
            skill_for_task("ХИМИЯ", 23, "oge"),
            OGE_CHEMISTRY_TASK_SKILLS[23],
        )

    def test_oge_topics_override_enriched_catalog(self):
        topic = topic_for_task("Химия", 8, "oge")
        self.assertEqual(topic, OGE_CHEMISTRY_TASK_TOPICS[8])
        self.assertNotIn("углеводород", topic.lower())


class ChemistryOge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин HI OGE")
        district = District.objects.create(ministry=ministry, code="HIO", name="Район HIO")
        school = School.objects.create(district=district, code="HIO", name="Школа HIO")
        exam = Exam.objects.create(
            exam_type="oge",
            code="HIO1",
            subject="Химия",
            exam_date=date(2026, 6, 5),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="HIO-1",
            full_name="Ученик HIO",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=30,
            total_score=30,
            passed=True,
        )
        for task_number in range(1, 24):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, OGE_CHEMISTRY_TASK_TOPICS[1])
        self.assertEqual(by_number[15].topic, OGE_CHEMISTRY_TASK_TOPICS[15])
        self.assertEqual(by_number[23].topic, OGE_CHEMISTRY_TASK_TOPICS[23])
        self.assertEqual(by_number[7].skill_name, OGE_CHEMISTRY_TASK_SKILLS[7])
        self.assertEqual(by_number[22].skill_name, OGE_CHEMISTRY_TASK_SKILLS[22])
        self.assertEqual(by_number[19].exam_part, 1)
        self.assertEqual(by_number[20].exam_part, 2)
