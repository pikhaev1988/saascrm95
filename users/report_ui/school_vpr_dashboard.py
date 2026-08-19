"""
Presentation packaging for school VPR analytics dashboard.

Uses VprAnalyticsEngine summaries (absolute ≥3, quality 4–5, marks 2–5).
Same BI shell as EGE/OGE analytics.
"""

from __future__ import annotations

from typing import Any


def build_vpr_dashboard_ui(
    *,
    protocols,
    school_subjects: list[dict] | None = None,
    selected_year: int | None = None,
    selected_summary=None,
    selected_analytics=None,
    school=None,
) -> dict[str, Any]:
    from apps.vpr.analytics import VprAnalyticsEngine

    subjects_meta = list(school_subjects or [])
    protocol_list = list(protocols) if protocols is not None else []
    engine = VprAnalyticsEngine()

    summaries_by_id: dict[int, Any] = {}
    if selected_summary is not None and selected_analytics is not None:
        pid = getattr(selected_analytics, "protocol_id", None)
        if pid is not None:
            summaries_by_id[int(pid)] = selected_summary

    for protocol in protocol_list:
        pid = int(protocol.id)
        if pid in summaries_by_id:
            continue
        try:
            result = engine.analyze(protocol)
            summaries_by_id[pid] = result.summary
        except Exception:
            continue

    total_participants = 0
    weighted_abs = 0.0
    weighted_quality = 0.0
    weighted_mark = 0.0
    weight_abs = 0
    weight_quality = 0
    weight_mark = 0
    high_count = 0
    avg_mark_values: list[float] = []

    enriched_subjects = []
    risk_count = 0
    best_subject = None
    best_metric = None

    for item in subjects_meta:
        eid = int(item.get("exam_id") or 0)
        summary = summaries_by_id.get(eid)
        participants = int(item.get("students_count") or 0)
        if summary is not None:
            participants = int(summary.participants_count or participants or 0)
            abs_rate = summary.absolute_achievement_percent
            quality = summary.knowledge_quality_percent
            avg_mark = summary.avg_mark_vpr
            avg_primary = summary.avg_primary_score
        else:
            abs_rate = quality = avg_mark = avg_primary = None

        total_participants += participants
        if abs_rate is not None and participants:
            weighted_abs += float(abs_rate) * participants
            weight_abs += participants
        if quality is not None and participants:
            weighted_quality += float(quality) * participants
            weight_quality += participants
        if avg_mark is not None and participants:
            weighted_mark += float(avg_mark) * participants
            weight_mark += participants
            avg_mark_values.append(float(avg_mark))

        tone = _subject_tone(abs_rate, avg_mark)
        if abs_rate is not None and float(abs_rate) < 70:
            risk_count += 1
        metric_for_best = avg_mark if avg_mark is not None else abs_rate
        if metric_for_best is not None and (best_metric is None or float(metric_for_best) > float(best_metric)):
            best_metric = metric_for_best
            best_subject = item.get("subject_label") or item.get("exam__subject")

        level_pct = float(abs_rate) if abs_rate is not None else _mark_to_pct(avg_mark)
        enriched_subjects.append(
            {
                **item,
                "avg": round(float(avg_mark), 2) if avg_mark is not None else (
                    round(float(avg_primary), 2) if avg_primary is not None else None
                ),
                "pass_rate": round(float(abs_rate), 1) if abs_rate is not None else None,
                "quality_rate": round(float(quality), 1) if quality is not None else None,
                "tone": tone,
                "level_pct": min(100.0, max(0.0, level_pct)),
            }
        )

    pass_rate = round(weighted_abs / weight_abs, 1) if weight_abs else None
    quality_rate = round(weighted_quality / weight_quality, 1) if weight_quality else None
    avg_score = round(weighted_mark / weight_mark, 2) if weight_mark else None

    # «Отличники» по выбранному протоколу (оценка 5), иначе сумма по срезу недоступна без students
    if selected_analytics is not None:
        high_count = sum(
            1 for s in (selected_analytics.students or []) if getattr(s, "mark_vpr", None) == 5
        )
    else:
        high_count = 0

    avg_delta = None
    # Динамика средней отметки: selected year vs previous (по доступным протоколам того же qs без фильтра)
    # передаётся только срез года — дельту считаем в view при необходимости; здесь None по умолчанию.

    subject_kpi = _subject_kpi(selected_summary, selected_analytics)
    insights = _insights(selected_summary, selected_analytics)
    profile = _profile(selected_summary, avg_score)
    status = _school_status(pass_rate, quality_rate, risk_count)

    school_meta = {
        "name": getattr(school, "name", None) or "Школа",
        "code": getattr(school, "code", None) or "—",
        "district": getattr(getattr(school, "district", None), "name", None) or "—",
        "type_label": "Общеобразовательная организация",
    }

    weak_tasks = []
    strong_tasks = []
    task_rows = []
    if selected_analytics is not None:
        tasks = list(selected_analytics.tasks or [])
        ranked = sorted(
            [t for t in tasks if t.completion_percent is not None],
            key=lambda t: float(t.completion_percent),
        )
        weak_tasks = [
            {
                "task_number": t.task_number or t.task_code,
                "topic": t.topic or t.checked_skill or "—",
                "success_rate": round(float(t.completion_percent), 1),
                "zero_count": t.zero_count,
                "full_count": t.full_count,
                "correct_count": int(getattr(t, "correct_count", None) or t.full_count or 0),
                "incorrect_count": int(getattr(t, "incorrect_count", None) or t.zero_count or 0),
                "partial_count": int(t.partial_count or 0),
                "answers_count": t.answers_count,
            }
            for t in ranked[:8]
        ]
        strong_tasks = [
            {
                "task_number": t.task_number or t.task_code,
                "topic": t.topic or t.checked_skill or "—",
                "success_rate": round(float(t.completion_percent), 1),
                "correct_count": int(getattr(t, "correct_count", None) or t.full_count or 0),
                "incorrect_count": int(getattr(t, "incorrect_count", None) or t.zero_count or 0),
                "partial_count": int(t.partial_count or 0),
                "answers_count": t.answers_count,
            }
            for t in reversed(ranked[-5:])
        ]
        ordered_tasks = sorted(tasks, key=lambda t: (int(t.position or 0), str(t.task_code or "")))
        task_rows = []
        for t in ordered_tasks:
            total = int(t.answers_count or 0)
            plus = int(getattr(t, "correct_count", None) or t.full_count or 0)
            # Как в ЕГЭ: верно + ошибок = всего (частичный балл относится к «ошибок»)
            minus = max(0, total - plus)
            success = round(100.0 * plus / total, 1) if total else (
                round(float(t.completion_percent), 1) if t.completion_percent is not None else None
            )
            task_rows.append(
                {
                    "task_number": t.task_number or t.task_code,
                    "topic": t.topic or "—",
                    "skill": t.checked_skill or "",
                    "section": t.program_section or "",
                    "skill_name": t.checked_skill or "",
                    "success_rate": success,
                    "plus": plus,
                    "minus": minus,
                    "partial": int(t.partial_count or 0),
                    "total": total,
                }
            )
        # В слабых/сильных — те же счётчики «верно / ошибок»
        for row in weak_tasks:
            total = int(row.get("answers_count") or 0)
            plus = int(row.get("correct_count") or row.get("full_count") or 0)
            row["plus"] = plus
            row["minus"] = max(0, total - plus)
            row["incorrect_count"] = row["minus"]
        for row in strong_tasks:
            total = int(row.get("answers_count") or 0)
            plus = int(row.get("correct_count") or 0)
            row["plus"] = plus
            row["minus"] = max(0, total - plus)
            row["incorrect_count"] = row["minus"]

    marks_bars = []
    if selected_analytics is not None and selected_analytics.marks:
        vpr_counts = selected_analytics.marks.vpr or {}
        total_m = sum(int(v or 0) for v in vpr_counts.values()) or 1
        for mark in ("2", "3", "4", "5"):
            count = int(vpr_counts.get(mark) or 0)
            marks_bars.append(
                {
                    "label": f"Оценка {mark}",
                    "value": count,
                    "pct": round(count / total_m * 100, 1),
                }
            )

    return {
        "school": school_meta,
        "status": status,
        "subjects_count": len(enriched_subjects),
        "participants": total_participants,
        "avg_score": avg_score,
        "quality_rate": quality_rate,
        "pass_rate": pass_rate,
        "high_count": high_count,
        "avg_delta": avg_delta,
        "risk_subjects": risk_count,
        "best_subject": best_subject,
        "best_subject_score": round(float(best_metric), 2) if best_metric is not None else None,
        "subjects": enriched_subjects,
        "subject_kpi": subject_kpi,
        "insights": insights,
        "profile": profile,
        "has_subjects": bool(enriched_subjects),
        "weak_tasks": weak_tasks,
        "strong_tasks": strong_tasks,
        "task_rows": task_rows,
        "marks_bars": marks_bars,
        "selected_year": selected_year,
    }


def _subject_tone(pass_rate, avg_mark) -> str:
    if pass_rate is not None:
        if float(pass_rate) >= 85:
            return "good"
        if float(pass_rate) < 70:
            return "risk"
        return "mid"
    if avg_mark is not None:
        if float(avg_mark) >= 4.0:
            return "good"
        if float(avg_mark) < 3.0:
            return "risk"
        return "mid"
    return "neutral"


def _school_status(pass_rate, quality_rate, risk_count) -> dict:
    if pass_rate is None:
        return {"label": "Нет данных", "tone": "neutral"}
    if float(pass_rate) >= 85 and (quality_rate or 0) >= 40 and risk_count == 0:
        return {"label": "Устойчивый уровень", "tone": "good"}
    if float(pass_rate) < 70 or risk_count >= 3:
        return {"label": "Требует внимания", "tone": "risk"}
    if float(pass_rate) < 85 or (quality_rate or 0) < 30:
        return {"label": "Рабочий уровень", "tone": "mid"}
    return {"label": "Стабильный уровень", "tone": "good"}


def _subject_kpi(summary, analytics) -> dict:
    if summary is None:
        return {
            "students_count": None,
            "avg_score": None,
            "min_score": None,
            "max_score": None,
            "pass_rate": None,
            "quality_rate": None,
            "high_count": None,
            "avg_primary": None,
            "avg_mark": None,
            "avg_journal": None,
        }
    high = None
    if analytics is not None:
        high = sum(1 for s in (analytics.students or []) if getattr(s, "mark_vpr", None) == 5)
    return {
        "students_count": summary.participants_count,
        "avg_score": summary.avg_mark_vpr,
        "min_score": summary.min_primary_score,
        "max_score": summary.max_primary_result,
        "pass_rate": summary.absolute_achievement_percent,
        "quality_rate": summary.knowledge_quality_percent,
        "high_count": high,
        "avg_primary": summary.avg_primary_score,
        "avg_mark": summary.avg_mark_vpr,
        "avg_journal": summary.avg_mark_journal,
    }


def _insights(summary, analytics) -> dict:
    strength = None
    risk = None
    best_task = None
    worst_task = None

    if summary is not None:
        if summary.knowledge_quality_percent is not None and float(summary.knowledge_quality_percent) >= 50:
            strength = f"Качество знаний {summary.knowledge_quality_percent}% (доля оценок 4–5)."
        if summary.absolute_achievement_percent is not None and float(summary.absolute_achievement_percent) < 70:
            risk = f"Абсолютная успеваемость {summary.absolute_achievement_percent}% — ниже целевого уровня."
        elif summary.avg_mark_vpr is not None and summary.avg_mark_journal is not None:
            delta = float(summary.avg_mark_journal) - float(summary.avg_mark_vpr)
            if abs(delta) >= 0.4:
                risk = (
                    f"Расхождение отметок: журнал {summary.avg_mark_journal}, "
                    f"ВПР {summary.avg_mark_vpr} (Δ {delta:+.2f})."
                )

    if analytics is not None:
        tasks = [t for t in (analytics.tasks or []) if t.completion_percent is not None]
        if tasks:
            best = max(tasks, key=lambda t: float(t.completion_percent))
            worst = min(tasks, key=lambda t: float(t.completion_percent))
            best_correct = int(getattr(best, "correct_count", None) or best.full_count or 0)
            worst_incorrect = int(getattr(worst, "incorrect_count", None) or worst.zero_count or 0)
            best_total = int(best.answers_count or 0)
            worst_total = int(worst.answers_count or 0)
            best_task = (
                f"№{best.task_number or best.task_code} · {round(float(best.completion_percent), 1)}%"
                f" (верно {best_correct} из {best_total})"
            )
            if best.topic:
                best_task += f" · {best.topic}"
            worst_task = (
                f"№{worst.task_number or worst.task_code} · {round(float(worst.completion_percent), 1)}%"
                f" (неверно {worst_incorrect} из {worst_total})"
            )
            if worst.topic:
                worst_task += f" · {worst.topic}"
            if risk is None and float(worst.completion_percent) < 50:
                risk = (
                    f"Задание №{worst.task_number or worst.task_code}: успешность "
                    f"{round(float(worst.completion_percent), 1)}% "
                    f"(неверно {worst_incorrect} из {worst_total})."
                )
            if strength is None and float(best.completion_percent) >= 80:
                strength = (
                    f"Задание №{best.task_number or best.task_code}: успешность "
                    f"{round(float(best.completion_percent), 1)}% "
                    f"(верно {best_correct} из {best_total})."
                )

    return {
        "strength": strength,
        "risk": risk,
        "best_task": best_task,
        "worst_task": worst_task,
    }


def _profile(summary, school_avg_mark) -> dict:
    bars = []
    if summary is not None:
        bars.append(
            {
                "label": "Средняя отметка ВПР (предмет)",
                "value": summary.avg_mark_vpr,
                "pct": _mark_to_pct(summary.avg_mark_vpr),
                "tone": "blue",
            }
        )
        bars.append(
            {
                "label": "Средняя отметка журнала",
                "value": summary.avg_mark_journal,
                "pct": _mark_to_pct(summary.avg_mark_journal),
                "tone": "navy",
                "empty": summary.avg_mark_journal is None,
            }
        )
        bars.append(
            {
                "label": "Абсолютная успеваемость",
                "value": summary.absolute_achievement_percent,
                "pct": float(summary.absolute_achievement_percent or 0),
                "tone": "green" if (summary.absolute_achievement_percent or 0) >= 85 else "mid",
                "is_percent": True,
            }
        )
        bars.append(
            {
                "label": "Качество знаний (4–5)",
                "value": summary.knowledge_quality_percent,
                "pct": float(summary.knowledge_quality_percent or 0),
                "tone": "mid",
                "is_percent": True,
            }
        )
    else:
        bars.append(
            {
                "label": "Средняя отметка ВПР по школе (срез)",
                "value": school_avg_mark,
                "pct": _mark_to_pct(school_avg_mark),
                "tone": "blue",
                "empty": school_avg_mark is None,
            }
        )
    return {"bars": bars}


def _mark_to_pct(v) -> float:
    if v is None:
        return 0.0
    try:
        grade = float(v)
    except (TypeError, ValueError):
        return 0.0
    if grade <= 0:
        return 0.0
    if grade <= 5:
        return max(0.0, min(100.0, ((grade - 2.0) / 3.0) * 100.0))
    return max(0.0, min(100.0, grade))
