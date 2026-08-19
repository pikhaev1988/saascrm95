"""
Baseline-тесты VPR Analytics (этап 3).

Проверяют зафиксированные на этапе 2 значения для production-протоколов.
Если протокол отсутствует в локальной БД — тест пропускается.
"""

from __future__ import annotations

from django.test import TestCase

from apps.vpr.analytics import VprAnalyticsEngine
from apps.vpr.comprehensive_analysis.groups import VprParticipantGroupAnalyzer
from apps.vpr.comprehensive_analysis.objectivity import VprObjectivityAnalyzer
from apps.vpr.expert_analysis.profiles import PROFILE_LABELS
from apps.vpr.models import VprProtocol


class VprBaselineBiologyProtocol11Tests(TestCase):
    PROTOCOL_ID = 11

    def setUp(self):
        self.protocol = VprProtocol.objects.filter(pk=self.PROTOCOL_ID).first()
        if self.protocol is None:
            self.skipTest(f"VprProtocol id={self.PROTOCOL_ID} отсутствует в БД")
        self.analytics = VprAnalyticsEngine().analyze(self.protocol)

    def test_summary_baseline(self):
        s = self.analytics.summary
        self.assertEqual(s.participants_count, 49)
        self.assertEqual(s.max_primary_score, 43)
        self.assertAlmostEqual(float(s.avg_primary_score or 0), 20.12, places=1)

    def test_marks_baseline(self):
        marks = self.analytics.marks.vpr or {}
        self.assertEqual(int(marks.get("2", 0)), 6)
        self.assertEqual(int(marks.get("3", 0)), 28)
        self.assertEqual(int(marks.get("4", 0)), 13)
        self.assertEqual(int(marks.get("5", 0)), 2)

    def test_groups_baseline(self):
        groups = VprParticipantGroupAnalyzer().analyze(self.analytics)
        self.assertEqual(groups.groups["high"].count, 2)
        self.assertEqual(groups.groups["medium"].count, 14)
        self.assertEqual(groups.groups["risk"].count, 33)
        self.assertEqual(
            groups.groups["high"].count + groups.groups["medium"].count + groups.groups["risk"].count,
            49,
        )

    def test_objectivity_baseline(self):
        obj = VprObjectivityAnalyzer().compute(self.analytics)
        self.assertEqual(obj.equal_count, 33)
        self.assertEqual(obj.lower_count, 16)
        self.assertEqual(obj.higher_count, 0)
        self.assertEqual(obj.compared_count, 49)

    def test_tasks_counts(self):
        tasks = list(self.analytics.tasks or [])
        self.assertEqual(len(tasks), 29)
        multi = [t for t in tasks if int(t.max_score or 0) > 1]
        self.assertEqual(len(multi), 13)

    def test_task3_multi_score_metrics(self):
        task = next((t for t in self.analytics.tasks if str(t.task_code) == "3"), None)
        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual(int(task.max_score), 2)
        self.assertEqual(task.full_score_count or task.full_count, 0)
        self.assertEqual(task.partial_score_count or task.partial_count, 25)
        self.assertEqual(task.zero_score_count or task.zero_count, 24)
        self.assertAlmostEqual(float(task.completion_percent or 0), 25.5, places=0)
        self.assertEqual(
            (task.full_score_count or task.full_count)
            + (task.partial_score_count or task.partial_count)
            + (task.zero_score_count or task.zero_count),
            task.total_students or task.answers_count,
        )

    def test_profile_check_report(self):
        """Фактический профиль protocol 11 через expert engine — зафиксировать, не чинить."""
        from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
        from apps.vpr.expert_analysis.engine import build_expert_analysis

        analysis = VprComprehensiveAnalysisEngine().analyze(self.protocol)
        expert = build_expert_analysis(analysis, protocol=self.protocol)
        code = getattr(expert, "profile_code", None) or ""
        label = getattr(expert, "profile_label", None) or ""
        stage2_code = "elevated_risk"
        stage2_label = "профиль повышенного риска"
        print(
            "PROFILE CHECK Biology id=11:",
            f"code={code!r}",
            f"label={label!r}",
            f"stage2_expected={stage2_code!r}/{stage2_label!r}",
            f"match={code == stage2_code or label == stage2_label}",
        )
        if code:
            self.assertIn(code, PROFILE_LABELS)
        if label and code in PROFILE_LABELS:
            self.assertEqual(label, PROFILE_LABELS[code])


class VprBaselineEnglishProtocol6Tests(TestCase):
    PROTOCOL_ID = 6

    def setUp(self):
        self.protocol = VprProtocol.objects.filter(pk=self.PROTOCOL_ID).first()
        if self.protocol is None:
            self.skipTest(f"VprProtocol id={self.PROTOCOL_ID} отсутствует в БД")
        self.analytics = VprAnalyticsEngine().analyze(self.protocol)

    def test_summary_baseline(self):
        s = self.analytics.summary
        self.assertEqual(s.participants_count, 29)
        self.assertEqual(s.max_primary_score, 25)
        self.assertAlmostEqual(float(s.avg_primary_score or 0), 14.17, places=1)

    def test_marks_baseline(self):
        marks = self.analytics.marks.vpr or {}
        self.assertEqual(int(marks.get("2", 0)), 3)
        self.assertEqual(int(marks.get("3", 0)), 17)
        self.assertEqual(int(marks.get("4", 0)), 7)
        self.assertEqual(int(marks.get("5", 0)), 2)

    def test_groups_baseline(self):
        groups = VprParticipantGroupAnalyzer().analyze(self.analytics)
        self.assertEqual(groups.groups["high"].count, 3)
        self.assertEqual(groups.groups["medium"].count, 16)
        self.assertEqual(groups.groups["risk"].count, 10)
        self.assertEqual(
            groups.groups["high"].count + groups.groups["medium"].count + groups.groups["risk"].count,
            29,
        )

    def test_objectivity_baseline(self):
        obj = VprObjectivityAnalyzer().compute(self.analytics)
        self.assertEqual(obj.equal_count, 17)
        self.assertEqual(obj.lower_count, 12)
        self.assertEqual(obj.higher_count, 0)
        self.assertEqual(obj.compared_count, 29)

    def test_tasks_count(self):
        self.assertEqual(len(list(self.analytics.tasks or [])), 5)
        multi = [t for t in self.analytics.tasks if int(t.max_score or 0) > 1]
        self.assertEqual(len(multi), 5)
