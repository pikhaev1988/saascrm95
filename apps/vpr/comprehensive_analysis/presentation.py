"""Презентационные срезы для экранов ВПР поверх VprComprehensiveAnalysisResult."""

from __future__ import annotations

from typing import Any

MARK_KEYS = ("2", "3", "4", "5")
PRIORITY_ORDER = ("Critical", "High", "Medium", "Low")
PRIORITY_LABELS = {
    "Critical": "Критические",
    "High": "Высокие",
    "Medium": "Средние",
    "Low": "Низкие",
}
# Подписи приоритета в таблице заданий (ед. число)
PRIORITY_BADGE_LABELS = {
    "Critical": "Критический",
    "High": "Высокий",
    "Medium": "Средний",
    "Low": "Низкий",
}

STATUS_LABELS = {
    "critical_deficit": "Критический дефицит",
    "problem_zone": "Проблемная зона",
    "ok": "Норма",
}


def status_label(status: str | None) -> str:
    if not status:
        return "—"
    return STATUS_LABELS.get(status, status)


def priority_label(priority: str | None) -> str:
    if not priority:
        return "—"
    return PRIORITY_BADGE_LABELS.get(priority, priority)


def build_marks_rows(analysis) -> list[dict[str, Any]]:
    analytics = analysis.analytics
    if analytics is None:
        return []
    marks = getattr(analytics, "marks", None)
    counts = (marks.vpr if marks else None) or {}
    percents = (marks.vpr_percents if marks else None) or {}
    return [
        {"mark": mark, "count": counts.get(mark, 0), "percent": percents.get(mark)}
        for mark in MARK_KEYS
    ]


def build_scores_rows(analysis) -> list[dict[str, Any]]:
    analytics = analysis.analytics
    if analytics is None:
        return []
    scores = getattr(analytics, "scores", None)
    counts = (scores.counts if scores else None) or {}
    percents = (scores.percents if scores else None) or {}
    return [
        {"score": score, "count": count, "percent": percents.get(score)}
        for score, count in counts.items()
    ]


def build_task_rows(analysis) -> list[dict[str, Any]]:
    analytics = analysis.analytics
    deficits = analysis.deficits
    if analytics is None:
        return []
    by_code = {}
    if deficits is not None and hasattr(deficits, "tasks"):
        by_code = {item.task_code: item for item in deficits.tasks}
    rows = []
    for task in analytics.tasks:
        deficit = by_code.get(task.task_code)
        correct = int(getattr(task, "correct_count", None) or task.full_count or 0)
        answers = int(task.answers_count or 0)
        # Верно (+) + Ошибок (-) = Всего (как в ЕГЭ): частичный балл входит в «ошибок»
        incorrect = max(0, answers - correct)
        partial = int(task.partial_count or 0)
        rows.append(
            {
                "task_code": task.task_code,
                "position": task.position,
                "max_score": task.max_score,
                "avg_score": task.avg_score,
                "completion_percent": task.completion_percent,
                "full_count": task.full_count,
                "partial_count": partial,
                "zero_count": task.zero_count,
                "answers_count": answers,
                "correct_count": correct,
                "incorrect_count": incorrect,
                "plus": correct,
                "minus": incorrect,
                "total": answers,
                "success_rate": round(100.0 * correct / answers, 1) if answers else None,
                "topic": task.topic,
                "checked_skill": task.checked_skill,
                "program_section": task.program_section,
                "difficulty": task.difficulty,
                "status": deficit.status if deficit else None,
                "status_label": status_label(deficit.status if deficit else None),
                "priority": deficit.priority if deficit else None,
                "priority_label": priority_label(deficit.priority if deficit else None),
                "mastery_level": deficit.mastery_level if deficit else None,
                "mastery_label": deficit.mastery_label if deficit else None,
            }
        )
    rows.sort(key=lambda row: (row["position"], row["task_code"]))
    return rows


def build_student_rows(analysis) -> list[dict[str, Any]]:
    analytics = analysis.analytics
    deficits = analysis.deficits
    if analytics is None:
        return []
    by_code = {}
    if deficits is not None and hasattr(deficits, "students"):
        by_code = {item.participant_code: item for item in deficits.students}
    rows = []
    for student in analytics.students:
        deficit = by_code.get(student.participant_code)
        rows.append(
            {
                "participant_code": student.participant_code,
                "full_name": student.full_name,
                "primary_score": student.primary_score,
                "completion_percent": student.completion_percent,
                "place_overall": student.place_overall,
                "critical_tasks_count": deficit.critical_tasks_count if deficit else None,
                "unfinished_tasks_count": deficit.unfinished_tasks_count if deficit else None,
            }
        )
    return rows


def build_priority_summary(analysis) -> list[dict[str, Any]]:
    deficits = analysis.deficits
    counts = {key: 0 for key in PRIORITY_ORDER}
    if deficits is not None and hasattr(deficits, "tasks"):
        for task in deficits.tasks:
            if task.priority in counts:
                counts[task.priority] += 1
    return [
        {"code": code, "label": PRIORITY_LABELS[code], "count": counts[code]}
        for code in PRIORITY_ORDER
    ]
