from django.contrib import admin

from apps.vpr.models import (
    VprImportLog,
    VprProtocol,
    VprStudentResult,
    VprTask,
    VprTaskCatalogEntry,
    VprTaskCatalogImport,
    VprTaskScore,
    VprUpload,
)


@admin.register(VprUpload)
class VprUploadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "original_filename",
        "status",
        "school",
        "students_imported",
        "tasks_imported",
        "created_at",
    )
    list_filter = ("status", "template_key")
    search_fields = ("original_filename", "error_message")
    readonly_fields = ("preview_payload", "created_at", "processed_at")


@admin.register(VprProtocol)
class VprProtocolAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subject",
        "parallel",
        "academic_year",
        "exam_date",
        "organization_name",
        "participants_count",
        "tasks_count",
    )
    list_filter = ("subject", "parallel", "academic_year")
    search_fields = ("organization_name", "organization_code", "subject")


@admin.register(VprTask)
class VprTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "protocol", "position", "code", "max_score", "difficulty")
    list_filter = ("difficulty",)


@admin.register(VprStudentResult)
class VprStudentResultAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "protocol",
        "participant_code",
        "class_group",
        "primary_score",
        "mark_vpr",
        "mark_journal",
    )
    search_fields = ("participant_code", "full_name")


@admin.register(VprTaskScore)
class VprTaskScoreAdmin(admin.ModelAdmin):
    list_display = ("id", "result", "task", "score", "max_score", "raw_value")


@admin.register(VprImportLog)
class VprImportLogAdmin(admin.ModelAdmin):
    list_display = ("id", "upload", "level", "message", "created_at")
    list_filter = ("level",)


@admin.register(VprTaskCatalogEntry)
class VprTaskCatalogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "academic_year",
        "subject",
        "parallel",
        "task_code",
        "topic",
        "checked_skill",
        "program_section",
        "difficulty",
        "max_score",
        "is_active",
    )
    list_filter = ("academic_year", "subject", "parallel", "difficulty", "is_active")
    search_fields = (
        "subject",
        "task_code",
        "topic",
        "checked_skill",
        "program_section",
        "short_description",
    )
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Идентификация",
            {
                "fields": (
                    "academic_year",
                    "subject",
                    "parallel",
                    "task_number",
                    "task_subnumber",
                    "task_code",
                    "official_code",
                    "max_score",
                    "is_active",
                )
            },
        ),
        (
            "Методическое содержание",
            {
                "fields": (
                    "checked_skill",
                    "fgos_result",
                    "program_section",
                    "topic",
                    "topic_subsection",
                    "difficulty",
                    "task_type",
                    "short_description",
                    "normative_source",
                )
            },
        ),
        ("Расширение", {"fields": ("extra", "created_at", "updated_at")}),
    )


@admin.register(VprTaskCatalogImport)
class VprTaskCatalogImportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "original_filename",
        "source_format",
        "status",
        "created_count",
        "updated_count",
        "error_count",
        "created_at",
    )
    list_filter = ("status", "source_format")
    readonly_fields = ("details", "created_at")
