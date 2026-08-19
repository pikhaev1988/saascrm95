from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    OGE_BIOLOGY_TASK_SKILLS,
    OGE_BIOLOGY_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 22
PART2_TASKS = range(22, 27)


class BiologyOge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_26_have_static_topics_and_skills(self):
        for number in range(1, 27):
            with self.subTest(task=number):
                self.assertIn(number, OGE_BIOLOGY_TASK_TOPICS)
                self.assertIn(number, OGE_BIOLOGY_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("Биология", number, "oge"),
                    OGE_BIOLOGY_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Биология", number, "oge"),
                    OGE_BIOLOGY_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(
                is_expanded_answer_task("oge", "biology", number),
                number,
            )
        for number in PART2_TASKS:
            self.assertTrue(
                is_expanded_answer_task("oge", "biology", number),
                number,
            )
        self.assertEqual(part2_start_task("oge", "biology"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("биология", 19, "oge"),
            OGE_BIOLOGY_TASK_TOPICS[19],
        )
        self.assertEqual(
            skill_for_task("БИОЛОГИЯ", 26, "oge"),
            OGE_BIOLOGY_TASK_SKILLS[26],
        )

    def test_oge_topics_override_enriched_catalog(self):
        topic = topic_for_task("Биология", 1, "oge")
        self.assertEqual(topic, OGE_BIOLOGY_TASK_TOPICS[1])
        self.assertNotIn("генетик", topic.lower())


class BiologyOge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин BI OGE")
        district = District.objects.create(ministry=ministry, code="BIO", name="Район BIO")
        school = School.objects.create(district=district, code="BIO", name="Школа BIO")
        exam = Exam.objects.create(
            exam_type="oge",
            code="BIO1",
            subject="Биология",
            exam_date=date(2026, 6, 5),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="BIO-1",
            full_name="Ученик BIO",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=38,
            total_score=38,
            passed=True,
        )
        for task_number in range(1, 27):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, OGE_BIOLOGY_TASK_TOPICS[1])
        self.assertEqual(by_number[14].topic, OGE_BIOLOGY_TASK_TOPICS[14])
        self.assertEqual(by_number[26].topic, OGE_BIOLOGY_TASK_TOPICS[26])
        self.assertEqual(by_number[8].skill_name, OGE_BIOLOGY_TASK_SKILLS[8])
        self.assertEqual(by_number[24].skill_name, OGE_BIOLOGY_TASK_SKILLS[24])
        self.assertEqual(by_number[21].exam_part, 1)
        self.assertEqual(by_number[22].exam_part, 2)
