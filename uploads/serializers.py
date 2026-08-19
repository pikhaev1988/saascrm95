from rest_framework import serializers

from uploads.models import UploadSession


class UploadSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadSession
        fields = ("id", "uploaded_by", "exam_type", "file", "status", "error_message", "created_at", "processed_at")
        read_only_fields = ("status", "error_message", "created_at", "processed_at", "uploaded_by")

    def validate_file(self, value):
        allowed_extensions = (".xlsx", ".xls", ".csv")
        if not value.name.lower().endswith(allowed_extensions):
            raise serializers.ValidationError("Поддерживаются форматы .xlsx, .xls, .csv")
        if value.size > 25 * 1024 * 1024:
            raise serializers.ValidationError("Размер файла больше 25MB")
        return value
