"""Валидация протоколов ВПР до импорта."""

from __future__ import annotations

from pathlib import Path

from apps.vpr.exceptions import VprValidationError
from apps.vpr.parsers.dto import VprParseResult
from apps.vpr.parsers.registry import detect_and_parse


def validate_vpr_file(path: Path | str) -> VprParseResult:
    """
    Полная проверка файла:
    читаемость, лист, структура, метаданные, учащиеся, задания, итоги.
    """
    result = detect_and_parse(path)
    errors: list[str] = []

    if not result.subject:
        errors.append("Не определён предмет.")
    if not result.parallel:
        errors.append("Не определён класс.")
    if not result.academic_year:
        errors.append("Не определён учебный год.")
    if not result.organization_name and not result.organization_code:
        errors.append("Не определена образовательная организация.")
    if result.participants_count <= 0:
        errors.append("Не найдены учащиеся.")
    if result.tasks_count <= 0:
        errors.append("Не найдены задания.")

    missing_scores = sum(1 for s in result.students if s.primary_score is None)
    if missing_scores == result.participants_count:
        errors.append("Не найдены итоговые первичные баллы участников.")

    missing_marks = sum(1 for s in result.students if s.mark_vpr is None)
    if missing_marks == result.participants_count:
        errors.append("Не найдены отметки ВПР участников.")

    if errors:
        raise VprValidationError(
            "Файл не прошёл проверку структуры протокола ВПР.",
            details=errors,
        )
    return result
