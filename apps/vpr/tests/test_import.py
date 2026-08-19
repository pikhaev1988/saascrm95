from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from apps.vpr.models import VprProtocol, VprStudentResult, VprTask, VprTaskScore, VprUpload
from apps.vpr.parsers import VprExcelParser
from apps.vpr.services import VprImportService
from apps.vpr.validators import validate_vpr_file
from organizations.models import District, Ministry, School

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "Ф1_Индивидуальные_результаты.xlsx"
User = get_user_model()


class VprParserTests(TestCase):
    def test_parse_f1_fixture(self):
        self.assertTrue(FIXTURE.exists(), f"Missing fixture: {FIXTURE}")
        parsed = VprExcelParser().parse(FIXTURE)
        self.assertEqual(parsed.template_key, "f1_individual")
        self.assertEqual(parsed.subject, "Русский язык")
        self.assertEqual(parsed.parallel, 4)
        self.assertEqual(parsed.academic_year, 2026)
        self.assertEqual(parsed.participants_count, 89)
        self.assertEqual(parsed.tasks_count, 15)
        self.assertEqual(parsed.max_primary_score, 24)
        self.assertIsNotNone(parsed.exam_date)
        self.assertEqual(parsed.organization_code, "edu203389")
        self.assertIn("СОШ №1", parsed.organization_name)
        self.assertIn("Урус-Мартан", parsed.organization_name)
        first = parsed.students[0]
        self.assertEqual(first.participant_code, "40001")
        self.assertEqual(len(first.task_scores), 15)
        self.assertEqual(first.mark_vpr, 3)
        self.assertEqual(first.mark_journal, 3)

    def test_validate_f1_ok(self):
        parsed = validate_vpr_file(FIXTURE)
        self.assertEqual(parsed.participants_count, 89)


class VprImportServiceTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Test Ministry VPR")
        district = District.objects.create(ministry=ministry, code="t20", name="Test District VPR")
        self.school = School.objects.create(
            district=district,
            code="13435-vpr-test",
            name='МБОУ «СОШ №1 г.Урус-Мартан»',
        )
        self.user = User.objects.create_user(
            username="vpr_school_user",
            password="pass12345",
            role="school",
            school=self.school,
        )

    def test_full_import_pipeline(self):
        service = VprImportService()
        content = FIXTURE.read_bytes()
        uploaded = SimpleUploadedFile(
            "Ф1_Индивидуальные_результаты.xlsx",
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        upload = service.create_upload(user=self.user, uploaded_file=uploaded, school=self.school)
        parsed = service.validate_and_preview(upload)
        self.assertEqual(upload.status, "preview")
        self.assertEqual(parsed.participants_count, 89)

        service.confirm_import(upload)
        upload.refresh_from_db()
        self.assertEqual(upload.status, "imported")
        self.assertEqual(upload.students_imported, 89)
        self.assertEqual(upload.results_imported, 89)
        self.assertEqual(upload.tasks_imported, 15)
        self.assertEqual(upload.errors_count, 0)

        protocol = VprProtocol.objects.get(upload=upload)
        self.assertEqual(protocol.subject, "Русский язык")
        self.assertEqual(protocol.parallel, 4)
        self.assertEqual(VprTask.objects.filter(protocol=protocol).count(), 15)
        self.assertEqual(VprStudentResult.objects.filter(protocol=protocol).count(), 89)
        scores = VprTaskScore.objects.filter(result__protocol=protocol).count()
        self.assertEqual(scores, 89 * 15)


@override_settings(ALLOWED_HOSTS=["*"])
class VprUploadViewTests(TestCase):
    def setUp(self):
        ministry = Ministry.objects.create(name="Test Ministry VPR2")
        district = District.objects.create(ministry=ministry, code="t21", name="Test District VPR2")
        self.school = School.objects.create(
            district=district,
            code="vpr-view-school",
            name="VPR View School",
        )
        self.user = User.objects.create_user(
            username="vpr_view_user",
            password="pass12345",
            role="school",
            school=self.school,
        )
        self.client = Client()
        self.client.login(username="vpr_view_user", password="pass12345")

    def test_upload_preview_confirm_flow(self):
        with FIXTURE.open("rb") as fh:
            response = self.client.post(
                "/cabinet/vpr/upload/",
                {"file": fh},
                follow=False,
            )
        self.assertEqual(response.status_code, 302)
        upload = VprUpload.objects.latest("id")
        self.assertEqual(upload.status, "preview")
        self.assertIn(f"/cabinet/vpr/upload/{upload.id}/preview/", response["Location"])

        confirm = self.client.post(f"/cabinet/vpr/upload/{upload.id}/confirm/")
        self.assertEqual(confirm.status_code, 302)
        upload.refresh_from_db()
        self.assertEqual(upload.status, "imported")
        self.assertEqual(upload.students_imported, 89)
