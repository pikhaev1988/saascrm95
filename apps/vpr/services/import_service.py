"""Сервис загрузки и импорта протоколов ВПР."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q
from django.utils import timezone

from apps.vpr.exceptions import VprImportError, VprValidationError
from apps.vpr.models import VprUpload, VprUploadStatus
from apps.vpr.parsers.dto import VprParseResult
from apps.vpr.repositories.protocol_repository import VprProtocolRepository
from apps.vpr.validators.protocol import validate_vpr_file
from organizations.models import School

logger = logging.getLogger(__name__)


def _resolve_school_for_user(user) -> School | None:
    school_id = getattr(user, "school_id", None)
    if school_id:
        return School.objects.filter(pk=school_id).first()
    return None


def _match_school_from_parsed(parsed: VprParseResult, fallback: School | None) -> School | None:
    if fallback:
        return fallback
    name = (parsed.organization_name or "").strip()
    if not name:
        return None
    # МБОУ «СОШ №1 г.Урус-Мартан»(edu203389) → поиск по фрагменту названия
    cleaned = re.sub(r"\(edu\d+\)", "", name, flags=re.IGNORECASE).strip()
    cleaned = cleaned.strip(" «»\"'")
    qs = School.objects.all()
    if cleaned:
        found = qs.filter(name__icontains=cleaned[:40]).first()
        if found:
            return found
    # Попытка по номеру школы
    m = re.search(r"№\s*(\d+)", name)
    city = None
    city_m = re.search(r"г\.\s*([А-Яа-яЁё\-]+)", name)
    if city_m:
        city = city_m.group(1)
    if m:
        number = m.group(1)
        q = Q(name__icontains=f"№{number}") | Q(name__icontains=f"№ {number}")
        if city:
            q &= Q(name__icontains=city)
        found = qs.filter(q).first()
        if found:
            return found
    return None


class VprImportService:
    """Оркестрация: загрузка → проверка → предпросмотр → импорт."""

    def __init__(self) -> None:
        self.repo = VprProtocolRepository()

    def create_upload(
        self,
        *,
        user,
        uploaded_file: UploadedFile,
        school: School | None = None,
        district=None,
    ) -> VprUpload:
        school = school or _resolve_school_for_user(user)
        upload = VprUpload.objects.create(
            uploaded_by=user if getattr(user, "is_authenticated", False) else None,
            school=school,
            district=district or getattr(user, "district", None),
            file=uploaded_file,
            original_filename=getattr(uploaded_file, "name", "") or "",
            status=VprUploadStatus.UPLOADED,
        )
        self.repo.add_log(upload, f"Файл загружен: {upload.original_filename}")
        return upload

    def validate_and_preview(self, upload: VprUpload) -> VprParseResult:
        path = Path(upload.file.path)
        try:
            parsed = validate_vpr_file(path)
        except VprValidationError as exc:
            details = "; ".join(exc.details) if exc.details else ""
            message = exc.message if not details else f"{exc.message} {details}"
            upload.mark_failed(message)
            self.repo.add_log(upload, message, level="error", details={"details": exc.details})
            raise

        upload.status = VprUploadStatus.PREVIEW
        upload.template_key = parsed.template_key
        upload.preview_payload = parsed.preview_dict()
        upload.error_message = ""
        upload.save(
            update_fields=["status", "template_key", "preview_payload", "error_message"]
        )
        self.repo.add_log(
            upload,
            (
                f"Предпросмотр: {parsed.subject}, {parsed.parallel} класс, "
                f"{parsed.participants_count} участников, {parsed.tasks_count} заданий."
            ),
            details=parsed.preview_dict(),
        )
        for warning in parsed.warnings:
            self.repo.add_log(upload, warning, level="warning")
        return parsed

    def confirm_import(self, upload: VprUpload) -> VprParseResult:
        if upload.status == VprUploadStatus.IMPORTED and hasattr(upload, "protocol"):
            raise VprImportError("Эта загрузка уже импортирована.")
        if upload.status == VprUploadStatus.FAILED:
            raise VprImportError("Нельзя импортировать файл с ошибкой проверки.")

        path = Path(upload.file.path)
        try:
            parsed = validate_vpr_file(path)
        except VprValidationError as exc:
            details = "; ".join(exc.details) if exc.details else ""
            message = exc.message if not details else f"{exc.message} {details}"
            upload.mark_failed(message)
            self.repo.add_log(upload, message, level="error")
            raise

        school = _match_school_from_parsed(parsed, upload.school)
        try:
            self.repo.persist_import(upload, parsed, school=school)
        except Exception as exc:  # noqa: BLE001
            logger.exception("VPR import failed upload_id=%s", upload.pk)
            upload.mark_failed(f"Ошибка сохранения данных: {exc}")
            self.repo.add_log(upload, str(exc), level="error")
            raise VprImportError(f"Ошибка сохранения данных: {exc}") from exc

        upload.refresh_from_db()
        protocol = getattr(upload, "protocol", None)
        if protocol is not None:
            from apps.vpr.services.catalog_sync import sync_catalog_for_protocol

            sync_catalog_for_protocol(protocol, user=getattr(upload, "uploaded_by", None))
        return parsed

    def reimport(self, upload: VprUpload) -> VprParseResult:
        """
        Повторный импорт из уже сохранённого файла.
        Не создаёт новую загрузку — перезаписывает протокол текущей сессии.
        """
        if not upload.file:
            raise VprImportError("Исходный файл отсутствует, повторный импорт невозможен.")
        path = Path(upload.file.path)
        if not path.exists():
            raise VprImportError("Исходный файл не найден на диске.")

        try:
            parsed = validate_vpr_file(path)
        except VprValidationError as exc:
            details = "; ".join(exc.details) if exc.details else ""
            message = exc.message if not details else f"{exc.message} {details}"
            upload.mark_failed(message)
            self.repo.add_log(upload, f"Повторный импорт: {message}", level="error")
            raise

        school = _match_school_from_parsed(parsed, upload.school)
        self.repo.add_log(upload, "Запущен повторный импорт из сохранённого файла.")
        try:
            self.repo.persist_import(upload, parsed, school=school)
        except Exception as exc:  # noqa: BLE001
            logger.exception("VPR reimport failed upload_id=%s", upload.pk)
            upload.mark_failed(f"Ошибка повторного импорта: {exc}")
            self.repo.add_log(upload, str(exc), level="error")
            raise VprImportError(f"Ошибка повторного импорта: {exc}") from exc

        upload.refresh_from_db()
        protocol = getattr(upload, "protocol", None)
        if protocol is not None:
            from apps.vpr.services.catalog_sync import sync_catalog_for_protocol

            sync_catalog_for_protocol(protocol, user=getattr(upload, "uploaded_by", None))
        return parsed

    def delete_upload(self, upload: VprUpload) -> None:
        """Удалить импорт ВПР вместе с протоколом и файлом."""
        upload_id = upload.pk
        file_name = ""
        if upload.file:
            file_name = upload.file.name
            try:
                upload.file.delete(save=False)
            except Exception:  # noqa: BLE001
                logger.warning("VPR file delete failed upload_id=%s", upload_id)
        upload.delete()
        logger.info("VPR upload deleted id=%s file=%s", upload_id, file_name)
