from django.test import TestCase

from analytics.knowledge.graph import (
    build_intelligent_deficit_cause,
    merge_deficits_by_section,
    priority_tier,
    TaskContext,
)


class KnowledgeGraphTests(TestCase):
    def test_priority_tiers(self):
        self.assertEqual(priority_tier(20, "критическое"), "critical")
        self.assertEqual(priority_tier(40, "слабое"), "high")
        self.assertEqual(priority_tier(55, "среднее"), "medium")
        self.assertEqual(priority_tier(80, "сильное"), "minor")

    def test_merge_deficits_deduplicates_section(self):
        ctx1 = TaskContext(
            task_number=13,
            success_rate=30,
            classification="критическое",
            topic="Логарифмические уравнения",
            section="Алгебра",
            subsection="Логарифмы",
            skill_name="решение логарифмических уравнений",
            grade_range=[10, 11],
            exam_part=1,
        )
        ctx2 = TaskContext(
            task_number=15,
            success_rate=25,
            classification="критическое",
            topic="Логарифмические неравенства",
            section="Алгебра",
            subsection="Логарифмы",
            skill_name="решение логарифмических неравенств",
            grade_range=[10, 11],
            exam_part=1,
        )
        topic_graph = {
            ctx1.topic: {"topic": ctx1.topic, "section": "Алгебра", "prerequisites": ["Логарифмы", "Показательная функция"], "tasks": [13], "avg_success": 30},
            ctx2.topic: {"topic": ctx2.topic, "section": "Алгебра", "prerequisites": ["Логарифмы"], "tasks": [15], "avg_success": 25},
        }
        raw = [
            build_intelligent_deficit_cause(
                ctx1,
                subject_name="Математика профильная",
                exam_type="ege",
                topic_graph=topic_graph,
                task_success_map={13: 30, 15: 25},
            ),
            build_intelligent_deficit_cause(
                ctx2,
                subject_name="Математика профильная",
                exam_type="ege",
                topic_graph=topic_graph,
                task_success_map={13: 30, 15: 25},
            ),
        ]
        merged = merge_deficits_by_section(raw)
        self.assertGreaterEqual(len(merged), 1)
        self.assertIn(13, merged[0]["task_numbers"])
        self.assertIn(15, merged[0]["task_numbers"])
