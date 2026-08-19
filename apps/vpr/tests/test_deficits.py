from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.vpr.analytics import VprAnalyticsEngine
from apps.vpr.deficits import VprDeficitEngine, clear_thresholds_cache, load_deficit_thresholds
from apps.vpr.deficits.config import DeficitThresholds, MasteryLevel
from apps.vpr.models import VprProtocol
from apps.vpr.services.catalog_import import import_catalog_file
from apps.vpr.services.import_service import VprImportService
from organizations.models import District, Ministry, School

User = get_user_model()
PROTOCOL_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "Ф1_Индивидуальные_результаты.xlsx"
CATALOG_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "vpr_task_catalog_sample.json"
ALT_PROTOCOLS = [
    Path(__file__).resolve().parents[1] / "fixtures" / "vpr_f1_sample.xlsx",
    Path(__file__).resolve().parents[1] / "fixtures" / "last_one_for_isa.xlsx",
    Path(__file__).resolve().parents[1] / "fixtures" / "2849657.xlsx",
]


class VprDeficitClassificationTests(TestCase):
    def tearDown(self):
        clear_thresholds_cache()

    def test_mastery_levels_from_config(self):
        thresholds = load_deficit_thresholds()
        cases = [
            (100, "high"),
            (90, "high"),
            (89.9, "sufficient"),
            (75, "sufficient"),
            (74.9, "acceptable"),
            (60, "acceptable"),
            (59.9, "problem"),
            (40, "problem"),
            (39.9, "critical"),
            (0, "critical"),
            (None, "critical"),
        ]
        for value, expected in cases:
            level = thresholds.classify(value)
            self.assertEqual(level.code, expected, msg=f"value={value}")

    def test_priority_mapping(self):
        thresholds = load_deficit_thresholds()
        self.assertEqual(thresholds.priority_for("critical"), "critical")
        self.assertEqual(thresholds.priority_for("problem"), "high")
        self.assertEqual(thresholds.priority_for("acceptable"), "medium")
        self.assertEqual(thresholds.priority_for("sufficient"), "low")
        self.assertEqual(thresholds.priority_for("high"), "low")

    @override_settings(
        VPR_DEFICIT_THRESHOLDS={
            "mastery_levels": [
                {"code": "high", "label": "High", "min_percent": 50, "max_percent": 100},
                {"code": "critical", "label": "Critical", "min_percent": 0, "max_percent": 49.9999},
            ],
            "priority_by_level": {"high": "low", "critical": "critical"},
            "risk_by_level": {"high": "low", "critical": "critical"},
            "problem_levels": ["critical"],
            "critical_levels": ["critical"],
        }
    )
    def test_thresholds_override_via_settings(self):
        clear_thresholds_cache()
        thresholds = load_deficit_thresholds()
        self.assertEqual(thresholds.classify(50).code, "high")
        self.assertEqual(thresholds.classify(49).code, "critical")


class VprDeficitEngineTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Deficit Ministry")
        district = District.objects.create(ministry=ministry, code="df20", name="Deficit District")
        self.school = School.objects.create(
            district=district,
            code="vpr-df-school",
            name='МБОУ «СОШ №1 г.Урус-Мартан»',
        )
        self.user = User.objects.create_user(
            username="vpr_df_user",
            password="pass12345",
            role="school",
            school=self.school,
        )
        import_catalog_file(CATALOG_FIXTURE)
        self.import_service = VprImportService()
        self.analytics_engine = VprAnalyticsEngine()
        self.deficit_engine = VprDeficitEngine()

    def tearDown(self):
        clear_thresholds_cache()

    def _import_protocol(self, fixture: Path, suffix: str) -> VprProtocol:
        uploaded = SimpleUploadedFile(
            f"f1_{suffix}.xlsx",
            fixture.read_bytes(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        upload = self.import_service.create_upload(
            user=self.user,
            uploaded_file=uploaded,
            school=self.school,
        )
        self.import_service.validate_and_preview(upload)
        self.import_service.confirm_import(upload)
        upload.refresh_from_db()
        return upload.protocol

    def test_structure_and_task_deficits(self):
        protocol = self._import_protocol(PROTOCOL_FIXTURE, "tasks")
        analytics = self.analytics_engine.analyze(protocol)
        deficits = self.deficit_engine.analyze(analytics)

        payload = deficits.to_dict()
        self.assertEqual(set(payload.keys()), {"protocol_id", "tasks", "topics", "skills", "students", "summary"})
        self.assertEqual(payload["protocol_id"], protocol.pk)
        self.assertEqual(len(deficits.tasks), len(analytics.tasks))

        for task in deficits.tasks:
            self.assertIn(task.mastery_level, {"high", "sufficient", "acceptable", "problem", "critical"})
            self.assertIn(task.priority, {"Critical", "High", "Medium", "Low"})
            self.assertIn(task.status, {"ok", "problem_zone", "critical_deficit"})
            if task.completion_percent is not None:
                if task.completion_percent < 40:
                    self.assertEqual(task.mastery_level, "critical")
                    self.assertEqual(task.priority, "Critical")
                    self.assertEqual(task.status, "critical_deficit")
                elif task.completion_percent < 60:
                    self.assertEqual(task.mastery_level, "problem")
                    self.assertEqual(task.priority, "High")
                    self.assertEqual(task.status, "problem_zone")

            # согласованность с аналитикой
            src = next(t for t in analytics.tasks if t.task_code == task.task_code)
            self.assertEqual(task.completion_percent, src.completion_percent)
            self.assertEqual(task.topic, src.topic)
            self.assertEqual(task.program_section, src.program_section)
            self.assertEqual(task.checked_skill, src.checked_skill)
            self.assertEqual(task.difficulty, src.difficulty)

    def test_topics_and_skills(self):
        protocol = self._import_protocol(PROTOCOL_FIXTURE, "topics")
        analytics = self.analytics_engine.analyze(protocol)
        deficits = self.deficit_engine.analyze(analytics)

        self.assertEqual(len(deficits.topics), len(analytics.topics))
        self.assertEqual(len(deficits.skills), len(analytics.skills))

        by_task = {t.task_code: t for t in deficits.tasks}
        for topic in deficits.topics:
            self.assertGreaterEqual(topic.tasks_count, 1)
            expected_critical = sum(
                1
                for code in topic.task_codes
                if by_task[code].mastery_level == "critical"
            )
            self.assertEqual(topic.critical_tasks_count, expected_critical)
            self.assertIn(topic.risk, {"Critical", "High", "Medium", "Low"})
            self.assertIn(topic.priority, {"Critical", "High", "Medium", "Low"})

        for skill in deficits.skills:
            self.assertGreaterEqual(skill.tasks_count, 1)
            self.assertIn(skill.risk, {"Critical", "High", "Medium", "Low"})

    def test_students(self):
        protocol = self._import_protocol(PROTOCOL_FIXTURE, "students")
        analytics = self.analytics_engine.analyze(protocol)
        deficits = self.deficit_engine.analyze(analytics, protocol=protocol)

        self.assertEqual(len(deficits.students), len(analytics.students))
        self.assertEqual(len(deficits.students), 89)

        for student in deficits.students:
            self.assertIn(student.mastery_level, {"high", "sufficient", "acceptable", "problem", "critical"})
            self.assertIn(student.priority, {"Critical", "High", "Medium", "Low"})
            self.assertGreaterEqual(student.unfinished_tasks_count, 0)
            self.assertGreaterEqual(student.critical_tasks_count, 0)
            self.assertGreaterEqual(student.problem_tasks_count, student.critical_tasks_count)
            self.assertIsInstance(student.problem_topics, list)
            self.assertIsInstance(student.problem_skills, list)

        # хотя бы у части учеников есть незавершённые/критические задания
        self.assertTrue(any(s.unfinished_tasks_count > 0 for s in deficits.students))
        self.assertTrue(any(s.critical_tasks_count > 0 for s in deficits.students))

    def test_summary_counts(self):
        protocol = self._import_protocol(PROTOCOL_FIXTURE, "sum")
        analytics = self.analytics_engine.analyze(protocol)
        deficits = self.deficit_engine.analyze(analytics)

        summary = deficits.summary
        self.assertEqual(summary.tasks_total, len(deficits.tasks))
        self.assertEqual(
            summary.tasks_critical,
            sum(1 for t in deficits.tasks if t.mastery_level == "critical"),
        )
        self.assertEqual(
            summary.tasks_problem,
            sum(1 for t in deficits.tasks if t.mastery_level in {"problem", "critical"}),
        )
        self.assertGreaterEqual(summary.critical_priority_count, 0)
        self.assertGreaterEqual(summary.high_priority_count, 0)

    def test_accepts_dict_payload(self):
        protocol = self._import_protocol(PROTOCOL_FIXTURE, "dict")
        analytics = self.analytics_engine.analyze(protocol)
        deficits = self.deficit_engine.analyze(analytics.to_dict(), protocol=protocol)
        self.assertEqual(len(deficits.tasks), len(analytics.tasks))
        self.assertEqual(len(deficits.students), len(analytics.students))

    def test_custom_thresholds_injected(self):
        protocol = self._import_protocol(PROTOCOL_FIXTURE, "custom")
        analytics = self.analytics_engine.analyze(protocol)
        custom = DeficitThresholds(
            levels=(
                MasteryLevel("ok", "OK", 50, 100),
                MasteryLevel("bad", "Bad", 0, 49.9999),
            ),
            priority_by_level={"ok": "low", "bad": "critical"},
            risk_by_level={"ok": "low", "bad": "critical"},
            problem_levels=("bad",),
            critical_levels=("bad",),
        )
        engine = VprDeficitEngine(thresholds=custom)
        deficits = engine.analyze(analytics)
        for task in deficits.tasks:
            if task.completion_percent is not None and task.completion_percent < 50:
                self.assertEqual(task.mastery_level, "bad")
                self.assertEqual(task.priority, "Critical")

    def test_second_protocol_if_available(self):
        protocol = None
        for idx, fixture in enumerate(ALT_PROTOCOLS):
            if not fixture.exists():
                continue
            try:
                protocol = self._import_protocol(fixture, f"alt{idx}")
                break
            except Exception:
                continue
        if protocol is None:
            self.skipTest("no alternative F1 protocol fixture available")

        analytics = self.analytics_engine.analyze(protocol)
        deficits = self.deficit_engine.analyze(analytics, protocol=protocol)
        self.assertEqual(len(deficits.tasks), len(analytics.tasks))
        self.assertEqual(len(deficits.students), len(analytics.students))
        self.assertGreater(deficits.summary.tasks_total, 0)
        for task in deficits.tasks:
            self.assertIn(task.mastery_level, {"high", "sufficient", "acceptable", "problem", "critical"})
