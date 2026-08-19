"""Тесты нормативного справочника apps/vpr/catalog/data."""

from __future__ import annotations

from django.test import TestCase

from apps.vpr.catalog.loader import discover_catalog_json_files, load_all_catalog_rows
from apps.vpr.catalog.quality import catalog_quality_check
from apps.vpr.models import VprTaskCatalogEntry
from apps.vpr.services.catalog_import import import_catalog_data_tree, import_catalog_path
from apps.vpr.services.catalog_lookup import lookup_task_catalog


class VprCatalogDataTreeTests(TestCase):
    def test_discover_seed_files(self):
        files = discover_catalog_json_files()
        names = {path.name for path in files}
        self.assertIn("2026.json", names)
        self.assertTrue(any("russian" in str(p).replace("\\", "/") for p in files))
        self.assertTrue(any("mathematics" in str(p).replace("\\", "/") for p in files))
        self.assertFalse(any(p.name.upper() == "MANIFEST.JSON" for p in files))

    def test_import_catalog_data_tree(self):
        rows = load_all_catalog_rows()
        self.assertGreaterEqual(len(rows), 20)

        record, stats = import_catalog_data_tree()
        self.assertEqual(record.status, "success")
        self.assertGreaterEqual(stats.created, 20)
        self.assertEqual(stats.errors, 0)

        self.assertTrue(
            VprTaskCatalogEntry.objects.filter(
                subject="Русский язык", parallel=4, academic_year=2026, task_code="1"
            ).exists()
        )
        self.assertTrue(
            VprTaskCatalogEntry.objects.filter(
                subject="Математика", parallel=4, academic_year=2026, task_code="1"
            ).exists()
        )

    def test_import_idempotent(self):
        import_catalog_path()
        first_count = VprTaskCatalogEntry.objects.count()
        record, stats = import_catalog_path()
        self.assertEqual(VprTaskCatalogEntry.objects.count(), first_count)
        self.assertEqual(stats.created, 0)
        self.assertGreaterEqual(stats.updated, first_count)
        self.assertEqual(record.status, "success")

    def test_lookup_after_seed_import(self):
        import_catalog_data_tree()

        info = lookup_task_catalog(
            subject="Русский язык",
            parallel=4,
            academic_year=2026,
            task_code="1",
        )
        self.assertIsNotNone(info)
        self.assertTrue(info.topic)
        self.assertTrue(info.program_section)
        self.assertTrue(info.checked_skill)
        self.assertTrue(info.difficulty)
        self.assertGreater(info.max_score, 0)

        info_sub = lookup_task_catalog(
            subject="Русский язык",
            parallel=4,
            academic_year=2026,
            task_code="9.1",
        )
        self.assertIsNotNone(info_sub)
        self.assertIn("9.1", info_sub.task_code)
        self.assertTrue(info_sub.topic)

        math_info = lookup_task_catalog(
            subject="Математика",
            parallel=4,
            academic_year=2026,
            task_code="5.1",
        )
        self.assertIsNotNone(math_info)
        self.assertTrue(math_info.checked_skill)

    def test_quality_check_clean_after_seed(self):
        import_catalog_data_tree()
        report = catalog_quality_check()
        self.assertFalse(report.has_issues, msg=f"issues={report.total_issues}")

    def test_seed_files_have_required_fields(self):
        from apps.vpr.services.catalog_import import load_rows_from_json

        required = ("topic", "checked_skill", "program_section", "difficulty")
        for path in discover_catalog_json_files():
            for row in load_rows_from_json(path):
                for field in required:
                    self.assertTrue(
                        str(row.get(field) or "").strip(),
                        msg=f"{path}: пустое поле {field} в задании {row.get('task_code')}",
                    )
                self.assertIsNotNone(row.get("max_score"))


class VprCatalogQualityNegativeTests(TestCase):
    def test_detects_missing_fields(self):
        VprTaskCatalogEntry.objects.create(
            academic_year=2026,
            subject="Русский язык",
            parallel=4,
            task_number=99,
            task_code="99",
            topic="",
            checked_skill="",
            program_section="",
            max_score=1,
        )
        report = catalog_quality_check()
        self.assertTrue(report.missing_topic)
        self.assertTrue(report.missing_skill)
        self.assertTrue(report.missing_section)
