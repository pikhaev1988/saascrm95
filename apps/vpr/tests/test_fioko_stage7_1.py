"""Stage 7.1 methodology hardening tests."""

from django.test import SimpleTestCase

from apps.vpr.comprehensive_analysis.groups import VprParticipantGroupAnalyzer
from apps.vpr.fioko_2026 import build_fioko_2026_layer
from apps.vpr.fioko_2026.sample import group_sample_flags, resolve_official_mark_boundaries
from apps.vpr.tests.fioko_fixtures import make_analytics, make_student, make_task


class Stage71GroupSampleTests(SimpleTestCase):
    def test_n3_limited(self):
        flags = group_sample_flags(3)
        self.assertEqual(flags["sample_status"], "LIMITED_SAMPLE")
        self.assertFalse(flags["informative"])

    def test_n9_limited(self):
        flags = group_sample_flags(9)
        self.assertEqual(flags["sample_status"], "LIMITED_SAMPLE")
        self.assertFalse(flags["informative"])

    def test_n10_informative(self):
        flags = group_sample_flags(10)
        self.assertEqual(flags["sample_status"], "INFORMATIVE")
        self.assertTrue(flags["informative"])

    def test_system_high_group_n3(self):
        # 3 high (>=80%), rest risk
        students = [
            make_student("1", primary=20, mark_vpr=5, completion=90),
            make_student("2", primary=19, mark_vpr=5, completion=85),
            make_student("3", primary=18, mark_vpr=4, completion=82),
        ] + [
            make_student(str(i), primary=5, mark_vpr=2, completion=30) for i in range(4, 15)
        ]
        analytics = make_analytics(students=students, n=len(students))
        # force completion on analytics summary max
        analytics.summary.max_primary_score = 25
        groups = VprParticipantGroupAnalyzer().analyze(analytics)
        high = groups.groups["high"]
        self.assertEqual(high.count, 3)
        self.assertEqual(high.sample_status, "LIMITED_SAMPLE")
        self.assertFalse(high.informative)


class Stage71PeaksTests(SimpleTestCase):
    def test_general_peak_not_objectivity_marker(self):
        # many students at score 14 — general peak; no official boundaries
        students = []
        for i in range(20):
            primary = 14 if i < 8 else (10 + (i % 5))
            students.append(make_student(str(i), primary=float(primary), mark_vpr=3 + (i % 3)))
        analytics = make_analytics(students=students, n=20)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        d = layer.distribution
        self.assertTrue(d.general_peak.is_peak)
        self.assertFalse(d.possible_objectivity_marker)
        self.assertEqual(d.boundary_peak_status, "NOT_AVAILABLE")
        self.assertEqual(d.boundary_source, "NOT_AVAILABLE")

    def test_boundaries_absent_not_available(self):
        analytics = make_analytics(n=15)
        layer = build_fioko_2026_layer(analytics, enrich_catalog=False)
        self.assertEqual(layer.distribution.boundary_peak_status, "NOT_AVAILABLE")
        self.assertFalse(layer.distribution.possible_objectivity_marker)
        self.assertTrue(
            all(f.status == "NOT_AVAILABLE" for f in layer.distribution.boundary_peak_flags)
        )

    def test_boundary_peak_with_official_scale(self):
        students = []
        # pile on boundary 12 (3->4)
        for i in range(25):
            primary = 12.0 if i < 10 else float(8 + (i % 7))
            mark = 4 if primary >= 12 else (3 if primary >= 7 else 2)
            students.append(make_student(str(i), primary=primary, mark_vpr=mark))
        analytics = make_analytics(students=students, n=25)

        class _Proto:
            extra = {"mark_boundaries": {"2->3": 7, "3->4": 12, "4->5": 18}}

        layer = build_fioko_2026_layer(analytics, protocol=_Proto(), enrich_catalog=False)
        d = layer.distribution
        self.assertEqual(d.boundary_source, "official")
        flagged = [f for f in d.boundary_peak_flags if f.status == "POSSIBLE_MARKER"]
        self.assertTrue(flagged)
        self.assertTrue(d.possible_objectivity_marker)
        self.assertEqual(d.boundary_peak_status, "HAS_MARKER")

    def test_resolve_official_none_without_meta(self):
        self.assertIsNone(resolve_official_mark_boundaries(subject="Математика", parallel=5))


class Stage71SystemVsFiokoTests(SimpleTestCase):
    def test_system_notes_present(self):
        layer = build_fioko_2026_layer(make_analytics(), enrich_catalog=False)
        blob = " ".join(layer.system_analytics_notes).lower()
        self.assertIn("system_analytics", blob)
        self.assertIn("80/50", blob)

    def test_report_wording_separates_system(self):
        from types import SimpleNamespace

        from apps.vpr.comprehensive_analysis.groups import VprParticipantGroupAnalyzer
        from apps.vpr.comprehensive_analysis.schemas import VprObjectivityProfile
        from apps.vpr.expert_analysis.fioko_report import _section2_individuals, _section8_group_tasks

        analytics = make_analytics(n=20)
        groups = VprParticipantGroupAnalyzer().analyze(analytics)
        analysis = SimpleNamespace(
            participant_groups=groups,
            analytics=analytics,
            objectivity=VprObjectivityProfile(),
            summary=analytics.summary,
            task_rows=[],
            subject=analytics.subject,
            parallel=analytics.parallel,
            academic_year=analytics.academic_year,
            organization_name="ОО",
        )
        expert = SimpleNamespace(
            profile_label="",
            profile_code="",
            profile_explanation="",
            tasks_analysis=[],
            topics_analysis=[],
            structure_analysis=[],
            patterns_analysis=[],
        )
        insights, cycle, *_ = _section2_individuals(analysis, expert)
        text = " ".join(cycle.interpretation).lower()
        self.assertIn("внутренн", text)
        self.assertNotIn("в логике рекомендаций фиоко: выделены группа риска", text)
        self.assertTrue(any(g.source_kind == "SYSTEM_ANALYTICS" for g in insights))

        class P:
            student_results = type(
                "QS",
                (),
                {"prefetch_related": lambda *a, **k: type("E", (), {"all": lambda self: []})()},
            )()

        _, cycle8 = _section8_group_tasks(analysis, P())
        text8 = " ".join(cycle8.interpretation).lower()
        self.assertNotIn("проведено в логике фиоко", text8)
        self.assertIn("внутренн", text8)


class Stage71MetricContractTests(SimpleTestCase):
    def test_full_partial_zero_untouched(self):
        tasks = [
            make_task("1", completion=55, max_score=2, full=0, partial=11, zero=9, difficulty="Базовый"),
        ]
        layer = build_fioko_2026_layer(make_analytics(tasks=tasks), enrich_catalog=False)
        t = layer.tasks[0]
        self.assertEqual(t.full_score_rate, 0.0)
        self.assertEqual(t.completion_percent, 55)
        self.assertNotEqual(t.completion_percent, t.full_score_rate)
