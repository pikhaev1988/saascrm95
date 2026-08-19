from __future__ import annotations

import hashlib
import json

from django.core.cache import cache
from django.db.models import Avg, Count

from analytics.engine.tokens import is_success_token
from exams.models import ExamResult, TaskResult


def scope_overview(scope_filter: dict, year: int | None = None) -> dict:
    normalized_scope = json.dumps(scope_filter, sort_keys=True, ensure_ascii=False)
    scope_hash = hashlib.md5(normalized_scope.encode("utf-8")).hexdigest()
    cache_key = f"engine:overview:v2:{scope_hash}:{year or 'all'}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    results_qs = ExamResult.objects.filter(**scope_filter)
    tasks_qs = TaskResult.objects.filter(**scope_filter)
    if year:
        results_qs = results_qs.filter(exam__year=year)
        tasks_qs = tasks_qs.filter(exam__year=year)

    raw_task_values = list(tasks_qs.values("task_number", "value").order_by("task_number"))
    task_agg = {}
    for row in raw_task_values:
        task_num = int(row["task_number"])
        bucket = task_agg.setdefault(task_num, {"task_number": task_num, "total": 0, "plus": 0, "minus": 0})
        bucket["total"] += 1
        if is_success_token(row["value"]):
            bucket["plus"] += 1
        else:
            bucket["minus"] += 1
    task_success = [task_agg[num] for num in sorted(task_agg)]
    hard_tasks = sorted(task_success, key=lambda item: item["minus"], reverse=True)[:10]

    data = {
        "avg_score": results_qs.aggregate(avg_score=Avg("total_score"))["avg_score"] or 0,
        "total_results": results_qs.count(),
        "unique_students": results_qs.values("student_id").distinct().count(),
        "task_success": task_success,
        "hard_tasks": hard_tasks,
    }
    cache.set(cache_key, data, 43200)
    return data
