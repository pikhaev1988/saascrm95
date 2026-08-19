"""Stage 8.1 — deficit evidence gate regression tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from apps.vpr.expert_analysis.fioko_report import (
    DeficitInsight,
    _insufficient_deficit_insight,
    _section9_deficits,
    _section14_methodical,
    _section15_plan,
)


class _Expert:
    deficits_analysis = [
        "Образовательные дефициты по предмету читаются в логике профиля "
        "«сбалансированная подготовка»: важны тип дефицита (локальный).",
        "Дефициты ближе к локальным: точечные потери не складываются "
        "в межраздельную системную проблему.",
    ]
    causes_analysis = []
    cause_chains = []
    cognitive_code = "balanced"


class Stage81DeficitEvidenceTests(TestCase):
    def test_deficit_with_linked_tasks_established(self):
        analysis = SimpleNamespace(
            deficits=SimpleNamespace(
                topics=[
                    SimpleNamespace(
                        topic="Тема А",
                        avg_completion_percent=28.0,
                        priority="High",
                        task_codes=["1", "2"],
                    )
                ],
                skills=[],
            ),
            topic_rows=[],
            skill_rows=[],
            deficit_summary=None,
            fioko_2026=SimpleNamespace(catalog_mapping_status="COMPLETE"),
        )
        items, _cycle = _section9_deficits(analysis, _Expert())
        self.assertTrue(items)
        self.assertEqual(items[0].evidence_status, "ESTABLISHED")
        self.assertTrue(items[0].linked_tasks)
        self.assertIn("Дефицит", items[0].impact_results)

    def test_deficit_without_evidence_insufficient(self):
        analysis = SimpleNamespace(
            deficits=SimpleNamespace(topics=[], skills=[]),
            topic_rows=[],
            skill_rows=[],
            deficit_summary=None,
            fioko_2026=SimpleNamespace(catalog_mapping_status="PARTIAL"),
        )
        items, cycle = _section9_deficits(analysis, _Expert())
        self.assertTrue(items)
        self.assertTrue(all(d.evidence_status == "INSUFFICIENT_DATA" for d in items))
        self.assertTrue(all("Недостаточно данных" in d.impact_results for d in items))
        # Expert narrative must not become categorical deficit items
        joined = " ".join(d.impact_results for d in items)
        self.assertNotIn("сбалансированная подготовка", joined)

    def test_partial_catalog_missing_mapping_no_categorical(self):
        analysis = SimpleNamespace(
            deficits=SimpleNamespace(
                topics=[
                    SimpleNamespace(
                        topic="Тема без связи",
                        avg_completion_percent=22.0,
                        priority="High",
                        task_codes=[],
                    )
                ],
                skills=[],
            ),
            topic_rows=[],
            skill_rows=[],
            deficit_summary=None,
            fioko_2026=SimpleNamespace(catalog_mapping_status="PARTIAL"),
        )
        items, _ = _section9_deficits(analysis, _Expert())
        self.assertEqual(items[0].evidence_status, "INSUFFICIENT_DATA")
        self.assertIn("Недостаточно данных", items[0].impact_results)
        self.assertNotIn("существенно снижает", items[0].impact_results)

    def test_insufficient_neutral_wording(self):
        d = _insufficient_deficit_insight(reason="unit", catalog_status="PARTIAL")
        self.assertEqual(d.evidence_status, "INSUFFICIENT_DATA")
        self.assertIn("Недостаточно данных", d.impact_results)
        self.assertIn("INSUFFICIENT_DATA", d.evidence)

    def test_insufficient_no_categorical_management(self):
        report = SimpleNamespace(
            deficit_items=[
                _insufficient_deficit_insight(reason="unit", catalog_status="PARTIAL")
            ],
            planned_results=[],
            individual_groups=[],
            objectivity_rows=[],
            objectivity_risk="низкий",
            attendance_control=None,
            journal_equal_share=None,
        )
        recs, _ = _section14_methodical(report, None, _Expert(), "Литература")
        blob = " ".join(recs).lower()
        self.assertIn("дополнительную диагностику", blob)
        self.assertNotIn("устранить выявленный дефицит", blob)
        plan = _section15_plan(report)
        mon = [r for r in plan if "INSUFFICIENT" in (r.action + r.problem + r.kpi)]
        self.assertTrue(mon)
        self.assertFalse(
            any("Мониторинг устранения образовательных дефицитов" == r.action for r in plan)
        )

    def test_html_docx_same_status_fields(self):
        # Structural: DeficitInsight exposes evidence_status used by HTML/DOCX
        d = DeficitInsight(
            name="X",
            kind="тема",
            priority="High",
            average_percent=30.0,
            impact_results="Дефицит «X» существенно снижает…",
            impact_quality="",
            impact_program="",
            evidence="evidence_status=ESTABLISHED; linked_tasks=1",
            linked_tasks=["1"],
            evidence_status="ESTABLISHED",
        )
        self.assertEqual(d.evidence_status, "ESTABLISHED")
        d2 = _insufficient_deficit_insight(reason="t")
        self.assertEqual(d2.evidence_status, "INSUFFICIENT_DATA")
