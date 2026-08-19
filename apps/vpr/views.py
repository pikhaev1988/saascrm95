"""Web-views модуля ВПР: загрузка → предпросмотр → импорт → результат."""

from __future__ import annotations

import logging
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, TemplateView, View

from apps.vpr.access import can_access_upload, scoped_uploads_qs, user_school
from apps.vpr.exceptions import VprImportError, VprValidationError
from apps.vpr.models import VprUpload, VprUploadStatus
from apps.vpr.services.import_service import VprImportService

logger = logging.getLogger(__name__)

VPR_SAMPLE_CANDIDATES = (
    Path(__file__).resolve().parent / "fixtures" / "vpr_f1_sample.xlsx",
    Path(__file__).resolve().parent / "fixtures" / "Ф1_Индивидуальные_результаты.xlsx",
)


def _sample_protocol_path() -> Path | None:
    for path in VPR_SAMPLE_CANDIDATES:
        if path.exists():
            return path
    return None


class VprSampleDownloadView(LoginRequiredMixin, View):
    """Скачать пример реального протокола Ф1 Индивидуальные результаты."""

    def get(self, request, *args, **kwargs):
        path = _sample_protocol_path()
        if not path:
            raise Http404("Пример протокола ВПР не найден.")
        return FileResponse(
            path.open("rb"),
            as_attachment=True,
            filename="Ф1_Индивидуальные_результаты_пример.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class VprUploadView(LoginRequiredMixin, TemplateView):
    template_name = "vpr/upload.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role not in {"school", "district"}:
            return redirect("cabinet")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = user_school(self.request.user)
        context["school"] = school
        context["user_role"] = self.request.user.role
        context["recent_uploads"] = scoped_uploads_qs(self.request.user).order_by("-created_at")[:20]
        return context

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        if not file_obj:
            messages.error(request, "Выберите файл протокола ВПР.")
            return redirect("vpr-upload")

        ext = (file_obj.name or "").rsplit(".", 1)
        if len(ext) < 2 or ext[-1].lower() not in {"xlsx", "xlsm"}:
            messages.error(request, "Поддерживаются только файлы Excel (.xlsx).")
            return redirect("vpr-upload")

        service = VprImportService()
        school = user_school(request.user)
        district = getattr(request.user, "district", None)
        upload = service.create_upload(
            user=request.user,
            uploaded_file=file_obj,
            school=school,
            district=district,
        )
        try:
            service.validate_and_preview(upload)
        except VprValidationError as exc:
            details = "; ".join(exc.details) if exc.details else ""
            messages.error(request, f"{exc.message}" + (f" {details}" if details else ""))
            return redirect("vpr-upload")
        except Exception as exc:  # noqa: BLE001
            logger.exception("VPR preview unexpected error")
            upload.mark_failed(str(exc))
            messages.error(request, f"Ошибка обработки файла: {exc}")
            return redirect("vpr-upload")

        messages.success(request, "Файл проверен. Проверьте данные перед импортом.")
        return redirect("vpr-preview", upload_id=upload.pk)


class VprPreviewView(LoginRequiredMixin, DetailView):
    template_name = "vpr/preview.html"
    model = VprUpload
    pk_url_kwarg = "upload_id"
    context_object_name = "upload"

    def dispatch(self, request, *args, **kwargs):
        upload = self.get_object()
        if not can_access_upload(request.user, upload):
            return redirect("vpr-upload")
        if upload.status == VprUploadStatus.IMPORTED:
            if hasattr(upload, "protocol"):
                return redirect("vpr-protocol-detail", protocol_id=upload.protocol.pk)
            return redirect("vpr-registry")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["preview"] = self.object.preview_payload or {}
        context["user_role"] = self.request.user.role
        return context


class VprConfirmImportView(LoginRequiredMixin, View):
    def post(self, request, upload_id: int, *args, **kwargs):
        upload = get_object_or_404(VprUpload, pk=upload_id)
        if not can_access_upload(request.user, upload):
            return redirect("vpr-upload")
        if upload.status == VprUploadStatus.IMPORTED:
            if hasattr(upload, "protocol"):
                return redirect("vpr-protocol-detail", protocol_id=upload.protocol.pk)
            return redirect("vpr-registry")

        service = VprImportService()
        try:
            service.confirm_import(upload)
        except (VprValidationError, VprImportError) as exc:
            messages.error(request, str(exc))
            return redirect("vpr-preview", upload_id=upload.pk)
        except Exception as exc:  # noqa: BLE001
            logger.exception("VPR confirm import failed")
            messages.error(request, f"Ошибка импорта: {exc}")
            return redirect("vpr-preview", upload_id=upload.pk)

        upload.refresh_from_db()
        messages.success(request, "Импорт протокола ВПР успешно завершён.")
        if hasattr(upload, "protocol"):
            return redirect("vpr-protocol-detail", protocol_id=upload.protocol.pk)
        return redirect("vpr-registry")


class VprImportResultView(LoginRequiredMixin, DetailView):
    template_name = "vpr/result.html"
    model = VprUpload
    pk_url_kwarg = "upload_id"
    context_object_name = "upload"

    def dispatch(self, request, *args, **kwargs):
        upload = self.get_object()
        if not can_access_upload(request.user, upload):
            return redirect("vpr-upload")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["protocol"] = getattr(self.object, "protocol", None)
        context["logs"] = self.object.logs.all()[:50]
        context["user_role"] = self.request.user.role
        return context
