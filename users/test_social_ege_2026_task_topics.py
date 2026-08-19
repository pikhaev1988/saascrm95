from django.test import TestCase

from users.task_topics import (
    EGE_SOCIAL_TASK_SKILLS,
    EGE_SOCIAL_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 17
PART2_TASKS = range(17, 26)


class SocialEge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_25_have_static_topics_and_skills(self):
        for number in range(1, 26):
            with self.subTest(task=number):
                self.assertIn(number, EGE_SOCIAL_TASK_TOPICS)
                self.assertIn(number, EGE_SOCIAL_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("Обществознание", number, "ege"),
                    EGE_SOCIAL_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("Обществознание", number, "ege"),
                    EGE_SOCIAL_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(
                is_expanded_answer_task("ege", "social_studies", number),
                number,
            )
        for number in PART2_TASKS:
            self.assertTrue(
                is_expanded_answer_task("ege", "social_studies", number),
                number,
            )
        self.assertEqual(part2_start_task("ege", "social_studies"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("обществознание", 12, "ege"),
            EGE_SOCIAL_TASK_TOPICS[12],
        )
        self.assertEqual(
            skill_for_task("ОБЩЕСТВОЗНАНИЕ", 25, "ege"),
            EGE_SOCIAL_TASK_SKILLS[25],
        )


class SocialEge2026ReportTopicIntegrationTests(TestCase):
    def test_analytics_engine_uses_fipi_topics(self):
        from datetime import date

        from analytics.engine import AnalyticsEngine
        from exams.models import Exam, ExamResult, Student, TaskResult
        from organizations.models import District, Ministry, School

        ministry = Ministry.objects.create(name="Мин OB")
        district = District.objects.create(ministry=ministry, code="OB", name="Район OB")
        school = School.objects.create(district=district, code="OB", name="Школа OB")
        exam = Exam.objects.create(
            exam_type="ege",
            code="OB01",
            subject="Обществознание",
            exam_date=date(2026, 6, 11),
            year=2026,
        )
        student = Student.objects.create(
            school=school,
            external_id="OB-1",
            full_name="Ученик OB",
        )
        ExamResult.objects.create(
            student=student,
            exam=exam,
            student_name=student.full_name,
            score=50,
            total_score=50,
            passed=True,
        )
        for task_number in range(1, 26):
            TaskResult.objects.create(
                student=student,
                exam=exam,
                task_number=task_number,
                value="+",
            )

        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[3].topic, EGE_SOCIAL_TASK_TOPICS[3])
        self.assertEqual(by_number[7].topic, EGE_SOCIAL_TASK_TOPICS[7])
        self.assertEqual(by_number[25].topic, EGE_SOCIAL_TASK_TOPICS[25])
        self.assertEqual(by_number[3].skill_name, EGE_SOCIAL_TASK_SKILLS[3])
