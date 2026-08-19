from datetime import date

from django.test import TestCase

from analytics.engine import AnalyticsEngine
from analytics.engine.catalog import get_task_metadata
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.task_topics import is_expanded_answer_task, part2_start_task


class Part2StartTaskCatalogTests(TestCase):
    def test_ege_catalog_boundaries(self):
        self.assertEqual(part2_start_task("ege", "russian"), 27)
        self.assertEqual(part2_start_task("ege", "math_profile"), 13)
        self.assertEqual(part2_start_task("ege", "chemistry"), 29)
        self.assertEqual(part2_start_task("ege", "biology"), 22)
        self.assertEqual(part2_start_task("ege", "physics"), 21)
        self.assertEqual(part2_start_task("ege", "informatics"), 26)

    def test_task_before_and_at_boundary(self):
        cases = (
            ("russian", 26, 27),
            ("math_profile", 12, 13),
            ("chemistry", 28, 29),
            ("biology", 21, 22),
            ("physics", 20, 21),
            ("informatics", 25, 26),
        )
        for subject_key, part1_task, part2_task in cases:
            with self.subTest(subject=subject_key):
                self.assertEqual(part2_start_task("ege", subject_key), part2_task)
                before = get_task_metadata(_subject_name(subject_key), part1_task, "ege")
                at_boundary = get_task_metadata(_subject_name(subject_key), part2_task, "ege")
                self.assertEqual(before.exam_part, 1)
                self.assertEqual(at_boundary.exam_part, 2)

    def test_is_expanded_answer_task(self):
        self.assertFalse(is_expanded_answer_task("ege", "biology", 21))
        self.assertTrue(is_expanded_answer_task("ege", "biology", 22))
        self.assertFalse(is_expanded_answer_task("ege", "chemistry", 28))
        self.assertTrue(is_expanded_answer_task("ege", "chemistry", 29))
        self.assertFalse(is_expanded_answer_task("ege", "russian", 26))
        self.assertTrue(is_expanded_answer_task("ege", "russian", 27))
        self.assertFalse(is_expanded_answer_task("ege", "math_profile", 12))
        self.assertTrue(is_expanded_answer_task("ege", "math_profile", 13))
        self.assertFalse(is_expanded_answer_task("ege", "physics", 20))
        self.assertTrue(is_expanded_answer_task("ege", "physics", 21))
        self.assertFalse(is_expanded_answer_task("ege", "informatics", 25))
        self.assertTrue(is_expanded_answer_task("ege", "informatics", 26))

    def test_math_profile_unchanged(self):
        self.assertEqual(part2_start_task("ege", "math_profile"), 13)
        self.assertEqual(get_task_metadata("Математика профильная", 12, "ege").exam_part, 1)
        self.assertEqual(get_task_metadata("Математика профильная", 13, "ege").exam_part, 2)

    def test_subjects_without_catalog_keep_hardcoded_fallback(self):
        self.assertEqual(part2_start_task("ege", "geography"), 13)
        self.assertEqual(part2_start_task("oge", "math_basic"), 20)
        self.assertEqual(part2_start_task("oge", "russian"), 14)

    def test_explicit_short_part_length_still_overrides(self):
        self.assertEqual(part2_start_task("ege", "biology", short_part_length=21), 22)
        self.assertEqual(part2_start_task("ege", "biology", short_part_length=10), 11)


class AnalyticsEngineKimPartBoundaryTests(TestCase):
    def _make_exam(self, subject: str, task_count: int, code: str) -> tuple[School, Exam]:
        ministry = Ministry.objects.create(name=f"Мин {code}")
        district = District.objects.create(ministry=ministry, code=code, name=f"Район {code}")
        school = School.objects.create(district=district, code=code, name=f"Школа {code}")
        exam = Exam.objects.create(
            exam_type="ege",
            code=code,
            subject=subject,
            exam_date=date(2026, 6, 2),
            year=2026,
        )
        for idx in range(2):
            student = Student.objects.create(
                school=school,
                external_id=f"{code}-{idx}",
                full_name=f"Ученик {idx}",
            )
            ExamResult.objects.create(
                student=student,
                exam=exam,
                student_name=student.full_name,
                score=60,
                total_score=60,
                passed=True,
            )
            for task_number in range(1, task_count + 1):
                TaskResult.objects.create(
                    student=student,
                    exam=exam,
                    task_number=task_number,
                    value="+" if task_number % 2 else "-",
                )
        return school, exam

    def test_biology_13_21_are_part_1(self):
        school, exam = self._make_exam("Биология", 28, "01")
        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        parts = {task.task_number: task.exam_part for task in result.tasks}
        for number in range(13, 22):
            self.assertEqual(parts[number], 1, number)
        for number in range(22, 29):
            self.assertEqual(parts[number], 2, number)

    def test_russian_14_26_are_part_1(self):
        school, exam = self._make_exam("Русский язык", 27, "02")
        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        parts = {task.task_number: task.exam_part for task in result.tasks}
        for number in range(14, 27):
            self.assertEqual(parts[number], 1, number)
        self.assertEqual(parts[27], 2)

    def test_chemistry_13_28_are_part_1(self):
        school, exam = self._make_exam("Химия", 34, "03")
        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        parts = {task.task_number: task.exam_part for task in result.tasks}
        for number in range(13, 29):
            self.assertEqual(parts[number], 1, number)
        for number in range(29, 35):
            self.assertEqual(parts[number], 2, number)

    def test_math_profile_boundary_unchanged(self):
        school, exam = self._make_exam("Математика профильная", 19, "04")
        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        parts = {task.task_number: task.exam_part for task in result.tasks}
        for number in range(1, 13):
            self.assertEqual(parts[number], 1, number)
        for number in range(13, 20):
            self.assertEqual(parts[number], 2, number)

    def test_physics_1_20_are_part_1(self):
        school, exam = self._make_exam("Физика", 26, "05")
        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        parts = {task.task_number: task.exam_part for task in result.tasks}
        for number in range(1, 21):
            self.assertEqual(parts[number], 1, number)
        for number in range(21, 27):
            self.assertEqual(parts[number], 2, number)
        narrative = " ".join(result.raw.get("part_narrative") or [])
        self.assertIn("1–20", narrative)
        self.assertIn("21+", narrative)
        insights_text = " ".join(result.insights or [])
        self.assertIn("1–20", insights_text)
        recs_text = " ".join(result.recommendations or [])
        sections = result.sections or {}
        part_section = " ".join(sections.get("5.1 Анализ частей экзамена") or [])
        self.assertTrue(
            "21+" in recs_text or "21+" in part_section or "21+" in insights_text
        )

    def test_informatics_1_25_are_part_1(self):
        school, exam = self._make_exam("Информатика", 27, "06")
        result = AnalyticsEngine().analyze_exam(school.id, exam.id)
        self.assertTrue(result.valid, result.error_message)
        parts = {task.task_number: task.exam_part for task in result.tasks}
        for number in range(1, 26):
            self.assertEqual(parts[number], 1, number)
        self.assertEqual(parts[26], 2)
        self.assertEqual(parts[27], 2)
        narrative = " ".join(result.raw.get("part_narrative") or [])
        self.assertIn("1–25", narrative)
        self.assertIn("26+", narrative)


def _subject_name(subject_key: str) -> str:
    return {
        "russian": "Русский язык",
        "math_profile": "Математика профильная",
        "chemistry": "Химия",
        "biology": "Биология",
        "physics": "Физика",
        "informatics": "Информатика",
    }[subject_key]
