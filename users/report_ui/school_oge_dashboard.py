"""
Presentation packaging for school OGE analytics dashboard.

Pass: grade ≥ 3 (oge_score_passed). Quality ≥ 4. High (отличники) = оценка 5.
Same BI shell as EGE analytics; thresholds differ for the 2–5 grade scale.
"""

from __future__ import annotations

from typing import Any


def build_oge_dashboard_ui(
    *,
    year_qs,
    all_years_qs=None,
    school_subjects: list[dict] | None = None,
    selected_year: int | None = None,
    analysis: dict | None = None,
    comparison: dict | None = None,
    selected_results: list | None = None,
    school=None,
) -> dict[str, Any]:
    from django.db.models import Avg, Count, Q

    from exams.passing import oge_score_passed

    analysis = analysis or {}
    subjects = list(school_subjects or [])

    total_results = 0
    participants = 0
    avg_score = None
    pass_rate = None
    quality_rate = None
    high_count = 0
    avg_delta = None

    subject_stats: dict[int, dict] = {}
    if year_qs is not None:
        total_results = year_qs.count()
        participants = year_qs.values("student_id").distinct().count()
        agg = year_qs.aggregate(
            avg=Avg("score"),
            quality=Count("id", filter=Q(score__gte=4)),
            high=Count("id", filter=Q(score__gte=5)),
        )
        avg_score = round(float(agg["avg"] or 0), 2) if total_results else None
        quality_rate = round((int(agg["quality"] or 0) / total_results) * 100, 1) if total_results else None
        high_count = int(agg["high"] or 0)

        passed_total = 0
        by_exam: dict[int, dict] = {}
        for row in year_qs.values("exam_id", "score", "passed"):
            eid = int(row["exam_id"])
            bucket = by_exam.setdefault(eid, {"total": 0, "passed": 0, "sum": 0.0, "quality": 0})
            score = float(row.get("score") or 0)
            bucket["total"] += 1
            bucket["sum"] += score
            if score >= 4:
                bucket["quality"] += 1
            if oge_score_passed(score, row.get("passed")):
                bucket["passed"] += 1
                passed_total += 1

        pass_rate = round((passed_total / total_results) * 100, 1) if total_results else None
        for eid, bucket in by_exam.items():
            total = int(bucket["total"] or 0)
            subject_stats[eid] = {
                "avg": round(bucket["sum"] / total, 2) if total else None,
                "pass_rate": round((int(bucket["passed"] or 0) / total) * 100, 1) if total else None,
                "quality_rate": round((int(bucket["quality"] or 0) / total) * 100, 1) if total else None,
                "total": total,
            }

        if all_years_qs is not None and selected_year:
            prev = all_years_qs.filter(exam__year=int(selected_year) - 1)
            if prev.exists():
                prev_avg = prev.aggregate(v=Avg("score"))["v"]
                if prev_avg is not None and avg_score is not None:
                    avg_delta = round(float(avg_score) - float(prev_avg), 2)

    enriched_subjects = []
    risk_count = 0
    best_subject = None
    best_avg = None
    for item in subjects:
        eid = int(item.get("exam_id") or 0)
        st = subject_stats.get(eid) or {}
        avg = st.get("avg")
        pr = st.get("pass_rate")
        tone = _subject_tone(pr, avg)
        if pr is not None and pr < 70:
            risk_count += 1
        if avg is not None and (best_avg is None or avg > best_avg):
            best_avg = avg
            best_subject = item.get("subject_label") or item.get("exam__subject")
        level_src = pr if pr is not None else _grade_to_pct(avg)
        enriched_subjects.append(
            {
                **item,
                "avg": avg,
                "pass_rate": pr,
                "quality_rate": st.get("quality_rate"),
                "tone": tone,
                "level_pct": min(100, max(0, float(level_src or 0))),
            }
        )

    subj_kpi = _subject_kpi(analysis, selected_results)
    insights = _insights(analysis)

    district_avg = None
    republic_avg = None
    if year_qs is not None and selected_year and school is not None:
        district_id = getattr(school, "district_id", None)
        if district_id:
            district_avg_raw = (
                year_qs.model.objects.filter(
                    student__school__district_id=district_id,
                    exam__exam_type="oge",
                    exam__year=int(selected_year),
                ).aggregate(v=Avg("score"))["v"]
            )
            if district_avg_raw is not None:
                district_avg = round(float(district_avg_raw), 2)
        republic_avg_raw = (
            year_qs.model.objects.filter(
                exam__exam_type="oge",
                exam__year=int(selected_year),
            ).aggregate(v=Avg("score"))["v"]
        )
        if republic_avg_raw is not None:
            republic_avg = round(float(republic_avg_raw), 2)

    profile = _profile(
        subj_kpi.get("avg_score"),
        avg_score,
        comparison,
        district_avg=district_avg,
        republic_avg=republic_avg,
    )
    status = _school_status(pass_rate, quality_rate, risk_count)

    school_meta = {
        "name": getattr(school, "name", None) or "Школа",
        "code": getattr(school, "code", None) or "—",
        "district": getattr(getattr(school, "district", None), "name", None) or "—",
        "type_label": "Общеобразовательная организация",
    }

    return {
        "school": school_meta,
        "status": status,
        "subjects_count": len(enriched_subjects),
        "participants": participants,
        "avg_score": avg_score,
        "quality_rate": quality_rate,
        "pass_rate": pass_rate,
        "high_count": high_count,
        "avg_delta": avg_delta,
        "risk_subjects": risk_count,
        "best_subject": best_subject,
        "best_subject_score": best_avg,
        "subjects": enriched_subjects,
        "subject_kpi": subj_kpi,
        "insights": insights,
        "profile": profile,
        "has_subjects": bool(enriched_subjects),
        "total_results": total_results,
    }


def _subject_tone(pass_rate, avg) -> str:
    if pass_rate is not None:
        if pass_rate >= 85:
            return "good"
        if pass_rate < 70:
            return "risk"
        return "mid"
    if avg is not None:
        if avg >= 4.0:
            return "good"
        if avg < 3.0:
            return "risk"
        return "mid"
    return "neutral"


def _school_status(pass_rate, quality_rate, risk_count) -> dict:
    if pass_rate is None:
        return {"label": "Нет данных", "tone": "neutral"}
    if pass_rate >= 85 and (quality_rate or 0) >= 40 and risk_count == 0:
        return {"label": "Устойчивый уровень", "tone": "good"}
    if pass_rate < 70 or risk_count >= 3:
        return {"label": "Требует внимания", "tone": "risk"}
    if pass_rate < 85 or (quality_rate or 0) < 30:
        return {"label": "Рабочий уровень", "tone": "mid"}
    return {"label": "Стабильный уровень", "tone": "good"}


def _subject_kpi(analysis: dict, selected_results: list | None) -> dict:
    from exams.passing import oge_score_passed

    students = analysis.get("students_count")
    avg = analysis.get("avg_score")
    min_s = analysis.get("min_score")
    max_s = analysis.get("max_score")
    pass_rate = analysis.get("pass_rate")
    quality = analysis.get("knowledge_quality_percent")
    high = None
    avg_primary = None

    rows = selected_results or []
    if rows:
        scores = []
        primary = []
        high_n = 0
        quality_n = 0
        passed_n = 0
        for row in rows:
            result = row.get("result") if isinstance(row, dict) else row
            if result is None:
                continue
            if isinstance(row, dict) and "below_minimum" in row:
                if not row.get("below_minimum"):
                    passed_n += 1
            try:
                sc = float(getattr(result, "score", None) or 0)
                scores.append(sc)
                if sc >= 5:
                    high_n += 1
                if sc >= 4:
                    quality_n += 1
            except (TypeError, ValueError):
                pass
            try:
                ps = getattr(result, "primary_score", None)
                if ps is not None:
                    primary.append(float(ps))
            except (TypeError, ValueError):
                pass
        n = len(scores)
        if quality is None and n:
            quality = round((quality_n / n) * 100, 1)
        high = high_n
        if primary:
            avg_primary = round(sum(primary) / len(primary), 2)
        if n and any(isinstance(row, dict) and "below_minimum" in row for row in rows):
            pass_rate = round((passed_n / n) * 100, 1)
            students = n
        elif n and pass_rate is None:
            passed_fallback = 0
            for row in rows:
                result = row.get("result") if isinstance(row, dict) else row
                if result is None:
                    continue
                if oge_score_passed(getattr(result, "score", None), getattr(result, "passed", None)):
                    passed_fallback += 1
            pass_rate = round((passed_fallback / n) * 100, 1)
            students = n

    return {
        "students_count": students,
        "avg_score": avg,
        "min_score": min_s,
        "max_score": max_s,
        "pass_rate": pass_rate,
        "quality_rate": quality,
        "high_count": high,
        "avg_primary": avg_primary,
    }


def _insights(analysis: dict) -> dict:
    strength = None
    lines = (analysis.get("strength_summary") or {}).get("lines") or []
    if lines:
        strength = lines[0]
    elif analysis.get("strong_tasks"):
        t = analysis["strong_tasks"][0]
        strength = f"Задание №{t.get('task_number')}: успешность {t.get('success_rate')}%"

    risk = None
    if analysis.get("weak_tasks"):
        t = analysis["weak_tasks"][0]
        risk = f"Задание №{t.get('task_number')}: успешность {t.get('success_rate')}%"
    elif analysis.get("risk_clusters"):
        c = analysis["risk_clusters"][0]
        risk = c.get("label")

    best_task = None
    if analysis.get("strong_tasks"):
        t = analysis["strong_tasks"][0]
        best_task = f"№{t.get('task_number')} · {t.get('success_rate')}%"
        if t.get("topic"):
            best_task += f" · {t.get('topic')}"

    worst_task = None
    if analysis.get("weak_tasks"):
        t = analysis["weak_tasks"][0]
        worst_task = f"№{t.get('task_number')} · {t.get('success_rate')}%"
        if t.get("topic"):
            worst_task += f" · {t.get('topic')}"

    return {
        "strength": strength,
        "risk": risk,
        "best_task": best_task,
        "worst_task": worst_task,
    }


def _profile(
    subject_avg,
    school_avg,
    comparison: dict | None,
    *,
    district_avg=None,
    republic_avg=None,
) -> dict:
    bars = [
        {
            "label": "Средний результат предмета",
            "value": subject_avg,
            "pct": _grade_to_pct(subject_avg),
            "tone": "blue",
        },
        {
            "label": "Относительно школы (среднее по срезу)",
            "value": school_avg,
            "pct": _grade_to_pct(school_avg),
            "tone": "navy",
        },
    ]
    if comparison and comparison.get("trend_delta") is not None:
        bars.append(
            {
                "label": "Динамика предмета (срез лет)",
                "value": comparison.get("trend_delta"),
                "pct": _delta_to_pct(comparison.get("trend_delta")),
                "tone": "green" if float(comparison.get("trend_delta") or 0) >= 0 else "risk",
                "is_delta": True,
            }
        )
    if district_avg is not None:
        bars.append(
            {
                "label": "Средний по району (загруженные протоколы)",
                "value": district_avg,
                "pct": _grade_to_pct(district_avg),
                "tone": "mid",
            }
        )
    else:
        bars.append(
            {
                "label": "Средний по району (загруженные протоколы)",
                "value": None,
                "pct": 0,
                "tone": "muted",
                "empty": True,
            }
        )
    if republic_avg is not None:
        bars.append(
            {
                "label": "Средний по всем ОО в системе",
                "value": republic_avg,
                "pct": _grade_to_pct(republic_avg),
                "tone": "mid",
            }
        )
    else:
        bars.append(
            {
                "label": "Средний по всем ОО в системе",
                "value": None,
                "pct": 0,
                "tone": "muted",
                "empty": True,
            }
        )
    return {"bars": bars}


def _grade_to_pct(v) -> float:
    """Map OGE grade ~2–5 onto bar width 0–100."""
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


def _delta_to_pct(v) -> float:
    try:
        return max(0.0, min(100.0, 50.0 + float(v) * 25.0))
    except (TypeError, ValueError):
        return 50.0
