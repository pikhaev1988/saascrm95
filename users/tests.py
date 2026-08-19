from django.test import TestCase

from users.export_reports import ExamData, _build_analysis_payload
from users.task_topics import (
    OGE_MATH_TASK_TOPICS,
    parse_long_answer_mask,
    subject_key_candidates,
    topic_for_task,
)


class TaskTopicsTests(TestCase):
    def test_oge_math_subject_mapping(self):
        self.assertIn("math_basic", subject_key_candidates("Математика", "oge"))

    def test_oge_math_task_topics(self):
        self.assertEqual(topic_for_task("Математика", 1, "oge"), OGE_MATH_TASK_TOPICS[1])
        self.assertEqual(topic_for_task("Математика", 5, "oge"), OGE_MATH_TASK_TOPICS[5])
        self.assertNotIn("спецификации ФИПИ", topic_for_task("Математика", 5, "oge"))

    def test_parse_long_answer_mask(self):
        parsed = parse_long_answer_mask("0(2)1(2)0(2)", 20)
        self.assertEqual(parsed, [(20, "0"), (21, "1"), (22, "0")])


class ExamAnalysisPayloadTests(TestCase):
    def _math_oge_data(self, tasks):
        return ExamData(
            subject="Математика",
            date="02.06.2026",
            students_count=100,
            avg_score=3.85,
            min_score=2.0,
            max_score=5.0,
            pass_rate=98.9,
            tasks=tasks,
            strong_tasks=[],
            weak_tasks=[],
            recommendations=[],
            topic_deficits=[],
            exam_type="oge",
            score_values=[4.0] * 100,
            exam_year=2026,
            dynamics=[],
        )

    def test_oge_math_uses_math_competencies(self):
        tasks = [
            {"id": i, "success_rate": 60.0, "correct": 6, "wrong": 4, "total": 10}
            for i in range(1, 20)
        ]
        payload = _build_analysis_payload(self._math_oge_data(tasks))
        skills_text = " ".join(payload["sections"]["8. Дефициты учебных умений"]).lower()
        self.assertNotIn("синтаксическ", skills_text)
        self.assertNotIn("письменной речи", skills_text)
        self.assertTrue(
            any(token in skills_text for token in ("вычисл", "алгебр", "геометр", "уравнен", "модел"))
        )

    def test_no_false_part2_zero_when_missing(self):
        tasks = [
            {"id": i, "success_rate": 84.9, "correct": 8, "wrong": 2, "total": 10}
            for i in range(1, 20)
        ]
        payload = _build_analysis_payload(self._math_oge_data(tasks))
        analysis_lines = payload["sections"]["5. Анализ выполнения заданий"]
        joined = " ".join(analysis_lines)
        self.assertIn("отсутствуют", joined.lower())
        self.assertNotIn("часть 2: 0.0%", joined.lower())
        conclusion = payload["sections"]["10. Выводы"][0].lower()
        self.assertNotIn("недостаточн", conclusion)

    def test_weak_tasks_only_below_50(self):
        tasks = [
            {"id": 1, "success_rate": 66.3, "correct": 6, "wrong": 3, "total": 9},
            {"id": 2, "success_rate": 59.8, "correct": 6, "wrong": 4, "total": 10},
            {"id": 5, "success_rate": 51.1, "correct": 5, "wrong": 5, "total": 10},
        ]
        payload = _build_analysis_payload(self._math_oge_data(tasks))
        analysis_lines = payload["sections"]["5. Анализ выполнения заданий"]
        joined = " ".join(analysis_lines)
        self.assertIn("Слабые задания (успешность ниже 50%): нет", joined)
        self.assertIn("Относительно более сложные", joined)

    def test_control_plan_uses_grade_9_for_oge(self):
        tasks = [
            {"id": 1, "success_rate": 30.0, "correct": 3, "wrong": 7, "total": 10},
        ]
        payload = _build_analysis_payload(self._math_oge_data(tasks))
        self.assertTrue(payload["control_plan"])
        self.assertIn("9", payload["control_plan"][0]["classes"])
