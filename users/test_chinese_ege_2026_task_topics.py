from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import (
    EGE_CHINESE_TASK_SKILLS,
    EGE_CHINESE_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 28
PART2_TASKS = range(28, 33)


class ChineseEge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_32_have_static_topics_and_skills(self):
        for number in range(1, 33):
            with self.subTest(task=number):
                self.assertIn(number, EGE_CHINESE_TASK_TOPICS)
                self.assertIn(number, EGE_CHINESE_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("Китайский язык", number, "ege"),
                    EGE_CHINESE_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Китайский язык", number, "ege"),
                    EGE_CHINESE_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(
                is_expanded_answer_task("ege", "chinese", number),
                number,
            )
        for number in PART2_TASKS:
            self.assertTrue(
                is_expanded_answer_task("ege", "chinese", number),
                number,
            )
        self.assertEqual(part2_start_task("ege", "chinese"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("китайский язык", 15, "ege"),
            EGE_CHINESE_TASK_TOPICS[15],
        )
        self.assertEqual(
            skill_for_task("КИТАЙСКИЙ ЯЗЫК", 29, "ege"),
            EGE_CHINESE_TASK_SKILLS[29],
        )


class ChineseEge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics_and_skills(self):
        from datetime import date

        ministry = Ministry.objects.create(name="Мин CN")
        district = District.objects.create(ministry=ministry, code="CN", name="Район CN")
        school = School.objects.create(district=district, code="CN", name="Школа CN")
        exam = Exam.objects.create(
            exam_type="ege",
            code="CN01",
            subject="Китайский язык",
            exam_date=date(2026, 6, 2),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="CN-1",
            full_name="Ученик CN",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=40,
            total_score=40,
            passed=True,
        )
        for task_number in range(1, 33):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].topic, EGE_CHINESE_TASK_TOPICS[1])
        self.assertEqual(by_number[15].topic, EGE_CHINESE_TASK_TOPICS[15])
        self.assertEqual(by_number[28].topic, EGE_CHINESE_TASK_TOPICS[28])
        self.assertEqual(by_number[32].topic, EGE_CHINESE_TASK_TOPICS[32])
        self.assertEqual(by_number[10].skill_name, EGE_CHINESE_TASK_SKILLS[10])
        self.assertEqual(by_number[29].skill_name, EGE_CHINESE_TASK_SKILLS[29])
        self.assertEqual(by_number[27].exam_part, 1)
        self.assertEqual(by_number[28].exam_part, 2)
        self.assertEqual(by_number[32].exam_part, 2)
