from django.db import models

from exams.models import ExamType


class UploadStatus(models.TextChoices):
    PENDING = "pending", "Ожидает"
    PROCESSING = "processing", "Обрабатывается"
    DONE = "done", "Завершено"
    FAILED = "failed", "Ошибка"


class UploadSession(models.Model):
    uploaded_by = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="uploads")
    school = models.ForeignKey(
        "organizations.School",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="upload_sessions",
        verbose_name="Школа",
    )
    district = models.ForeignKey(
        "organizations.District",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="upload_sessions",
        verbose_name="Район",
    )
    exam_type = models.CharField(max_length=8, choices=ExamType.choices)
    file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    status = models.CharField(max_length=20, choices=UploadStatus.choices, default=UploadStatus.PENDING)
    error_message = models.TextField(blank=True)
    exams = models.ManyToManyField("exams.Exam", related_name="upload_sessions", blank=True)
    results_imported = models.PositiveIntegerField(default=0, verbose_name="Загружено записей")
    exams_processed = models.PositiveIntegerField(default=0, verbose_name="Обработано экзаменов")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    reverted_at = models.DateTimeField(null=True, blank=True, verbose_name="Отменена")

    def __str__(self):
        return f"{self.exam_type} #{self.pk} ({self.status})"

    class Meta:
        verbose_name = "Сессия загрузки"
        verbose_name_plural = "Сессии загрузки"
