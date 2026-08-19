from django.contrib import admin

from analytics.knowledge_models import TaskKnowledge
from analytics.models import AnalyticsSnapshot


@admin.register(TaskKnowledge)
class TaskKnowledgeAdmin(admin.ModelAdmin):
    list_display = (
        "exam_type",
        "subject_key",
        "task_number",
        "topic",
        "fgos_class_start",
        "difficulty",
        "confidence",
        "source_document",
    )
    list_filter = ("exam_type", "subject_key", "document_year", "difficulty")
    search_fields = ("topic", "skill_name", "section", "fipi_content_code")
    readonly_fields = ("last_updated",)


admin.site.register(AnalyticsSnapshot)
