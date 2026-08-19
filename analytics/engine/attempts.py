"""Выбор итоговой попытки сдачи предмета (резервные дни, пересдача)."""

from __future__ import annotations

from datetime import date as date_cls
from typing import Any

from django.db.models import Exists, OuterRef, QuerySet

from exams.models import ExamResult


def latest_exam_result_ids(qs: QuerySet) -> list[int]:
    """
    Один ExamResult на пару (ученик, предмет): протокол с самой поздней датой.
    При совпадении даты берётся запись с большим id.
    """
    chosen: dict[tuple[Any, str], dict[str, Any]] = {}
    rows = qs.values("id", "student_id", "exam__subject", "exam__exam_date")
    for row in rows.iterator(chunk_size=2000):
        key = (row["student_id"], row["exam__subject"] or "")
        exam_date = row["exam__exam_date"] or date_cls.min
        prev = chosen.get(key)
        if prev is None:
            chosen[key] = {"id": row["id"], "exam_date": exam_date}
            continue
        if exam_date > prev["exam_date"] or (
            exam_date == prev["exam_date"] and int(row["id"]) > int(prev["id"])
        ):
            chosen[key] = {"id": row["id"], "exam_date": exam_date}
    return [int(item["id"]) for item in chosen.values()]


def filter_latest_exam_results(qs: QuerySet) -> QuerySet:
    ids = latest_exam_result_ids(qs)
    if not ids:
        return qs.none()
    return qs.filter(pk__in=ids)


def task_results_for_exam_results(task_qs: QuerySet, exam_result_qs: QuerySet) -> QuerySet:
    ids = latest_exam_result_ids(exam_result_qs)
    if not ids:
        return task_qs.none()
    return task_qs.filter(
        Exists(
            ExamResult.objects.filter(
                pk__in=ids,
                student_id=OuterRef("student_id"),
                exam_id=OuterRef("exam_id"),
            )
        )
    )
