from datetime import date

from django.test import TestCase

from analytics.engine import AnalyticsEngine
from exams.models import Exam, ExamResult, Student, TaskResult
from organizations.models import District, Ministry, School
from users.export_reports import collect_subject_data_for_export, generate_school_subject_note_docx


class AnalyzeSubjectLatestAttemptTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Мин SUBJ")
        district = District.objects.create(ministry=ministry, code="SUBJ", name="Район SUBJ")
        self.school = School.objects.create(district=district, code="SUBJ", name="Школа SUBJ")
        self.student = Student.objects.create(
            school=self.school,
            external_id="SUBJ-1",
            full_name="Ученик SUBJ",
        )
        self.exam_main = Exam.objects.create(
            exam_type="ege",
            code="SUBJ1",
            subject="Математика базовая",
            exam_date=date(2026, 6, 8),
            year=2026,
        )
        self.exam_reserve = Exam.objects.create(
            exam_type="ege",
            code="SUBJ2",
            subject="Математика базовая",
            exam_date=date(2026, 6, 22),
            year=2026,
        )
        ExamResult.objects.create(
            student=self.student,
            exam=self.exam_main,
            student_name=self.student.full_name,
            score=3,
            total_score=3,
            passed=False,
        )
        ExamResult.objects.create(
            student=self.student,
            exam=self.exam_reserve,
            student_name=self.student.full_name,
            score=4,
            total_score=4,
            passed=True,
            short_answer_tasks="+" * 21,
            long_answer_tasks="",
            primary_score=4,
        )
        for task_number in range(1, 22):
            TaskResult.objects.create(
                student=self.student,
                exam=self.exam_main,
                task_number=task_number,
                value="-",
            )
            TaskResult.objects.create(
                student=self.student,
                exam=self.exam_reserve,
                task_number=task_number,
                value="+",
            )

    def test_analyze_subject_uses_latest_attempt_per_student(self):
        result = AnalyticsEngine().analyze_subject(
            self.school.id,
            "ege",
            "Математика базовая",
            2026,
        )
        self.assertTrue(result.valid, result.error_message)
        self.assertEqual(result.students_count, 1)
        self.assertEqual(result.avg_score, 4.0)
        self.assertEqual(result.exam_date, "итоговые результаты за 2026 год")
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].success_rate, 100.0)

    def test_collect_subject_data_for_export_builds_full_report_payload(self):
        data = collect_subject_data_for_export(
            self.school.id,
            "ege",
            "Математика базовая",
            2026,
        )
        self.assertIsNotNone(data)
        assert data is not None
        self.assertEqual(data.students_count, 1)
        self.assertEqual(data.avg_score, 4.0)
        self.assertTrue(getattr(data, "engine_result", None))
        self.assertEqual(len(data.protocol_rows or []), 1)
        self.assertEqual(data.protocol_rows[0]["student_name"], "Ученик SUBJ")
        self.assertEqual(data.protocol_rows[0]["exam_date"], "22.06.2026")
        self.assertTrue(str(data.protocol_rows[0]["short_answer_tasks"]).startswith("+"))

    def test_generate_school_subject_note_docx_is_full_analytical_report(self):
        payload = generate_school_subject_note_docx(
            self.school.id,
            "ege",
            "Математика базовая",
            2026,
        )
        import zipfile
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(payload) as zf:
            root = ET.fromstring(zf.read("word/document.xml"))
        text = "".join(
            el.text or ""
            for el in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
        )
        self.assertIn("АНАЛИТИЧЕСКАЯ СПРАВКА", text)
        self.assertIn("итоговые результаты за 2026 год", text)
        self.assertIn("Приложение. Протокол экзамена", text)
        self.assertIn("Ученик SUBJ", text)
        self.assertIn("22.06.2026", text)

    def test_analyze_exam_still_uses_single_protocol(self):
        result = AnalyticsEngine().analyze_exam(self.school.id, self.exam_main.id)
        self.assertTrue(result.valid)
        self.assertEqual(result.avg_score, 3.0)
        by_number = {task.task_number: task for task in result.tasks}
        self.assertEqual(by_number[1].success_rate, 0.0)

    def test_analyze_district_subject_uses_latest_attempt_per_student(self):
        ministry = Ministry.objects.create(name="Мин DIST")
        district = District.objects.create(ministry=ministry, code="DIST", name="Район DIST")
        school = School.objects.create(district=district, code="DIST", name="Школа DIST")
        student = Student.objects.create(
            school=school,
            external_id="DIST-1",
            full_name="Ученик DIST",
        )
        exam_main = Exam.objects.create(
            exam_type="ege",
            code="DIST1",
            subject="Математика базовая",
            exam_date=date(2026, 6, 8),
            year=2026,
        )
        exam_reserve = Exam.objects.create(
            exam_type="ege",
            code="DIST2",
            subject="Математика базовая",
            exam_date=date(2026, 6, 22),
            year=2026,
        )
        ExamResult.objects.create(
            student=student,
            exam=exam_main,
            student_name=student.full_name,
            score=3,
            total_score=3,
            passed=False,
        )
        ExamResult.objects.create(
            student=student,
            exam=exam_reserve,
            student_name=student.full_name,
            score=4,
            total_score=4,
            passed=True,
        )
        for task_number in range(1, 22):
            TaskResult.objects.create(
                student=student, exam=exam_main, task_number=task_number, value="-"
            )
            TaskResult.objects.create(
                student=student, exam=exam_reserve, task_number=task_number, value="+"
            )

        result = AnalyticsEngine().analyze_district_subject(
            district.id,
            "ege",
            "Математика базовая",
            2026,
        )
        self.assertTrue(result.valid, result.error_message)
        self.assertEqual(result.students_count, 1)
        self.assertEqual(result.avg_score, 4.0)

        from users.district_export_reports import _build_district_subject_note_payload

        payload = _build_district_subject_note_payload(
            district.id,
            "ege",
            "Математика базовая",
            2026,
            with_ai=False,
        )
        self.assertTrue(payload["has_data"])
        self.assertEqual(payload["participants"], 1)
        self.assertEqual(payload["avg_score"], 4.0)
        self.assertEqual(payload["aggregate_label"], "итоговые результаты за 2026 год")
