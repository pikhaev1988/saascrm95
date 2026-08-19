from __future__ import annotations

from analytics.engine.result import VALIDATION_ERROR_MESSAGE


def _approx_equal(a: float, b: float, tol: float = 0.05) -> bool:
    return abs(float(a) - float(b)) <= tol


def validate_exam_metrics(
    *,
    students_count: int,
    avg_score: float,
    median_score: float,
    min_score: float,
    max_score: float,
    pass_count: int,
    fail_count: int,
    score_values: list[float],
    tasks: list[dict],
    raw_task_rows: list[dict],
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if students_count <= 0:
        errors.append("Количество участников равно нулю.")
        return False, errors

    if len(score_values) != students_count:
        errors.append(
            f"Число итоговых баллов ({len(score_values)}) не совпадает с числом участников ({students_count})."
        )

    if score_values:
        recomputed_avg = round(sum(score_values) / len(score_values), 2)
        if not _approx_equal(recomputed_avg, avg_score, 0.02):
            errors.append(
                f"Средний балл {avg_score} не совпадает с пересчётом {recomputed_avg}."
            )
        recomputed_min = round(min(score_values), 2)
        recomputed_max = round(max(score_values), 2)
        if not _approx_equal(recomputed_min, min_score, 0.02):
            errors.append(f"Минимальный балл {min_score} ≠ {recomputed_min}.")
        if not _approx_equal(recomputed_max, max_score, 0.02):
            errors.append(f"Максимальный балл {max_score} ≠ {recomputed_max}.")

    if pass_count + fail_count != students_count:
        errors.append(
            f"Сумма сдавших ({pass_count}) и не сдавших ({fail_count}) ≠ участников ({students_count})."
        )

    task_totals: dict[int, dict[str, int]] = {}
    for row in raw_task_rows:
        num = int(row["task_number"])
        bucket = task_totals.setdefault(num, {"total": 0, "plus": 0, "minus": 0, "blank": 0})
        bucket["total"] += 1
        value = row.get("value")
        token = str(value or "").strip()
        if not token:
            bucket["blank"] += 1
        elif token == "+":
            bucket["plus"] += 1
        elif token in {"-", "0"}:
            bucket["minus"] += 1
        elif token.isdigit():
            if int(token) > 0:
                bucket["plus"] += 1
            else:
                bucket["minus"] += 1
        else:
            bucket["minus"] += 1

    for task in tasks:
        num = int(task["task_number"])
        source = task_totals.get(num)
        if not source:
            continue
        if int(task["total"]) != source["total"]:
            errors.append(f"Задание №{num}: total {task['total']} ≠ {source['total']}.")
        if int(task["correct"]) != source["plus"]:
            errors.append(f"Задание №{num}: correct {task['correct']} ≠ {source['plus']}.")
        if int(task["wrong"]) != source["minus"]:
            errors.append(f"Задание №{num}: wrong {task['wrong']} ≠ {source['minus']}.")
        if int(task.get("blank", 0)) != source["blank"]:
            errors.append(f"Задание №{num}: blank {task.get('blank', 0)} ≠ {source['blank']}.")

    valid = len(errors) == 0
    return valid, errors


def validation_error_message(details: list[str]) -> str:
    if not details:
        return VALIDATION_ERROR_MESSAGE
    return VALIDATION_ERROR_MESSAGE + " " + "; ".join(details[:5])
