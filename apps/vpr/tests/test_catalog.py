from __future__ import annotations

import csv
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from openpyxl import Workbook

from apps.vpr.models import VprTaskCatalogEntry
from apps.vpr.services.catalog_import import import_catalog_file
from apps.vpr.services.catalog_lookup import lookup_task_catalog, parse_task_code
from apps.vpr.services.catalog_registry import build_catalog_list

User = get_user_model()
FIXTURE_JSON = Path(__file__).resolve().parents[1] / "fixtures" / "vpr_task_catalog_sample.json"


class VprCatalogLookupTests(TestCase):
    def setUp(self):
        import_catalog_file(FIXTURE_JSON)

    def test_parse_task_codes(self):
        self.assertEqual(parse_task_code("9.1"), (9, "1", "9.1"))
        self.assertEqual(parse_task_code("7"), (7, "", "7"))
        self.assertEqual(parse_task_code("4К1")[2], "4К1")

    def test_lookup_by_code(self):
        info = lookup_task_catalog(
            subject="Русский язык",
            parallel=4,
            academic_year=2026,
            task_code="7",
        )
        self.assertIsNotNone(info)
        self.assertEqual(info.topic, "Части речи")
        self.assertIn("грамматическ", info.checked_skill.lower())

        info_sub = lookup_task_catalog(
            subject="Русский язык",
            parallel=4,
            academic_year=2026,
            task_code="9.1",
        )
        self.assertIsNotNone(info_sub)
        self.assertEqual(info_sub.difficulty, "П")
        self.assertEqual(info_sub.program_section, "Развитие речи")


class VprCatalogImportFormatTests(TestCase):
    def test_import_json(self):
        record, stats = import_catalog_file(FIXTURE_JSON)
        self.assertEqual(stats.created, 4)
        self.assertEqual(VprTaskCatalogEntry.objects.count(), 4)
        self.assertEqual(record.status, "success")

    def test_import_csv(self, tmp_path=None):
        path = Path(self._temp_dir()) / "catalog.csv"
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                ["учебный год", "предмет", "класс", "код задания", "тема", "проверяемое умение", "максимальный балл"]
            )
            writer.writerow([2026, "Математика", 4, "3", "Числа", "Вычисление", 1])
        record, stats = import_catalog_file(path)
        self.assertEqual(stats.created, 1)
        self.assertTrue(VprTaskCatalogEntry.objects.filter(subject="Математика", task_code="3").exists())
        self.assertEqual(record.source_format, "csv")

    def test_import_excel(self):
        path = Path(self._temp_dir()) / "catalog.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(["year", "subject", "class", "task_code", "topic", "skill", "max_score", "difficulty"])
        ws.append([2026, "Окружающий мир", 4, "2", "Природа", "Наблюдение", 2, "Б"])
        wb.save(path)
        record, stats = import_catalog_file(path)
        self.assertEqual(stats.created, 1)
        entry = VprTaskCatalogEntry.objects.get(subject="Окружающий мир", task_code="2")
        self.assertEqual(entry.topic, "Природа")
        self.assertEqual(entry.checked_skill, "Наблюдение")
        self.assertEqual(record.source_format, "xlsx")

    def _temp_dir(self) -> str:
        import tempfile

        return tempfile.mkdtemp()


class VprCatalogCrudTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="vpr_catalog_admin",
            password="pass12345",
            role="district",
            is_staff=True,
        )
        self.client = Client()
        self.client.login(username="vpr_catalog_admin", password="pass12345")
        import_catalog_file(FIXTURE_JSON)

    def test_list_search_filter(self):
        response = self.client.get("/cabinet/vpr/catalog/", {"q": "Части", "year": "2026"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Русский язык")
        data = build_catalog_list({"subject": "Русский", "parallel": "4"})
        self.assertEqual(data["total_count"], 4)
        data_empty = build_catalog_list({"subject": "Химия"})
        self.assertEqual(data_empty["total_count"], 0)

    def test_create_edit_delete(self):
        create = self.client.post(
            "/cabinet/vpr/catalog/new/",
            {
                "academic_year": 2026,
                "subject": "Биология",
                "parallel": 5,
                "task_number": 1,
                "task_subnumber": "",
                "task_code": "1",
                "official_code": "",
                "max_score": 2,
                "checked_skill": "Умение X",
                "fgos_result": "",
                "program_section": "Раздел",
                "topic": "Тема Б",
                "topic_subsection": "",
                "difficulty": "Б",
                "task_type": "Тест",
                "short_description": "Описание",
                "normative_source": "Источник",
                "is_active": "on",
            },
        )
        self.assertEqual(create.status_code, 302)
        entry = VprTaskCatalogEntry.objects.get(subject="Биология", parallel=5)
        detail = self.client.get(f"/cabinet/vpr/catalog/{entry.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Тема Б")

        edit = self.client.post(
            f"/cabinet/vpr/catalog/{entry.id}/edit/",
            {
                "academic_year": 2026,
                "subject": "Биология",
                "parallel": 5,
                "task_number": 1,
                "task_subnumber": "",
                "task_code": "1",
                "official_code": "",
                "max_score": 3,
                "checked_skill": "Умение Y",
                "fgos_result": "",
                "program_section": "Раздел",
                "topic": "Тема обновлена",
                "topic_subsection": "",
                "difficulty": "П",
                "task_type": "Тест",
                "short_description": "Описание",
                "normative_source": "Источник",
                "is_active": "on",
            },
        )
        self.assertEqual(edit.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.topic, "Тема обновлена")
        self.assertEqual(entry.max_score, 3)

        delete = self.client.post(f"/cabinet/vpr/catalog/{entry.id}/delete/")
        self.assertEqual(delete.status_code, 302)
        self.assertFalse(VprTaskCatalogEntry.objects.filter(id=entry.id).exists())

    def test_web_import_json(self):
        with FIXTURE_JSON.open("rb") as fh:
            response = self.client.post("/cabinet/vpr/catalog/import/", {"file": fh})
        self.assertEqual(response.status_code, 302)
        # upsert — уже были 4, станут updated
        self.assertEqual(VprTaskCatalogEntry.objects.filter(subject="Русский язык").count(), 4)


@override_settings(ALLOWED_HOSTS=["*"])
class VprCatalogSchoolViewOnlyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="vpr_catalog_school",
            password="pass12345",
            role="school",
        )
        self.client = Client()
        self.client.login(username="vpr_catalog_school", password="pass12345")
        import_catalog_file(FIXTURE_JSON)

    def test_school_can_view_but_not_create(self):
        self.assertEqual(self.client.get("/cabinet/vpr/catalog/").status_code, 200)
        self.assertEqual(self.client.get("/cabinet/vpr/catalog/new/").status_code, 302)
