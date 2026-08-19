from django.db import models

from analytics.knowledge_models import TaskKnowledge  # noqa: F401


class AnalyticsSnapshot(models.Model):
    scope = models.CharField(max_length=32)
    scope_id = models.PositiveIntegerField()
    exam_year = models.PositiveIntegerField()
    subject = models.CharField(max_length=255)
    metrics = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("scope", "scope_id", "exam_year", "subject")
        verbose_name = "Снимок аналитики"
        verbose_name_plural = "Снимки аналитики"
