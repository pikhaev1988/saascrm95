"""
Изолированный слой классификации тем заданий ЕГЭ/ОГЭ.

На этапе 1 заполнен только каталог ЕГЭ-2026 / русский язык.
Существующий topic_for_task() сохраняет строковый API.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from json import JSONDecodeError, loads
from pathlib import Path

from users.task_topics import (
    is_usable_catalog_topic,
    manual_task_meta,
    part2_start_task,
    subject_key,
    subject_key_candidates,
)

CATALOG_ROOT = Path(__file__).resolve().parents[1] / "data" / "task_catalog_2026"

_EMPTY_FIPI = {
    "content_codes": [],
    "content_name": "",
    "source_document": "",
    "year": None,
}
_EMPTY_THEME = {"block": "", "display_name": ""}
_EMPTY_PROGRAM = {"grades": [], "items": [], "line_scope": ""}


def _catalog_path(exam_type: str, year: int, subject_key_value: str) -> Path | None:
    et = (exam_type or "ege").lower()
    key = (subject_key_value or "").strip().lower()
    if not key:
        return None
    path = CATALOG_ROOT / et / f"{key}.json"
    if not path.exists():
        return None
    return path


@lru_cache(maxsize=32)
def _load_subject_classification_cached(source_path: str, version_token: int) -> dict:
    source = Path(source_path)
    if not source.exists():
        return {}
    raw = source.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        payload = loads(raw)
    except JSONDecodeError:
        return {}
    exam_type = (payload.get("exam_type") or "").strip().lower()
    subject = (payload.get("subject") or "").strip().lower()
    try:
        year = int(payload.get("year") or 0)
    except (TypeError, ValueError):
        year = 0
    if not exam_type or not subject or not year:
        return {}
    tasks: dict[int, dict] = {}
    for item in payload.get("tasks") or []:
        try:
            number = int(item.get("task"))
        except (TypeError, ValueError):
            continue
        tasks[number] = deepcopy(item)
    return {
        "exam_type": exam_type,
        "subject": subject,
        "year": year,
        "tasks": tasks,
    }


def _load_subject_classification(exam_type: str, year: int, subject_key_value: str) -> dict:
    path = _catalog_path(exam_type, year, subject_key_value)
    if path is None:
        return {}
    version_token = path.stat().st_mtime_ns if path.exists() else 0
    payload = _load_subject_classification_cached(str(path), version_token)
    if not payload:
        return {}
    if payload.get("exam_type") != (exam_type or "ege").lower():
        return {}
    if payload.get("subject") != (subject_key_value or "").strip().lower():
        return {}
    if int(payload.get("year") or 0) != int(year):
        return {}
    return payload


def _official_record(
    subject_name: str,
    task_number: int,
    exam_type: str,
    year: int,
) -> dict | None:
    et = (exam_type or "ege").lower()
    try:
        number = int(task_number)
        year_value = int(year)
    except (TypeError, ValueError):
        return None
    for candidate in subject_key_candidates(subject_name, et):
        payload = _load_subject_classification(et, year_value, candidate)
        record = (payload.get("tasks") or {}).get(number)
        if record:
            return deepcopy(record)
    return None


def official_theme_display_name(
    subject_name: str,
    task_number: int,
    exam_type: str = "ege",
    year: int = 2026,
) -> str | None:
    """Отображаемая тема из нормализованного каталога, если запись есть."""
    record = _official_record(subject_name, task_number, exam_type, year)
    if not record:
        return None
    theme = record.get("theme") or {}
    display_name = str(theme.get("display_name") or "").strip()
    if is_usable_catalog_topic(display_name):
        return display_name
    return None


def _fallback_part(exam_type: str, subject_name: str, task_number: int) -> int:
    sk = subject_key(subject_name, exam_type)
    return 2 if task_number >= part2_start_task(exam_type, sk) else 1


def _envelope(
    *,
    subject_key_value: str,
    exam_type: str,
    year: int,
    task_number: int,
    record: dict | None,
) -> dict:
    if record:
        kim = record.get("kim") or {}
        fipi = record.get("fipi") or {}
        theme = record.get("theme") or {}
        program = record.get("school_program") or {}
        verification = record.get("verification") or {}
        return {
            "subject": subject_key_value,
            "exam_type": exam_type,
            "year": year,
            "task": task_number,
            "kim": {
                "line": int(kim.get("line") or task_number),
                "part": int(kim.get("part") or 1),
                "answer_type": str(kim.get("answer_type") or ""),
            },
            "fipi": {
                "content_codes": list(fipi.get("content_codes") or []),
                "content_name": str(fipi.get("content_name") or ""),
                "source_document": str(fipi.get("source_document") or ""),
                "year": fipi.get("year") if fipi.get("year") is not None else year,
            },
            "theme": {
                "block": str(theme.get("block") or ""),
                "display_name": str(theme.get("display_name") or ""),
            },
            "school_program": {
                "grades": list(program.get("grades") or []),
                "items": list(program.get("items") or []),
                "line_scope": str(program.get("line_scope") or record.get("line_scope") or ""),
            },
            "skills": list(record.get("skills") or []),
            "task_format": str(record.get("task_format") or ""),
            "line_scope": str(record.get("line_scope") or program.get("line_scope") or ""),
            "verification": {
                "status": str(verification.get("status") or "needs_review"),
                "source": str(verification.get("source") or ""),
                "year": verification.get("year") if verification.get("year") is not None else year,
                "note": str(verification.get("note") or ""),
            },
        }
    return {
        "subject": subject_key_value,
        "exam_type": exam_type,
        "year": year,
        "task": task_number,
        "kim": {"line": task_number, "part": 1, "answer_type": ""},
        "fipi": dict(_EMPTY_FIPI),
        "theme": dict(_EMPTY_THEME),
        "school_program": dict(_EMPTY_PROGRAM),
        "skills": [],
        "task_format": "",
        "line_scope": "",
        "verification": {
            "status": "needs_review",
            "source": "",
            "year": year,
            "note": "",
        },
    }


def get_task_classification(
    subject_name: str,
    task_number: int,
    exam_type: str = "ege",
    year: int = 2026,
) -> dict:
    """
    Структурированная классификация задания.

    Не подменяет тему умением: theme и skills — разные поля.
    Ручной ExamTaskTopic не получает status=verified автоматически.
    """
    et = (exam_type or "ege").lower()
    try:
        number = int(task_number)
        year_value = int(year or 2026)
    except (TypeError, ValueError):
        number = int(task_number or 0)
        year_value = 2026
    sk = subject_key(subject_name, et)
    official = _official_record(subject_name, number, et, year_value)
    result = _envelope(
        subject_key_value=sk,
        exam_type=et,
        year=year_value,
        task_number=number,
        record=official,
    )

    manual = manual_task_meta(subject_name, number, et)
    manual_topic = str((manual or {}).get("topic") or "").strip()
    if manual and is_usable_catalog_topic(manual_topic):
        official_display = result["theme"]["display_name"]
        result["theme"]["display_name"] = manual_topic
        if not official or manual_topic != official_display:
            result["verification"] = {
                "status": "needs_review",
                "source": "manual_override",
                "year": year_value,
            }

    if result["theme"]["display_name"]:
        if result["kim"]["line"] == 0:
            result["kim"]["line"] = number
        return result

    from users.task_topics import _legacy_topic_for_task

    legacy = _legacy_topic_for_task(subject_name, number, et)
    result["theme"]["display_name"] = legacy
    result["kim"]["part"] = _fallback_part(et, subject_name, number)
    result["fipi"] = {
        "content_codes": [],
        "content_name": "",
        "source_document": "",
        "year": year_value,
    }
    result["verification"] = {
        "status": "needs_review",
        "source": "legacy_catalog",
        "year": year_value,
    }
    return result
