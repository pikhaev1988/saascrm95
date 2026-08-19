from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    OGE_HISTORY_TASK_SKILLS,
    OGE_HISTORY_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 18
PART2_TASKS = range(18, 25)


class HistoryOge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_24_have_static_topics_and_skills(self):
        for number in range(1, 25):
            with self.subTest(task=number):
                self.assertIn(number, OGE_HISTORY_TASK_TOPICS)
                self.assertIn(number, OGE_HISTORY_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("История", number, "oge"),
                    OGE_HISTORY_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("История", number, "oge"),
                    OGE_HISTORY_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(
                is_expanded_answer_task("oge", "history", number),
                number,
            )
        for number in PART2_TASKS:
            self.assertTrue(
                is_expanded_answer_task("oge", "history", number),
                number,
            )
        self.assertEqual(part2_start_task("oge", "history"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("история", 10, "oge"),
            OGE_HISTORY_TASK_TOPICS[10],
        )
        self.assertEqual(
            skill_for_task("ИСТОРИЯ", 24, "oge"),
            OGE_HISTORY_TASK_SKILLS[24],
        )

    def test_oge_topics_override_enriched_catalog(self):
        topic = topic_for_task("История", 1, "oge")
        self.assertEqual(topic, OGE_HISTORY_TASK_TOPICS[1])
        self.assertIn("1914", topic)


class HistoryOge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин IS OGE")
        district = District.objects.create(ministry=ministry, code="ISO", name="Район ISO")
        school = School.objects.create(district=district, code="ISO", name="Школа ISO")
        exam = Exam.objects.create(
            exam_type="oge",
            code="ISO1",
            subject="История",
            exam_date=date(2026, 6, 5),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="ISO-1",
            full_name="Ученик ISO",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=30,
            total_score=30,
            passed=True,
        )
        for task_number in range(1, 25):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, OGE_HISTORY_TASK_TOPICS[1])
        self.assertEqual(by_number[15].topic, OGE_HISTORY_TASK_TOPICS[15])
        self.assertEqual(by_number[24].topic, OGE_HISTORY_TASK_TOPICS[24])
        self.assertEqual(by_number[7].skill_name, OGE_HISTORY_TASK_SKILLS[7])
        self.assertEqual(by_number[22].skill_name, OGE_HISTORY_TASK_SKILLS[22])
        self.assertEqual(by_number[17].exam_part, 1)
        self.assertEqual(by_number[18].exam_part, 2)
