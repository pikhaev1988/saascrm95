"""Реестр протоколов ВПР: список, карточка, действия."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, ListView, View

from apps.vpr.access import can_access_protocol, can_access_upload, user_school
from apps.vpr.exceptions import VprImportError, VprValidationError
from apps.vpr.models import VprProtocol, VprUpload
from apps.vpr.services.import_service import VprImportService
from apps.vpr.services.registry import build_registry

logger = logging.getLogger(__name__)


class VprProtocolRegistryView(LoginRequiredMixin, ListView):
    template_name = "vpr/registry.html"
    context_object_name = "protocols"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role not in {"school", "district"}:
            if not request.user.is_superuser:
                return redirect("cabinet")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Данные собираются в get_context_data через build_registry.
        return VprProtocol.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registry = build_registry(self.request.user, self.request.GET)
        context.update(registry)
        context["school"] = user_school(self.request.user)
        context["user_role"] = getattr(self.request.user, "role", None)
        context["querystring"] = self._querystring_without("page")
        return context

    def _querystring_without(self, *keys: str) -> str:
        params = self.request.GET.copy()
        for key in keys:
            params.pop(key, None)
        return params.urlencode()


class VprProtocolDetailView(LoginRequiredMixin, DetailView):
    template_name = "vpr/protocol_detail.html"
    model = VprProtocol
    pk_url_kwarg = "protocol_id"
    context_object_name = "protocol"

    def dispatch(self, request, *args, **kwargs):
        protocol = self.get_object()
        if not can_access_protocol(request.user, protocol):
            return redirect("vpr-registry")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return VprProtocol.objects.select_related(
            "upload",
            "upload__uploaded_by",
            "school",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        protocol = self.object
        tasks = list(protocol.tasks.all().order_by("position"))
        participants_qs = protocol.student_results.prefetch_related("task_scores__task").order_by(
            "participant_code"
        )
        participants = []
        for row in participants_qs:
            score_by_code = {item.task.code: item for item in row.task_scores.all()}
            row.score_cells = [score_by_code.get(task.code) for task in tasks]
            participants.append(row)
        context["participants"] = participants
        context["tasks"] = tasks
        context["upload"] = protocol.upload
        context["user_role"] = getattr(self.request.user, "role", None)
        context["active_tab"] = "protocol"
        return context


class VprProtocolInfoView(VprProtocolDetailView):
    """Карточка сведений — тот же шаблон, якорь #info."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["focus"] = "info"
        context["active_tab"] = "info"
        return context


class VprUploadFileDownloadView(LoginRequiredMixin, View):
    def get(self, request, upload_id: int, *args, **kwargs):
        upload = get_object_or_404(VprUpload, pk=upload_id)
        if not can_access_upload(request.user, upload):
            return redirect("vpr-registry")
        if not upload.file:
            raise Http404("Файл не сохранён.")
        try:
            handle = upload.file.open("rb")
        except Exception as exc:  # noqa: BLE001
            raise Http404("Файл недоступен.") from exc
        filename = upload.original_filename or f"vpr_upload_{upload.pk}.xlsx"
        return FileResponse(
            handle,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class VprUploadDeleteView(LoginRequiredMixin, View):
    def post(self, request, upload_id: int, *args, **kwargs):
        upload = get_object_or_404(VprUpload, pk=upload_id)
        if not can_access_upload(request.user, upload):
            return redirect("vpr-registry")
        service = VprImportService()
        try:
            service.delete_upload(upload)
            messages.success(request, "Импорт ВПР удалён.")
        except Exception as exc:  # noqa: BLE001
            logger.exception("VPR delete failed")
            messages.error(request, f"Не удалось удалить импорт: {exc}")
        return redirect("vpr-registry")


class VprUploadReimportView(LoginRequiredMixin, View):
    def post(self, request, upload_id: int, *args, **kwargs):
        upload = get_object_or_404(VprUpload, pk=upload_id)
        if not can_access_upload(request.user, upload):
            return redirect("vpr-registry")
        service = VprImportService()
        try:
            service.reimport(upload)
            messages.success(request, "Повторный импорт выполнен успешно.")
            upload.refresh_from_db()
            if hasattr(upload, "protocol"):
                return redirect("vpr-protocol-detail", protocol_id=upload.protocol.pk)
        except (VprValidationError, VprImportError) as exc:
            messages.error(request, str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception("VPR reimport failed")
            messages.error(request, f"Ошибка повторного импорта: {exc}")
        return redirect("vpr-registry")
