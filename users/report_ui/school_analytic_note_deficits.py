"""
Методический анализ предметных дефицитов для аналитической справки ГИА.

Агрегация по темам / разделам / КЭС (не перечень заданий).
Только ЕГЭ↔ФИПИ ЕГЭ и ОГЭ↔ФИПИ ОГЭ.
Полные списки заданий — только в technical_appendix.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from datetime import date as date_cls

from django.db.models import Exists, OuterRef, QuerySet

from analytics.engine.tokens import is_blank_token, is_success_token
from analytics.knowledge.service import get_task_knowledge
from exams.models import ExamResult, TaskResult
from organizations.models import School


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


def _task_results_for_latest_attempts(task_qs: QuerySet, exam_result_qs: QuerySet) -> QuerySet:
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


def build_methodological_deficits(
    school_id: int,
    exam_type: str,
    year: int | None = None,
) -> dict[str, Any]:
    et = (exam_type or "").strip().lower()
    if et not in {"ege", "oge"}:
        et = "ege"
    exam_label = "ЕГЭ" if et == "ege" else "ОГЭ"

    subjects = list(
        ExamResult.objects.filter(student__school_id=school_id, exam__exam_type=et)
        .filter(**({"exam__year": year} if year else {}))
        .values_list("exam__subject", flat=True)
        .distinct()
        .order_by("exam__subject")
    )

    school = School.objects.select_related("district", "district__ministry").filter(id=school_id).first()
    district_id = school.district_id if school else None
    ministry_id = school.district.ministry_id if school and school.district_id else None

    subject_blocks: list[dict[str, Any]] = []
    all_topics: list[dict[str, Any]] = []
    appendix_tasks: list[dict[str, Any]] = []

    for subject_name in subjects:
        block = _analyze_subject(
            school_id=school_id,
            exam_type=et,
            year=year,
            subject_name=subject_name,
            district_id=district_id,
            ministry_id=ministry_id,
        )
        subject_blocks.append(block)
        if block.get("has_task_data"):
            all_topics.extend(block.get("topics") or [])
            appendix_tasks.extend(block.get("task_rows") or [])

    topics_ranked = sorted(
        all_topics,
        key=lambda r: (float(r.get("deficit_score") or 0), int(r.get("task_count") or 0)),
        reverse=True,
    )
    priority_topics = _build_priority_topics(topics_ranked[:10])
    class_analysis = _build_class_analysis(topics_ranked)
    correction_plan = _build_correction_plan(priority_topics)
    school_map = _build_school_deficit_map(topics_ranked)
    methodological_conclusion = _build_methodological_conclusion(
        exam_label=exam_label,
        topics=topics_ranked,
        priority=priority_topics,
        subject_blocks=subject_blocks,
    )
    aggregation_overview = _build_aggregation_overview(subject_blocks, topics_ranked)

    return {
        "exam_type": et,
        "year": year,
        "has_any_task_data": any(b.get("has_task_data") for b in subject_blocks),
        "methodology_note": (
            f"Анализ выполнен по официальным спецификациям и кодификаторам ФИПИ для {exam_label}; "
            f"задания объединены по темам, разделам и КЭС. Полные перечни заданий вынесены в приложение."
        ),
        "aggregation_overview": aggregation_overview,
        "subject_blocks": subject_blocks,
        "topics": topics_ranked,
        "priority_topics": priority_topics,
        "class_analysis": class_analysis[:12],
        "recommendations_by_topic": _build_topic_recommendations(priority_topics),
        "correction_plan": correction_plan,
        "school_deficit_map": school_map[:20],
        "methodological_conclusion": methodological_conclusion,
        # совместимость со старым UI
        "deficit_map": topics_ranked,
        "technical_appendix": {
            "note": "Техническое приложение: полные списки заданий, КЭС и процентов выполнения.",
            "task_rows": appendix_tasks,
        },
    }


def _analyze_subject(
    *,
    school_id: int,
    exam_type: str,
    year: int | None,
    subject_name: str,
    district_id: int | None,
    ministry_id: int | None,
) -> dict[str, Any]:
    task_stats = _aggregate_school_tasks(school_id, exam_type, year, subject_name)
    if not task_stats:
        return {
            "subject": subject_name,
            "has_task_data": False,
            "message": (
                f"По предмету «{subject_name}» предметный анализ по КЭС и темам невозможен: "
                f"отсутствуют данные выполнения заданий КИМ."
            ),
            "topics": [],
            "sections": [],
            "analysis_text": "",
            "task_rows": [],
            "school_task_avg": None,
        }

    school_avg = round(sum(r["success_rate"] for r in task_stats) / len(task_stats), 1)
    district_rates = _aggregate_scope_rates(
        exam_type=exam_type,
        year=year,
        subject_name=subject_name,
        scope={"student__school__district_id": district_id} if district_id else None,
    )
    region_rates = _aggregate_scope_rates(
        exam_type=exam_type,
        year=year,
        subject_name=subject_name,
        scope={"student__school__district__ministry_id": ministry_id} if ministry_id else None,
    )

    enriched: list[dict[str, Any]] = []
    for row in task_stats:
        meta = _fipi_meta(subject_name, int(row["task_number"]), exam_type)
        success = float(row["success_rate"])
        district_rate = district_rates.get(int(row["task_number"]))
        region_rate = region_rates.get(int(row["task_number"]))
        enriched.append(
            {
                "subject": subject_name,
                "task_number": int(row["task_number"]),
                "success_rate": success,
                "total": int(row["total"]),
                "correct": int(row["correct"]),
                "wrong": int(row["wrong"]),
                "blank": int(row["blank"]),
                "avg_primary": row.get("avg_primary"),
                "topic": meta.get("topic") or "",
                "topic_short": meta.get("topic_short") or "",
                "grade_label": meta.get("grade_label") or "—",
                "grades": meta.get("grades") or [],
                "spec_section": meta.get("section") or "",
                "codifier_section": meta.get("subsection") or meta.get("section") or "",
                "kes": meta.get("kes") or "",
                "kt": meta.get("kt") or "",
                "kt_name": meta.get("kt_name") or "",
                "max_score": meta.get("max_score"),
                "difficulty": meta.get("difficulty") or _difficulty_from_rate(success),
                "school_avg_delta": round(success - school_avg, 1),
                "district_delta": round(success - district_rate, 1) if district_rate is not None else None,
                "region_delta": round(success - region_rate, 1) if region_rate is not None else None,
                "catalog_ok": bool(meta.get("catalog_ok")),
            }
        )

    topics = _aggregate_topics(subject_name, enriched, school_avg)
    sections = _aggregate_sections(subject_name, enriched)
    analysis_text = _subject_analysis_text(subject_name, topics, sections, school_avg)

    return {
        "subject": subject_name,
        "has_task_data": True,
        "message": "",
        "school_task_avg": school_avg,
        "topics": topics,
        "sections": sections,
        "analysis_text": analysis_text,
        "task_rows": enriched,
        # совместимость
        "hard_topics": topics[:5],
        "deficit_rows": [],
        "loss_tasks": [],
        "min_success_tasks": [],
        "risk_tasks": [],
    }


def _aggregation_key(row: dict[str, Any]) -> tuple[str, str]:
    """Ключ объединения: тема → КЭС → раздел спецификации → раздел кодификатора."""
    topic = (row.get("topic_short") or row.get("topic") or "").strip()
    kes = (row.get("kes") or "").strip()
    section = (row.get("spec_section") or "").strip()
    codifier = (row.get("codifier_section") or "").strip()
    if topic:
        return "topic", topic
    if kes and kes != "—":
        return "kes", kes
    if section and section != "—":
        return "section", section
    if codifier and codifier != "—":
        return "codifier", codifier
    return "task", f"Задание №{row.get('task_number')}"


def _aggregate_topics(subject: str, rows: list[dict[str, Any]], school_avg: float) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        kind, key = _aggregation_key(row)
        bucket = buckets.setdefault(
            (kind, key),
            {
                "agg_kind": kind,
                "topic": key,
                "subject": subject,
                "tasks": [],
                "success_sum": 0.0,
                "n": 0,
                "grades": set(),
                "kes_set": set(),
                "sections": set(),
                "codifiers": set(),
                "wrong_sum": 0,
                "total_answers": 0,
            },
        )
        bucket["tasks"].append(int(row["task_number"]))
        bucket["success_sum"] += float(row["success_rate"])
        bucket["n"] += 1
        bucket["wrong_sum"] += int(row.get("wrong") or 0) + int(row.get("blank") or 0)
        bucket["total_answers"] += int(row.get("total") or 0)
        for g in row.get("grades") or []:
            bucket["grades"].add(int(g))
        if row.get("kes"):
            bucket["kes_set"].add(row["kes"])
        if row.get("spec_section"):
            bucket["sections"].add(row["spec_section"])
        if row.get("codifier_section"):
            bucket["codifiers"].add(row["codifier_section"])

    out: list[dict[str, Any]] = []
    for (_kind, _key), b in buckets.items():
        avg = round(b["success_sum"] / b["n"], 1) if b["n"] else 0.0
        risk_level, risk_label = _risk_from_success(avg)
        tasks = sorted(set(b["tasks"]))
        grades = sorted(b["grades"])
        importance = _topic_importance(len(tasks), avg, b["wrong_sum"], b["total_answers"])
        influence = _topic_influence(avg, len(tasks), school_avg)
        title = b["topic"]
        section_label = next(iter(b["sections"]), "") or next(iter(b["codifiers"]), "") or title
        out.append(
            {
                "subject": subject,
                "topic": title,
                "topic_short": title,
                "agg_kind": b["agg_kind"],
                "section_label": section_label,
                "task_count": len(tasks),
                "tasks": tasks,
                "tasks_label": _tasks_label(tasks),
                "success_rate": avg,
                "deficit_score": round(100.0 - avg, 1),
                "risk_level": risk_level,
                "risk_label": risk_label,
                "deficit_degree": _deficit_degree(avg),
                "grade_label": _grades_label(grades),
                "grades": grades,
                "kes": ", ".join(sorted(b["kes_set"])) if b["kes_set"] else "—",
                "spec_section": ", ".join(sorted(b["sections"])[:2]) if b["sections"] else "—",
                "codifier_section": ", ".join(sorted(b["codifiers"])[:2]) if b["codifiers"] else "—",
                "importance": importance,
                "influence": influence,
                "analysis_text": _topic_analysis_text(
                    subject=subject,
                    topic=title,
                    tasks=tasks,
                    avg=avg,
                    risk_label=risk_label,
                    grade_label=_grades_label(grades),
                    importance=importance,
                    influence=influence,
                    section_label=section_label,
                ),
                "why_critical": _why_critical(avg, len(tasks), importance),
                "exam_impact": influence,
                "actions": _topic_actions(avg, {"topic_short": title, "topic": title, "grade_label": _grades_label(grades)}),
                "school_avg_delta": round(avg - school_avg, 1),
            }
        )
    return sorted(out, key=lambda r: (r["deficit_score"], r["task_count"]), reverse=True)


def _aggregate_sections(subject: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = (row.get("spec_section") or row.get("codifier_section") or row.get("topic_short") or "").strip()
        if not key:
            key = f"Задания без раздела ({subject})"
        bucket = buckets.setdefault(key, {"section": key, "tasks": [], "success_sum": 0.0, "n": 0})
        bucket["tasks"].append(int(row["task_number"]))
        bucket["success_sum"] += float(row["success_rate"])
        bucket["n"] += 1
    out = []
    for key, b in buckets.items():
        avg = round(b["success_sum"] / b["n"], 1) if b["n"] else 0.0
        risk_level, risk_label = _risk_from_success(avg)
        tasks = sorted(set(b["tasks"]))
        out.append(
            {
                "subject": subject,
                "section": key,
                "tasks": tasks,
                "tasks_label": _tasks_label(tasks),
                "task_count": len(tasks),
                "success_rate": avg,
                "risk_level": risk_level,
                "risk_label": risk_label,
                "text": (
                    f"Раздел «{key}» включает задания {_tasks_label(tasks)}. "
                    f"Средний процент выполнения {avg}%. Уровень риска: {risk_label}."
                ),
            }
        )
    return sorted(out, key=lambda r: r["success_rate"])


def _tasks_label(tasks: list[int]) -> str:
    if not tasks:
        return "—"
    if len(tasks) == 1:
        return str(tasks[0])
    if len(tasks) <= 8:
        return ", ".join(str(t) for t in tasks)
    head = ", ".join(str(t) for t in tasks[:6])
    return f"{head} и ещё {len(tasks) - 6}"


def _topic_importance(task_count: int, avg: float, wrong_sum: int, total_answers: int) -> str:
    share = (wrong_sum / total_answers) if total_answers else 0.0
    if task_count >= 3 and avg < 50:
        return "Высокая"
    if task_count >= 2 and avg < 60:
        return "Повышенная"
    if share >= 0.4 or avg < 55:
        return "Средняя"
    return "Локальная"


def _topic_influence(avg: float, task_count: int, school_avg: float) -> str:
    delta = school_avg - avg
    if avg < 40 and task_count >= 2:
        return "Существенно снижает итоговый результат за счёт серии низковыполненных заданий одной темы."
    if avg < 50:
        return "Оказывает выраженное негативное влияние на устойчивость результата по предмету."
    if delta >= 15:
        return "Тема выполняется заметно ниже среднего уровня школы и тянет вниз общий профиль."
    if avg < 65:
        return "Умеренно влияет на итоговый результат; при сохранении тренда повышает вероятность пороговых потерь."
    return "Влияние на итоговый результат ограничено; достаточно планового закрепления."


def _topic_analysis_text(
    *,
    subject: str,
    topic: str,
    tasks: list[int],
    avg: float,
    risk_label: str,
    grade_label: str,
    importance: str,
    influence: str,
    section_label: str,
) -> str:
    section_bit = f" (раздел «{section_label}»)" if section_label and section_label != topic else ""
    return (
        f"По предмету «{subject}» тема «{topic}»{section_bit} объединяет задания {_tasks_label(tasks)} "
        f"({len(tasks)} шт.). Средний процент выполнения {avg}%, риск — {risk_label}. "
        f"Класс изучения по справочнику ФИПИ: {grade_label}. "
        f"Важность темы для сдачи экзамена: {importance}. {influence}"
    )


def _why_critical(avg: float, task_count: int, importance: str) -> str:
    if avg < 30:
        return (
            f"Критичность обусловлена крайне низким средним выполнением ({avg}%) "
            f"по группе из {task_count} заданий одной темы."
        )
    if avg < 45:
        return (
            f"Тема входит в зону высокого риска: средний процент выполнения {avg}% "
            f"при {task_count} связанных заданиях; важность — {importance.lower()}."
        )
    return (
        f"Тема приоритетна из-за сочетания пониженного выполнения ({avg}%) "
        f"и числа связанных заданий ({task_count})."
    )


def _subject_analysis_text(
    subject: str,
    topics: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    school_avg: float,
) -> str:
    weak = [t for t in topics if t["risk_level"] in {"critical", "high", "medium"}][:4]
    if not weak:
        return (
            f"По предмету «{subject}» выраженных тематических дефицитов не выявлено "
            f"(средний % выполнения заданий {school_avg}%)."
        )
    names = ", ".join(f"«{t['topic']}» ({t['success_rate']}%)" for t in weak)
    top_sections = ", ".join(f"«{s['section']}»" for s in sections[:3]) if sections else "—"
    return (
        f"По предмету «{subject}» основные затруднения сосредоточены в темах: {names}. "
        f"Агрегированные разделы с пониженным выполнением: {top_sections}. "
        f"Средний процент выполнения заданий по предмету — {school_avg}%."
    )


def _build_aggregation_overview(
    subject_blocks: list[dict[str, Any]],
    topics: list[dict[str, Any]],
) -> list[str]:
    lines = []
    with_data = [b for b in subject_blocks if b.get("has_task_data")]
    without = [b for b in subject_blocks if not b.get("has_task_data")]
    if with_data:
        lines.append(
            f"Данные по заданиям КИМ доступны по {len(with_data)} предметам; "
            f"задания объединены в {len(topics)} тематических групп."
        )
    for block in with_data:
        if block.get("analysis_text"):
            lines.append(block["analysis_text"])
        for section in (block.get("sections") or [])[:2]:
            if section.get("risk_level") in {"critical", "high", "medium"}:
                lines.append(section["text"])
    for block in without:
        lines.append(block.get("message") or "")
    return [x for x in lines if x][:16]


def _build_priority_topics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        out.append(
            {
                **row,
                "why_critical": row.get("why_critical"),
                "exam_impact": row.get("exam_impact") or row.get("influence"),
            }
        )
    return out


def _build_methodological_conclusion(
    *,
    exam_label: str,
    topics: list[dict[str, Any]],
    priority: list[dict[str, Any]],
    subject_blocks: list[dict[str, Any]],
) -> list[str]:
    if not topics:
        return [
            f"По {exam_label} методическое заключение по темам не сформировано: "
            f"недостаточно данных выполнения заданий КИМ."
        ]

    weak = [t for t in topics if t["risk_level"] in {"critical", "high"}]
    critical_tasks = sum(int(t.get("task_count") or 0) for t in weak)
    all_weak_tasks = sum(int(t.get("task_count") or 0) for t in topics if t["risk_level"] in {"critical", "high", "medium"})
    subjects = list(dict.fromkeys(t["subject"] for t in priority))[:5]
    sections = []
    for t in priority:
        if t.get("section_label"):
            sections.append(t["section_label"])
    section_names = ", ".join(list(dict.fromkeys(sections))[:5]) or "отдельных тематических группах"

    grade_counter: Counter[int] = Counter()
    for t in weak or priority:
        for g in t.get("grades") or []:
            grade_counter[int(g)] += int(t.get("task_count") or 1)
    dominant_grade = None
    grade_share = 0.0
    if grade_counter:
        dominant_grade, cnt = grade_counter.most_common(1)[0]
        total_g = sum(grade_counter.values()) or 1
        grade_share = round(100.0 * cnt / total_g, 0)

    lines = [
        (
            f"Основные предметные дефициты образовательной организации по {exam_label} "
            f"сосредоточены преимущественно в разделах: {section_names}."
        ),
        (
            f"Приоритетные предметы для методической коррекции: {', '.join(subjects)}."
            if subjects
            else "Приоритетные предметы по тематическим дефицитам не выделены."
        ),
    ]
    if dominant_grade is not None and grade_share >= 40:
        lines.append(
            f"Около {int(grade_share)}% выявленных проблемных тематических групп относятся к темам, "
            f"изучаемым в {dominant_grade} классе. Это свидетельствует о необходимости усиления "
            f"методической работы на этапе обучения в {dominant_grade} классе, а не только в выпускном классе."
        )
    if all_weak_tasks:
        share_critical = round(100.0 * critical_tasks / all_weak_tasks, 0) if all_weak_tasks else 0
        if share_critical >= 50:
            lines.append(
                f"Более {int(share_critical)}% заданий из проблемных тематических групп относятся "
                f"к зонам высокого/критического риска."
            )
    lines.append(
        "Наибольший ожидаемый эффект может быть достигнут за счёт коррекции рабочих программ "
        "по приоритетным темам и проведения адресной диагностики."
    )
    no_data = [b["subject"] for b in subject_blocks if not b.get("has_task_data")]
    if no_data:
        lines.append(
            "По предметам без данных выполнения заданий КИМ тематический анализ не проводился: "
            + ", ".join(no_data[:8])
            + ("…" if len(no_data) > 8 else "")
            + "."
        )
    return lines


def _build_class_analysis(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    seen = set()
    for row in rows:
        grades = row.get("grades") or []
        topic = row.get("topic") or ""
        if not topic:
            continue
        if not grades:
            key = (row.get("subject"), topic, "—")
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "subject": row.get("subject"),
                    "topic": topic,
                    "grade_label": "класс изучения в справочнике не указан",
                    "text": (
                        f"Тема «{topic}» ({row.get('subject')}): класс изучения в справочнике ФИПИ "
                        f"не указан; коррекцию следует планировать по рабочей программе."
                    ),
                }
            )
            continue
        primary = int(grades[0])
        key = (row.get("subject"), topic, primary)
        if key in seen:
            continue
        seen.add(key)
        if primary >= 10:
            focus = "необходимо усилить подготовку выпускников текущего года по данной теме."
        else:
            focus = f"коррекционная работа должна быть организована уже в {primary} классе."
        out.append(
            {
                "subject": row.get("subject"),
                "topic": topic,
                "grade_label": _grades_label(grades),
                "primary_grade": primary,
                "text": f"Тема «{topic}» изучается в {primary} классе. Следовательно, {focus}",
            }
        )
    return out


def _build_topic_recommendations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows[:8]:
        out.append(
            {
                "subject": row.get("subject"),
                "topic": row.get("topic"),
                "grade_label": row.get("grade_label"),
                "success_rate": row.get("success_rate"),
                "actions": (row.get("actions") or [])[:4],
            }
        )
    return out


def _build_correction_plan(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plan = []
    for row in rows[:10]:
        topic = row.get("topic") or "Тема"
        plan.append(
            {
                "topic": topic,
                "grade": row.get("grade_label") or "—",
                "subject": row.get("subject"),
                "reason": (
                    f"Среднее выполнение темы {row.get('success_rate')}% "
                    f"({row.get('task_count')} заданий: {row.get('tasks_label')}); {row.get('risk_label')}"
                ),
                "owner": "Руководитель МО / учитель-предметник",
                "deadline": "в течение ближайшей учебной четверти",
                "kpi": f"Рост среднего % выполнения по теме «{topic}» не менее чем на 10 п.п.",
                "expected": f"Снижение тематического дефицита и рост устойчивости результатов.",
            }
        )
    return plan


def _build_school_deficit_map(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for row in rows:
        if row.get("risk_level") not in {"critical", "high", "medium"}:
            continue
        grades = row.get("grades") or []
        primary = int(grades[0]) if grades else None
        items.append(
            {
                "grade": primary,
                "grade_label": row.get("grade_label") or "—",
                "subject": row.get("subject"),
                "topic": row.get("topic"),
                "success_rate": row.get("success_rate"),
                "task_count": row.get("task_count"),
                "risk_level": row.get("risk_level"),
                "risk_label": row.get("risk_label"),
            }
        )
    items.sort(
        key=lambda r: (
            r["grade"] is None,
            r["grade"] if r["grade"] is not None else 99,
            float(r.get("success_rate") or 100),
        )
    )
    return items


def _aggregate_school_tasks(
    school_id: int,
    exam_type: str,
    year: int | None,
    subject_name: str,
) -> list[dict[str, Any]]:
    exam_result_qs = ExamResult.objects.filter(
        student__school_id=school_id,
        exam__exam_type=exam_type,
        exam__subject=subject_name,
    )
    if year:
        exam_result_qs = exam_result_qs.filter(exam__year=year)
    qs = TaskResult.objects.filter(
        student__school_id=school_id,
        exam__exam_type=exam_type,
        exam__subject=subject_name,
    )
    if year:
        qs = qs.filter(exam__year=year)
    qs = _task_results_for_latest_attempts(qs, exam_result_qs)

    raw = list(qs.values("task_number", "value"))
    if not raw:
        raw = _tasks_from_masks(school_id, exam_type, year, subject_name)
    if not raw:
        return []

    agg: dict[int, dict[str, float | int]] = {}
    for row in raw:
        num = int(row["task_number"])
        value = row.get("value")
        bucket = agg.setdefault(
            num,
            {"total": 0, "correct": 0, "wrong": 0, "blank": 0, "score_sum": 0.0, "score_n": 0},
        )
        bucket["total"] += 1
        token = str(value or "").strip()
        if is_blank_token(token):
            bucket["blank"] += 1
        elif is_success_token(token):
            bucket["correct"] += 1
        else:
            bucket["wrong"] += 1
        if token.isdigit():
            bucket["score_sum"] += float(token)
            bucket["score_n"] += 1

    out = []
    for num in sorted(agg):
        b = agg[num]
        total = int(b["total"])
        correct = int(b["correct"])
        avg_primary = None
        if int(b["score_n"]):
            avg_primary = round(float(b["score_sum"]) / int(b["score_n"]), 2)
        out.append(
            {
                "task_number": num,
                "total": total,
                "correct": correct,
                "wrong": int(b["wrong"]),
                "blank": int(b["blank"]),
                "success_rate": round((correct / total) * 100, 1) if total else 0.0,
                "avg_primary": avg_primary,
            }
        )
    return out


def _tasks_from_masks(
    school_id: int,
    exam_type: str,
    year: int | None,
    subject_name: str,
) -> list[dict[str, Any]]:
    qs = ExamResult.objects.filter(
        student__school_id=school_id,
        exam__exam_type=exam_type,
        exam__subject=subject_name,
    ).only("short_answer_tasks", "long_answer_tasks")
    if year:
        qs = qs.filter(exam__year=year)
    qs = filter_latest_exam_results(qs)
    rows: list[dict[str, Any]] = []
    for er in qs:
        short_mask = er.short_answer_tasks or ""
        for idx, token in enumerate(short_mask, start=1):
            rows.append({"task_number": idx, "value": token})
        long_mask = (er.long_answer_tasks or "").strip()
        if not long_mask:
            continue
        if ":" in long_mask or ";" in long_mask:
            for part in long_mask.replace(",", ";").split(";"):
                part = part.strip()
                if not part:
                    continue
                if ":" in part:
                    left, right = part.split(":", 1)
                    if left.strip().isdigit():
                        rows.append({"task_number": int(left.strip()), "value": right.strip()})
        else:
            start = len(short_mask) + 1 if short_mask else 1
            for offset, token in enumerate(long_mask):
                rows.append({"task_number": start + offset, "value": token})
    return rows


def _aggregate_scope_rates(
    *,
    exam_type: str,
    year: int | None,
    subject_name: str,
    scope: dict | None,
) -> dict[int, float]:
    if not scope:
        return {}
    qs = TaskResult.objects.filter(exam__exam_type=exam_type, exam__subject=subject_name, **scope)
    if year:
        qs = qs.filter(exam__year=year)
    if not qs.exists():
        return {}
    by_task: dict[int, dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    for row in qs.values("task_number", "value").iterator(chunk_size=2000):
        num = int(row["task_number"])
        by_task[num]["total"] += 1
        if is_success_token(row["value"]):
            by_task[num]["correct"] += 1
    return {
        num: round((b["correct"] / b["total"]) * 100, 1) if b["total"] else 0.0
        for num, b in by_task.items()
    }


def _fipi_meta(subject_name: str, task_number: int, exam_type: str) -> dict[str, Any]:
    knowledge = get_task_knowledge(subject_name, task_number, exam_type)
    if knowledge is None:
        return {
            "catalog_ok": False,
            "topic": "",
            "topic_short": "",
            "section": "",
            "subsection": "",
            "kes": "",
            "kt": "",
            "kt_name": "",
            "grades": [],
            "grade_label": "—",
            "max_score": None,
            "difficulty": "",
        }

    grades = list(knowledge.fgos_classes or [])
    if knowledge.fgos_class_start and knowledge.fgos_class_start not in grades:
        grades = [knowledge.fgos_class_start] + grades
    topic = (knowledge.topic or "").strip()
    topic_short = _short_topic(topic)
    kes = (knowledge.fipi_content_code or "").strip()
    kt = (knowledge.skill or knowledge.requirement_code or "").strip()
    kt_name = (knowledge.skill_name or "").strip()
    if kt_name and len(kt_name) > 180:
        kt_name = topic_short or kt_name[:180]
    if not kt_name:
        kt_name = "—" if not kt else kt

    return {
        "catalog_ok": bool(topic),
        "topic": topic,
        "topic_short": topic_short or topic[:120],
        "section": (knowledge.section or "").strip(),
        "subsection": (knowledge.subsection or "").strip(),
        "kes": kes,
        "kt": kt,
        "kt_name": kt_name,
        "grades": grades,
        "grade_label": _grades_label(grades),
        "max_score": float(knowledge.max_score) if knowledge.max_score is not None else None,
        "difficulty": (knowledge.difficulty or "").strip(),
    }


def _short_topic(topic: str) -> str:
    import re

    text = (topic or "").strip()
    if not text:
        return ""
    chunks = re.split(r"\d+\s*кл(?:асс)?[.,:]?\s*", text, flags=re.IGNORECASE)
    candidates = [c.strip(" .;,—-") for c in chunks if c and len(c.strip(" .;,—-")) > 3]
    if candidates:
        cleaned = re.sub(r"^п\.\s*[\d.]+\.?\s*", "", candidates[-1], flags=re.IGNORECASE).strip()
        return cleaned[:160] if cleaned else candidates[-1][:160]
    return text[:160]


def _grades_label(grades: list[int]) -> str:
    if not grades:
        return "—"
    uniq = sorted({int(g) for g in grades if g})
    if not uniq:
        return "—"
    if len(uniq) == 1:
        return f"{uniq[0]} класс"
    return ", ".join(f"{g} класс" for g in uniq)


def _risk_from_success(success: float) -> tuple[str, str]:
    if success < 30:
        return "critical", "Критический риск"
    if success < 45:
        return "high", "Высокий риск"
    if success < 60:
        return "medium", "Средний риск"
    if success < 75:
        return "watch", "Мониторинг"
    return "low", "Низкий риск"


def _deficit_degree(success: float) -> str:
    if success < 30:
        return "Критический дефицит"
    if success < 45:
        return "Высокий дефицит"
    if success < 60:
        return "Средний дефицит"
    if success < 75:
        return "Умеренный дефицит"
    return "Дефицит не выражен"


def _difficulty_from_rate(success: float) -> str:
    if success < 40:
        return "повышенный"
    if success < 70:
        return "базовый"
    return "рабочий"


def _topic_actions(success: float, meta: dict[str, Any]) -> list[str]:
    topic = meta.get("topic_short") or meta.get("topic") or "выявленная тема"
    actions = [
        f"Провести тематическую диагностику по теме «{topic}».",
        f"Организовать повторение темы «{topic}».",
        f"Включить дополнительные задания по теме «{topic}».",
    ]
    if success < 45:
        actions.extend(
            [
                f"Увеличить количество практических работ по теме «{topic}».",
                f"Скорректировать рабочую программу в части темы «{topic}».",
                f"Провести заседание методического объединения по теме «{topic}».",
            ]
        )
    elif success < 60:
        actions.extend(
            [
                f"Изменить календарно-тематическое планирование с усилением темы «{topic}».",
                f"Провести заседание методического объединения по теме «{topic}».",
            ]
        )
    return actions
