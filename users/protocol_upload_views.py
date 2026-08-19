import os
import tempfile

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from exams.models import Exam, ExamType
from organizations.models import District, School
from uploads.models import UploadSession
from uploads.parsers import parse_ege, parse_oge
from uploads.sample_protocols import build_ege_sample_xlsx, build_oge_sample_xlsx
from uploads.services import (
    delete_district_exam_results,
    delete_school_exam_results,
    get_district_exams_with_results,
    get_school_exams_with_results,
    link_upload_exams,
    revert_district_upload,
    revert_school_upload,
)
from users.web_views import _resolve_school_id_for_user


class SchoolProtocolUploadView(LoginRequiredMixin, TemplateView):
    exam_type = ExamType.EGE
    template_name = "users/protocol_upload.html"
    upload_history_limit = 20

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("no-role")
        self.school = School.objects.get(pk=school_id)
        return super().dispatch(request, *args, **kwargs)

    def get_redirect_name(self):
        return "cabinet-upload-ege" if self.exam_type == ExamType.EGE else "cabinet-upload-oge"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_role"] = self.request.user.role
        context["upload_scope"] = "school"
        context["school"] = self.school
        context["district"] = None
        context["district_schools_count"] = 0
        context["exam_type"] = self.exam_type
        context["exam_type_label"] = "ЕГЭ" if self.exam_type == ExamType.EGE else "ОГЭ"
        context["sample_url_name"] = (
            "cabinet-upload-ege-sample" if self.exam_type == ExamType.EGE else "cabinet-upload-oge-sample"
        )
        context["revert_url_name"] = (
            "cabinet-upload-ege-revert" if self.exam_type == ExamType.EGE else "cabinet-upload-oge-revert"
        )
        context["delete_exam_url_name"] = (
            "cabinet-upload-ege-delete-exam"
            if self.exam_type == ExamType.EGE
            else "cabinet-upload-oge-delete-exam"
        )
        context["recent_uploads"] = (
            UploadSession.objects.filter(
                school=self.school,
                exam_type=self.exam_type,
            )
            .prefetch_related("exams")
            .order_by("-created_at")[: self.upload_history_limit]
        )
        context["loaded_exams"] = get_school_exams_with_results(self.school, self.exam_type)
        return context

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        redirect_name = self.get_redirect_name()
        if not file_obj:
            messages.error(request, "Выберите файл протокола.")
            return redirect(redirect_name)

        ext = os.path.splitext(file_obj.name)[1].lower()
        allowed = {".xlsx", ".xls", ".csv"} if self.exam_type == ExamType.OGE else {".xlsx", ".xls"}
        if ext not in allowed:
            formats = ", ".join(sorted(allowed))
            messages.error(request, f"Неподдерживаемый формат. Допустимые: {formats}.")
            return redirect(redirect_name)

        session = UploadSession.objects.create(
            uploaded_by=request.user,
            school=self.school,
            exam_type=self.exam_type,
            file=file_obj,
        )
        session.status = "processing"
        session.save(update_fields=["status"])

        school_codes = [self.school.code]
        tmp_path = None
        try:
            if hasattr(session.file, "path") and session.file.path:
                file_path = session.file.path
            else:
                suffix = ext or ".xlsx"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    for chunk in file_obj.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                file_path = tmp_path

            if self.exam_type == ExamType.EGE:
                exam_ids, stats = parse_ege(file_path, school_codes=school_codes)
            else:
                exam_ids, stats = parse_oge(file_path, school_codes=school_codes)

            link_upload_exams(session, exam_ids)
            session.status = "done"
            session.processed_at = timezone.now()
            session.error_message = ""
            session.results_imported = stats.results_imported
            session.exams_processed = stats.exams_processed
            session.save(
                update_fields=[
                    "status",
                    "processed_at",
                    "error_message",
                    "results_imported",
                    "exams_processed",
                ]
            )

            success_parts = [
                f"Загружено записей: {stats.results_imported}.",
                f"Обработано экзаменов: {stats.exams_processed}.",
            ]
            if stats.skipped_other_school:
                success_parts.append(
                    f"Пропущено строк других ОО: {stats.skipped_other_school}."
                )
            messages.success(request, " ".join(success_parts))
        except Exception as exc:
            session.status = "failed"
            session.error_message = str(exc)
            session.save(update_fields=["status", "error_message"])
            messages.error(request, f"Ошибка загрузки: {exc}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

        return redirect(redirect_name)


class SchoolUploadEgeProtocolsView(SchoolProtocolUploadView):
    exam_type = ExamType.EGE


class SchoolUploadOgeProtocolsView(SchoolProtocolUploadView):
    exam_type = ExamType.OGE


class DistrictProtocolUploadView(LoginRequiredMixin, TemplateView):
    exam_type = ExamType.EGE
    template_name = "users/protocol_upload.html"
    upload_history_limit = 20

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role != "district":
            return redirect("cabinet")
        if not request.user.district_id:
            return redirect("no-role")
        self.district = District.objects.get(pk=request.user.district_id)
        self.district_schools = list(
            School.objects.filter(district_id=self.district.id).only("id", "code", "name").order_by("name")
        )
        return super().dispatch(request, *args, **kwargs)

    def get_redirect_name(self):
        return (
            "cabinet-district-upload-ege"
            if self.exam_type == ExamType.EGE
            else "cabinet-district-upload-oge"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_role"] = self.request.user.role
        context["upload_scope"] = "district"
        context["school"] = None
        context["district"] = self.district
        context["district_schools_count"] = len(self.district_schools)
        context["exam_type"] = self.exam_type
        context["exam_type_label"] = "ЕГЭ" if self.exam_type == ExamType.EGE else "ОГЭ"
        context["sample_url_name"] = (
            "cabinet-district-upload-ege-sample"
            if self.exam_type == ExamType.EGE
            else "cabinet-district-upload-oge-sample"
        )
        context["revert_url_name"] = (
            "cabinet-district-upload-ege-revert"
            if self.exam_type == ExamType.EGE
            else "cabinet-district-upload-oge-revert"
        )
        context["delete_exam_url_name"] = (
            "cabinet-district-upload-ege-delete-exam"
            if self.exam_type == ExamType.EGE
            else "cabinet-district-upload-oge-delete-exam"
        )
        context["recent_uploads"] = (
            UploadSession.objects.filter(
                district=self.district,
                exam_type=self.exam_type,
            )
            .prefetch_related("exams")
            .order_by("-created_at")[: self.upload_history_limit]
        )
        context["loaded_exams"] = get_district_exams_with_results(self.district, self.exam_type)
        return context

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        redirect_name = self.get_redirect_name()
        if not file_obj:
            messages.error(request, "Выберите файл протокола.")
            return redirect(redirect_name)

        school_codes = [school.code for school in self.district_schools if school.code]
        if not school_codes:
            messages.error(request, "В районе нет привязанных школ. Загрузка невозможна.")
            return redirect(redirect_name)

        ext = os.path.splitext(file_obj.name)[1].lower()
        allowed = {".xlsx", ".xls", ".csv"} if self.exam_type == ExamType.OGE else {".xlsx", ".xls"}
        if ext not in allowed:
            formats = ", ".join(sorted(allowed))
            messages.error(request, f"Неподдерживаемый формат. Допустимые: {formats}.")
            return redirect(redirect_name)

        session = UploadSession.objects.create(
            uploaded_by=request.user,
            district=self.district,
            exam_type=self.exam_type,
            file=file_obj,
        )
        session.status = "processing"
        session.save(update_fields=["status"])

        tmp_path = None
        try:
            if hasattr(session.file, "path") and session.file.path:
                file_path = session.file.path
            else:
                suffix = ext or ".xlsx"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    for chunk in file_obj.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                file_path = tmp_path

            if self.exam_type == ExamType.EGE:
                exam_ids, stats = parse_ege(file_path, school_codes=school_codes)
            else:
                exam_ids, stats = parse_oge(file_path, school_codes=school_codes)

            link_upload_exams(session, exam_ids)
            session.status = "done"
            session.processed_at = timezone.now()
            session.error_message = ""
            session.results_imported = stats.results_imported
            session.exams_processed = stats.exams_processed
            session.save(
                update_fields=[
                    "status",
                    "processed_at",
                    "error_message",
                    "results_imported",
                    "exams_processed",
                ]
            )

            success_parts = [
                f"Загружено записей: {stats.results_imported}.",
                f"Обработано экзаменов: {stats.exams_processed}.",
            ]
            if stats.skipped_other_school:
                success_parts.append(
                    f"Пропущено строк ОО вне вашего района: {stats.skipped_other_school}."
                )
            if stats.skipped_unknown_school:
                success_parts.append(
                    f"Пропущено строк с неизвестным кодом ОО: {stats.skipped_unknown_school}."
                )
            messages.success(request, " ".join(success_parts))
        except Exception as exc:
            session.status = "failed"
            session.error_message = str(exc)
            session.save(update_fields=["status", "error_message"])
            messages.error(request, f"Ошибка загрузки: {exc}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

        return redirect(redirect_name)


class DistrictUploadEgeProtocolsView(DistrictProtocolUploadView):
    exam_type = ExamType.EGE


class DistrictUploadOgeProtocolsView(DistrictProtocolUploadView):
    exam_type = ExamType.OGE


class _SchoolCabinetMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("no-role")
        self.school = School.objects.get(pk=school_id)
        return super().dispatch(request, *args, **kwargs)


class _DistrictCabinetMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role != "district":
            return redirect("cabinet")
        if not request.user.district_id:
            return redirect("no-role")
        self.district = District.objects.get(pk=request.user.district_id)
        return super().dispatch(request, *args, **kwargs)


class SchoolProtocolUploadRevertView(_SchoolCabinetMixin, LoginRequiredMixin, View):
    def post(self, request, session_id):
        session = get_object_or_404(
            UploadSession,
            pk=session_id,
            school=self.school,
            uploaded_by=request.user,
        )
        redirect_name = (
            "cabinet-upload-ege" if session.exam_type == ExamType.EGE else "cabinet-upload-oge"
        )
        try:
            result = revert_school_upload(session)
            messages.success(
                request,
                (
                    f"Загрузка отменена: удалены результаты по {result['exams_affected']} "
                    f"экзаменам ({result['results_removed']} записей)."
                ),
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"Не удалось отменить загрузку: {exc}")
        return redirect(redirect_name)


class DistrictProtocolUploadRevertView(_DistrictCabinetMixin, LoginRequiredMixin, View):
    def post(self, request, session_id):
        session = get_object_or_404(
            UploadSession,
            pk=session_id,
            district=self.district,
            uploaded_by=request.user,
        )
        redirect_name = (
            "cabinet-district-upload-ege"
            if session.exam_type == ExamType.EGE
            else "cabinet-district-upload-oge"
        )
        try:
            result = revert_district_upload(session)
            messages.success(
                request,
                (
                    f"Загрузка отменена: удалены результаты школ района по {result['exams_affected']} "
                    f"экзаменам ({result['results_removed']} записей)."
                ),
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"Не удалось отменить загрузку: {exc}")
        return redirect(redirect_name)


class SchoolProtocolExamDeleteView(_SchoolCabinetMixin, LoginRequiredMixin, View):
    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
        redirect_name = (
            "cabinet-upload-ege" if exam.exam_type == ExamType.EGE else "cabinet-upload-oge"
        )
        try:
            result = delete_school_exam_results(self.school, exam)
            messages.success(
                request,
                (
                    f"Удалены результаты по экзамену «{exam.subject}» "
                    f"({exam.exam_date:%d.%m.%Y}): {result['results_removed']} записей."
                ),
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"Не удалось удалить результаты: {exc}")
        return redirect(redirect_name)


class DistrictProtocolExamDeleteView(_DistrictCabinetMixin, LoginRequiredMixin, View):
    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
        redirect_name = (
            "cabinet-district-upload-ege"
            if exam.exam_type == ExamType.EGE
            else "cabinet-district-upload-oge"
        )
        try:
            result = delete_district_exam_results(self.district, exam)
            messages.success(
                request,
                (
                    f"Удалены результаты школ района по экзамену «{exam.subject}» "
                    f"({exam.exam_date:%d.%m.%Y}): {result['results_removed']} записей."
                ),
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"Не удалось удалить результаты: {exc}")
        return redirect(redirect_name)


class SchoolProtocolSampleDownloadView(LoginRequiredMixin, View):
    exam_type = ExamType.EGE

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("no-role")
        self.school = School.objects.get(pk=school_id)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.exam_type == ExamType.EGE:
            content = build_ege_sample_xlsx(self.school.code)
            filename = "primer-protokola-ege.xlsx"
        else:
            content = build_oge_sample_xlsx(self.school.code)
            filename = "primer-protokola-oge.xlsx"

        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class SchoolDownloadEgeProtocolSampleView(SchoolProtocolSampleDownloadView):
    exam_type = ExamType.EGE


class SchoolDownloadOgeProtocolSampleView(SchoolProtocolSampleDownloadView):
    exam_type = ExamType.OGE


class DistrictProtocolSampleDownloadView(LoginRequiredMixin, View):
    exam_type = ExamType.EGE

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role != "district":
            return redirect("cabinet")
        if not request.user.district_id:
            return redirect("no-role")
        self.district = District.objects.get(pk=request.user.district_id)
        self.sample_school = (
            School.objects.filter(district_id=self.district.id).only("code").order_by("name").first()
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not self.sample_school:
            messages.error(request, "В районе нет школ для формирования примера.")
            redirect_name = (
                "cabinet-district-upload-ege"
                if self.exam_type == ExamType.EGE
                else "cabinet-district-upload-oge"
            )
            return redirect(redirect_name)

        if self.exam_type == ExamType.EGE:
            content = build_ege_sample_xlsx(self.sample_school.code)
            filename = "primer-protokola-ege-raion.xlsx"
        else:
            content = build_oge_sample_xlsx(self.sample_school.code)
            filename = "primer-protokola-oge-raion.xlsx"

        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class DistrictDownloadEgeProtocolSampleView(DistrictProtocolSampleDownloadView):
    exam_type = ExamType.EGE


class DistrictDownloadOgeProtocolSampleView(DistrictProtocolSampleDownloadView):
    exam_type = ExamType.OGE
