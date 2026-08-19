from django.test import TestCase

from analytics.knowledge.parser import parse_topic_text
from analytics.knowledge.service import TaskKnowledgeIndexer
from analytics.knowledge_models import TaskKnowledge


class TaskKnowledgeParserTests(TestCase):
    def test_biology_chemical_composition_is_allowed(self):
        from analytics.engine.catalog import validate_topic_belongs_to_subject

        errors = validate_topic_belongs_to_subject(
            "Биология", "ege", "Химический состав и строение клетки"
        )
        self.assertEqual(errors, [])

    def test_parse_russian_topic_with_fipi_code(self):
        parsed = parse_topic_text(
            "10 класс, п. 19.6.9. Логикосмысловые отношения между предложениями в тексте",
            [10],
            subject_key="russian",
        )
        self.assertIn("Логикосмысловые", parsed.topic)
        self.assertEqual(parsed.fgos_class_start, 10)
        self.assertTrue(parsed.fipi_content_code)
        self.assertEqual(parsed.section, "Работа с текстом")

    def test_parse_math_topic(self):
        parsed = parse_topic_text("Логарифмические уравнения", [10, 11], subject_key="math_profile")
        self.assertEqual(parsed.topic, "Логарифмические уравнения")
        self.assertEqual(parsed.fgos_class_start, 10)
        self.assertIn(11, parsed.fgos_class_repeat)
        self.assertEqual(parsed.section, "Логарифмы")

    def test_parse_biology_multi_grade_fipi(self):
        parsed = parse_topic_text(
            "10 кл., п. 119.6.2. Живые системы и их организация "
            "9 кл., п. 157.7.1. Человек – биосоциальный вид",
            [9, 10, 11],
            subject_key="biology",
        )
        self.assertIn("Человек", parsed.topic)
        self.assertTrue(parsed.section)

    def test_parse_oge_math_corrupted_topic_fallback(self):
        parsed = parse_topic_text(
            "5 класс: ; 6 класс: ; 8 класс",
            [5, 6, 8],
            subject_key="math_basic",
            exam_type="oge",
        )
        self.assertFalse(parsed.topic.strip() in {":", ""})


class TaskKnowledgeIndexerTests(TestCase):
    def setUp(self):
        TaskKnowledgeIndexer().index_all(document_year=2026)

    def test_index_math_profile_task_13(self):
        row = TaskKnowledge.objects.filter(
            exam_type="ege", subject_key="math_profile", task_number=13
        ).first()
        self.assertIsNotNone(row)
        self.assertIn("Логарифм", row.topic)
        self.assertEqual(row.fgos_class_start, 10)
        self.assertTrue(row.previous_topics)

    def test_index_russian_ege_task_21(self):
        row = TaskKnowledge.objects.filter(
            exam_type="ege", subject_key="russian", task_number=21
        ).first()
        self.assertIsNotNone(row)
        self.assertIn("Пунктуацион", row.topic)
        self.assertIn(row.section, ("Пунктуация", "Синтаксис", ""))

    def test_index_physics_oge_task_1(self):
        row = TaskKnowledge.objects.filter(
            exam_type="oge", subject_key="physics", task_number=1
        ).first()
        self.assertIsNotNone(row)
        self.assertIn("Кинемат", row.topic)

    def test_index_oge_math_basic_task_13(self):
        row = TaskKnowledge.objects.filter(
            exam_type="oge", subject_key="math_basic", task_number=13
        ).first()
        self.assertIsNotNone(row)
        self.assertIn("Геометр", row.topic)
        self.assertGreater(len(row.topic), 8)

    def test_index_social_studies_ege(self):
        row = TaskKnowledge.objects.filter(
            exam_type="ege", subject_key="social_studies", task_number=1
        ).first()
        self.assertIsNotNone(row)
        self.assertTrue(len(row.topic) > 5)

    def test_all_subjects_indexed(self):
        for exam_type in ("ege", "oge"):
            keys = TaskKnowledge.objects.filter(exam_type=exam_type).values_list(
                "subject_key", flat=True
            ).distinct()
            self.assertGreater(len(keys), 5, f"Мало предметов для {exam_type}")
