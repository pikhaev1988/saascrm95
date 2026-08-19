from django.contrib import admin, messages
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import path, reverse

from exams.models import ExamType
from uploads.models import UploadSession
from uploads.parsers import parse_ege, parse_oge


@admin.register(UploadSession)
class UploadSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "exam_type", "school", "district", "uploaded_by", "status", "results_imported", "created_at", "reverted_at")
    list_filter = ("exam_type", "status", "created_at")
    search_fields = ("uploaded_by__username", "error_message", "school__code", "district__code")
    ordering = ("-created_at",)
    change_list_template = "admin/uploads/uploadsession/change_list.html"
    actions = None

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "upload-ege/",
                self.admin_site.admin_view(self.upload_ege_view),
                name="uploads_uploadsession_upload_ege",
            ),
            path(
                "upload-oge/",
                self.admin_site.admin_view(self.upload_oge_view),
                name="uploads_uploadsession_upload_oge",
            ),
        ]
        return custom_urls + urls

    def upload_ege_view(self, request):
        return self._handle_upload(request, ExamType.EGE)

    def upload_oge_view(self, request):
        return self._handle_upload(request, ExamType.OGE)

    def _handle_upload(self, request, exam_type):
        changelist_url = reverse("admin:uploads_uploadsession_changelist")
        if request.method != "POST":
            return HttpResponseRedirect(changelist_url)

        file_obj = request.FILES.get("file")
        if not file_obj:
            messages.error(request, "Файл не передан.")
            return HttpResponseRedirect(changelist_url)

        session = UploadSession.objects.create(
            uploaded_by=request.user,
            exam_type=exam_type,
            file=file_obj,
        )
        session.status = "processing"
        session.error_message = ""
        session.save(update_fields=["status", "error_message"])
        try:
            if exam_type == ExamType.EGE:
                parse_ege(session.file.path)
            else:
                parse_oge(session.file.path)
            session.status = "done"
            session.processed_at = timezone.now()
            session.save(update_fields=["status", "processed_at"])
            messages.success(
                request,
                f"Загрузка {session.get_exam_type_display()} завершена. Сессия #{session.id}.",
            )
        except Exception as exc:
            session.status = "failed"
            session.error_message = str(exc)
            session.save(update_fields=["status", "error_message"])
            messages.error(
                request,
                f"Ошибка загрузки {session.get_exam_type_display()}: {exc}",
            )
        return HttpResponseRedirect(changelist_url)
