from analytics.engine.aggregation import scope_overview
from analytics.engine.tokens import is_success_token


def exam_overview(scope_filter: dict, year: int | None = None):
    return scope_overview(scope_filter, year=year)


def russian_2025_school_report(school_id: int | None):
    """Сохранена для обратной совместимости; данные строятся через Analytics Engine."""
    if not school_id:
        return None

    from django.core.cache import cache
    from django.db.models import Avg, Count, Q

    from exams.models import ExamResult, TaskResult

    cache_key = f"russian_2025_school_report:v3:{school_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    base_2025_qs = ExamResult.objects.filter(student__school_id=school_id, exam__year=2025).select_related("exam")
    russian_exam_ids = {
        row["exam_id"]
        for row in base_2025_qs.values("exam_id", "exam__subject").distinct()
        if "рус" in (row.get("exam__subject") or "").lower()
    }
    results_qs = base_2025_qs.filter(exam_id__in=russian_exam_ids)
    tasks_qs = TaskResult.objects.filter(
        student__school_id=school_id,
        exam__year=2025,
        exam_id__in=russian_exam_ids,
    )

    total_results = results_qs.count()
    if total_results == 0:
        data = {
            "year": 2025,
            "subject": "Русский язык",
            "has_data": False,
            "summary": "Нет данных по русскому языку за 2025 год для вашей ОО.",
            "recommendations": [],
        }
        cache.set(cache_key, data, 43200)
        return data

    avg_score = results_qs.aggregate(avg_score=Avg("score"))["avg_score"] or 0
    pass_rate = (
        results_qs.aggregate(passed=Count("id", filter=Q(passed=True)))["passed"] / total_results * 100
        if total_results
        else 0
    )
    weak_tasks = []
    for row in tasks_qs.values("task_number").annotate(
        total=Count("id"),
        minus=Count("id", filter=Q(value="-")),
    ).order_by("-minus", "task_number")[:5]:
        total = int(row["total"] or 0)
        minus = int(row["minus"] or 0)
        success_rate = round(100.0 * (total - minus) / total, 1) if total else 0.0
        weak_tasks.append(
            {
                "task_number": row["task_number"],
                "total": total,
                "minus": minus,
                "success_rate": success_rate,
            }
        )

    from analytics.engine.exam import InsightBuilder

    builder = InsightBuilder()
    subject_avg = round(sum(t["success_rate"] for t in weak_tasks) / len(weak_tasks), 1) if weak_tasks else 0.0
    recommendations = [
        builder.task_insight(
            type("T", (), {"task_number": t["task_number"], "success_rate": t["success_rate"]})(),
            subject_avg,
        )
        for t in weak_tasks[:3]
    ]

    data = {
        "year": 2025,
        "subject": "Русский язык",
        "has_data": True,
        "summary": (
            f"Проанализировано {total_results} результатов. "
            f"Средний балл: {float(avg_score):.2f}. Доля сдавших: {pass_rate:.1f}%."
        ),
        "metrics": {
            "students_count": total_results,
            "avg_score": round(float(avg_score), 2),
            "pass_rate": round(pass_rate, 1),
        },
        "weak_tasks": weak_tasks,
        "recommendations": recommendations,
    }
    cache.set(cache_key, data, 43200)
    return data
