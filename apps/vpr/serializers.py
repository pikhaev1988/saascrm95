"""Сериализаторы модуля ВПР (заготовка под будущий API)."""

from __future__ import annotations

from rest_framework import serializers

from apps.vpr.models import VprProtocol, VprStudentResult, VprUpload


class VprUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = VprUpload
        fields = (
            "id",
            "original_filename",
            "status",
            "template_key",
            "students_imported",
            "results_imported",
            "tasks_imported",
            "errors_count",
            "created_at",
            "processed_at",
        )


class VprProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        model = VprProtocol
        fields = (
            "id",
            "subject",
            "parallel",
            "academic_year",
            "exam_date",
            "organization_code",
            "organization_name",
            "municipality",
            "max_primary_score",
            "participants_count",
            "tasks_count",
        )


class VprStudentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = VprStudentResult
        fields = (
            "id",
            "participant_code",
            "full_name",
            "gender",
            "class_group",
            "variant",
            "primary_score",
            "mark_vpr",
            "mark_journal",
        )
