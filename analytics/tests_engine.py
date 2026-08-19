from django.test import TestCase

from analytics.engine import AnalyticsEngine, VALIDATION_ERROR_MESSAGE
from analytics.engine.statistics import classify_by_thresholds, dynamic_thresholds, pearson_correlation
from analytics.engine.tokens import is_success_token
from analytics.engine.validation import validate_exam_metrics
from users.export_reports import ExamData, _build_analysis_payload


class AnalyticsEngineTokenTests(TestCase):
    def test_success_tokens(self):
        self.assertTrue(is_success_token("+"))
        self.assertTrue(is_success_token("2"))
        self.assertFalse(is_success_token("-"))
        self.assertFalse(is_success_token("0"))
        self.assertFalse(is_success_token(""))


class AnalyticsEngineStatisticsTests(TestCase):
    def test_dynamic_thresholds(self):
        thresholds = dynamic_thresholds([20.0, 40.0, 60.0, 80.0])
        self.assertLessEqual(thresholds["critical"], thresholds["weak"])
        self.assertEqual(classify_by_thresholds(10, thresholds), "критическое")
        self.assertEqual(classify_by_thresholds(90, thresholds), "сильное")

    def test_pearson(self):
        corr = pearson_correlation([1, 2, 3, 4], [1, 2, 3, 4])
        self.assertAlmostEqual(corr, 1.0, places=3)


class AnalyticsEngineValidationTests(TestCase):
    def test_validation_detects_avg_mismatch(self):
        valid, errors = validate_exam_metrics(
            students_count=2,
            avg_score=50.0,
            median_score=50.0,
            min_score=40.0,
            max_score=60.0,
            pass_count=2,
            fail_count=0,
            score_values=[40.0, 60.0],
            tasks=[{"task_number": 1, "total": 2, "correct": 1, "wrong": 1, "blank": 0, "success_rate": 50.0}],
            raw_task_rows=[{"task_number": 1, "value": "+"}, {"task_number": 1, "value": "-"}],
        )
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_validation_fails_on_count_mismatch(self):
        valid, errors = validate_exam_metrics(
            students_count=3,
            avg_score=50.0,
            median_score=50.0,
            min_score=40.0,
            max_score=60.0,
            pass_count=2,
            fail_count=0,
            score_values=[40.0, 60.0],
            tasks=[],
            raw_task_rows=[],
        )
        self.assertFalse(valid)
        self.assertTrue(errors)


class AnalyticsEngineIntegrationTests(TestCase):
    def test_build_payload_legacy_path_still_works(self):
        tasks = [
            {"id": i, "success_rate": 60.0, "correct": 6, "wrong": 4, "total": 10}
            for i in range(1, 20)
        ]
        data = ExamData(
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
        payload = _build_analysis_payload(data)
        self.assertIn("sections", payload)
        self.assertIn("5. Анализ выполнения заданий", payload["sections"])


class AnalyticsEngineMessageTests(TestCase):
    def test_validation_message_constant(self):
        self.assertIn("несоответствие", VALIDATION_ERROR_MESSAGE.lower())


class CatalogMetadataPriorityTests(TestCase):
    """Official catalog metadata must override enriched/legacy sources."""

    def test_get_task_metadata_uses_catalog_kim_part(self):
        from analytics.engine.catalog import get_task_metadata
        # Russian: task 14 should be part 1 (not part 2 as old hardcoded 13/14 boundary)
        meta = get_task_metadata("Русский язык", 14, "ege")
        self.assertEqual(meta.exam_part, 1)
        meta26 = get_task_metadata("Русский язык", 26, "ege")
        self.assertEqual(meta26.exam_part, 1)
        meta27 = get_task_metadata("Русский язык", 27, "ege")
        self.assertEqual(meta27.exam_part, 2)

    def test_get_task_metadata_uses_catalog_topic(self):
        from analytics.engine.catalog import get_task_metadata
        meta = get_task_metadata("Русский язык", 14, "ege")
        # Should come from catalog display_name, not legacy "Орфография и пунктуация"
        self.assertNotEqual(meta.topic, "Орфография и пунктуация")
        self.assertTrue(len(meta.topic) > 5)

    def test_get_task_metadata_uses_catalog_section_as_block(self):
        from analytics.engine.catalog import get_task_metadata
        meta = get_task_metadata("Русский язык", 1, "ege")
        # theme.block for task 1 is "Текст"
        self.assertEqual(meta.section, "Текст")

    def test_get_task_metadata_school_program_grades(self):
        from analytics.engine.catalog import get_task_metadata
        meta = get_task_metadata("Русский язык", 1, "ege")
        self.assertTrue(len(meta.grade_range) > 0, "grade_range should come from catalog")

    def test_chemistry_part_boundaries(self):
        from analytics.engine.catalog import get_task_metadata
        meta28 = get_task_metadata("Химия", 28, "ege")
        meta29 = get_task_metadata("Химия", 29, "ege")
        self.assertEqual(meta28.exam_part, 1)
        self.assertEqual(meta29.exam_part, 2)

    def test_biology_part_boundaries(self):
        from analytics.engine.catalog import get_task_metadata
        meta21 = get_task_metadata("Биология", 21, "ege")
        meta22 = get_task_metadata("Биология", 22, "ege")
        self.assertEqual(meta21.exam_part, 1)
        self.assertEqual(meta22.exam_part, 2)

    def test_subjects_without_catalog_fallback(self):
        from analytics.engine.catalog import get_task_metadata
        meta = get_task_metadata("География", 13, "ege")
        self.assertEqual(meta.exam_part, 2)  # fallback: 13 boundary


class NoDuplicateTopicsTests(TestCase):
    """Strong topics must not duplicate when multiple tasks share display_name."""

    def test_strength_summary_deduplicates(self):
        from analytics.knowledge.graph import TaskContext, build_strength_summary
        ctxs = [
            TaskContext(task_number=n, success_rate=85.0, classification="сильное",
                        topic="Грамматика и письменная речь", section="Грамматика", subsection="",
                        skill_name="навык", grade_range=[], exam_part=2)
            for n in range(28, 37)
        ]
        summary = build_strength_summary(ctxs, subject_name="Русский язык", subject_avg=60.0)
        topic_names = [t["topic"] for t in summary["topics"]]
        self.assertEqual(len(set(topic_names)), len(topic_names), "Topics should be deduplicated")
        # Should be only 1 entry for the same topic
        self.assertEqual(len(topic_names), 1)
        # That entry should aggregate all tasks
        self.assertEqual(sorted(summary["topics"][0]["tasks"]), list(range(28, 37)))


class NoFalseCausalityTests(TestCase):
    """Deficit causes must not claim false causation."""

    def test_deficit_cause_no_unsubstantiated_claims(self):
        from analytics.knowledge.graph import TaskContext, build_intelligent_deficit_cause
        ctx = TaskContext(
            task_number=14, success_rate=20.0, classification="критическое",
            topic="Слитное, дефисное и раздельное написание слов",
            section="Орфография", subsection="Правописание",
            skill_name="навык", grade_range=[], exam_part=1,
        )
        topic_graph = {
            ctx.topic[:200]: {
                "topic": ctx.topic,
                "section": ctx.section,
                "subsection": ctx.subsection,
                "prerequisites": [],
                "dependents": [],
                "tasks": [14],
                "avg_success": 20.0,
            }
        }
        result = build_intelligent_deficit_cause(
            ctx, subject_name="Русский язык", exam_type="ege",
            topic_graph=topic_graph, task_success_map={14: 20.0},
        )
        cause = result.get("cause", "")
        self.assertNotIn("обусловлена недостаточным освоением", cause)
        self.assertNotIn("невозможно успешное выполнение", cause)


class ReportConsistencyTests(TestCase):
    """HTML/DOCX/PDF must share the same analytics payload."""

    def test_to_legacy_payload_uses_engine_sections(self):
        from analytics.engine.adapters import to_legacy_payload
        from analytics.engine.result import ExamAnalysisResult
        result = ExamAnalysisResult(
            valid=True,
            students_count=10,
            avg_score=60.0,
            sections={"5.1 Анализ частей экзамена": ["Часть 1: 70%; часть 2: 30%"]},
            raw={"unified_recommendations": {"Дефициты": ["rec1"]}},
        )
        payload = to_legacy_payload(result)
        self.assertEqual(payload["sections"], result.sections)
        self.assertEqual(payload["recommendations"], result.raw["unified_recommendations"])


class DashboardChartAdapterTests(TestCase):
    def test_minus_counts_filled_from_tasks(self):
        from analytics.engine.adapters import to_dashboard_analysis
        from analytics.engine.result import ExamAnalysisResult, TaskAnalysis

        task = TaskAnalysis(
            task_number=1,
            total=2,
            correct=1,
            wrong=1,
            blank=0,
            success_rate=50.0,
            error_rate=50.0,
            blank_rate=0.0,
            avg_score=None,
            difficulty=0.5,
            discrimination=0.0,
            score_correlation=0.0,
            result_contribution=0.0,
            classification="слабое",
            topic="Тема",
            section="",
            subsection="",
            fipi_code="",
            skill="",
            skill_name="",
            grade_range=[],
            exam_part=1,
            max_score=None,
        )
        result = ExamAnalysisResult(
            valid=True,
            students_count=2,
            avg_score=50.0,
            median_score=50.0,
            min_score=40.0,
            max_score=60.0,
            pass_rate=100.0,
            fail_rate=0.0,
            tasks=[task],
            chart={"labels": ["№1"], "success_rates": [50.0]},
        )
        payload = to_dashboard_analysis(result)
        self.assertEqual(payload["chart"]["minus_counts"], [1])
