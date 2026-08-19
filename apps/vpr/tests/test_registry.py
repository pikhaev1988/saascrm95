from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from apps.vpr.models import VprProtocol, VprStudentResult, VprUpload
from apps.vpr.services import VprImportService, build_registry
from organizations.models import District, Ministry, School

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "Ф1_Индивидуальные_результаты.xlsx"
User = get_user_model()


class VprRegistryTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Registry Ministry")
        self.district = District.objects.create(ministry=ministry, code="reg20", name="Registry District")
        self.school = School.objects.create(
            district=self.district,
            code="vpr-reg-school",
            name='МБОУ «СОШ №1 г.Урус-Мартан»',
        )
        self.user = User.objects.create_user(
            username="vpr_reg_user",
            password="pass12345",
            role="school",
            school=self.school,
        )
        self.service = VprImportService()
        self.client = Client()
        self.client.login(username="vpr_reg_user", password="pass12345")

    def _import_once(self, suffix: str = "a") -> VprUpload:
        content = FIXTURE.read_bytes()
        uploaded = SimpleUploadedFile(
            f"Ф1_{suffix}.xlsx",
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        upload = self.service.create_upload(
            user=self.user,
            uploaded_file=uploaded,
            school=self.school,
        )
        self.service.validate_and_preview(upload)
        self.service.confirm_import(upload)
        upload.refresh_from_db()
        return upload

    def test_multiple_imports_appear_in_registry(self):
        self._import_once("1")
        self._import_once("2")
        registry = build_registry(self.user, {})
        self.assertEqual(registry["total_count"], 2)
        response = self.client.get("/cabinet/vpr/protocols/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Русский язык")
        self.assertContains(response, "Протоколы ВПР")

    def test_filter_and_search(self):
        self._import_once("f")
        registry = build_registry(self.user, {"subject": "Русский", "year": "2026", "parallel": "4"})
        self.assertEqual(registry["total_count"], 1)
        registry_empty = build_registry(self.user, {"subject": "Математика"})
        self.assertEqual(registry_empty["total_count"], 0)
        registry_q = build_registry(self.user, {"q": "Урус"})
        self.assertEqual(registry_q["total_count"], 1)

    def test_protocol_detail_page(self):
        upload = self._import_once("d")
        protocol = upload.protocol
        response = self.client.get(f"/cabinet/vpr/protocols/{protocol.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Карточка протокола")
        self.assertContains(response, "40001")
        self.assertEqual(VprStudentResult.objects.filter(protocol=protocol).count(), 89)

    def test_delete_import(self):
        upload = self._import_once("del")
        protocol_id = upload.protocol.id
        response = self.client.post(f"/cabinet/vpr/uploads/{upload.id}/delete/")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(VprUpload.objects.filter(id=upload.id).exists())
        self.assertFalse(VprProtocol.objects.filter(id=protocol_id).exists())

    def test_reimport(self):
        upload = self._import_once("re")
        old_protocol_id = upload.protocol.id
        response = self.client.post(f"/cabinet/vpr/uploads/{upload.id}/reimport/")
        self.assertEqual(response.status_code, 302)
        upload.refresh_from_db()
        self.assertEqual(upload.status, "imported")
        self.assertEqual(upload.students_imported, 89)
        self.assertTrue(hasattr(upload, "protocol"))
        # протокол пересоздан
        self.assertNotEqual(upload.protocol.id, old_protocol_id)
        self.assertEqual(VprStudentResult.objects.filter(protocol=upload.protocol).count(), 89)

    def test_download_file(self):
        upload = self._import_once("dl")
        response = self.client.get(f"/cabinet/vpr/uploads/{upload.id}/file/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.get("Content-Disposition", ""))


@override_settings(ALLOWED_HOSTS=["*"])
class VprRegistryPaginationTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Page Ministry")
        district = District.objects.create(ministry=ministry, code="page20", name="Page District")
        self.school = School.objects.create(district=district, code="vpr-page", name="Page School")
        self.user = User.objects.create_user(
            username="vpr_page_user",
            password="pass12345",
            role="school",
            school=self.school,
        )

    def test_sort_by_year(self):
        # два протокола через сервис с одним файлом — оба year=2026
        service = VprImportService()
        for i in range(2):
            uploaded = SimpleUploadedFile(
                f"page_{i}.xlsx",
                FIXTURE.read_bytes(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            upload = service.create_upload(user=self.user, uploaded_file=uploaded, school=self.school)
            service.validate_and_preview(upload)
            service.confirm_import(upload)
        registry = build_registry(self.user, {"sort": "subject"})
        self.assertEqual(registry["total_count"], 2)
        self.assertEqual(registry["page_obj"].paginator.num_pages, 1)
