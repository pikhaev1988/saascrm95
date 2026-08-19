"""
Презентационный слой предметной аналитической справки муниципалитета.

Только форматирование и группировка готовых полей payload.
Без SQL, пересчётов метрик и изменения источников данных.
"""

from __future__ import annotations

from datetime import date
from typing import Any


DOC_VERSION = "2.0"


def build_district_subject_note_presentation(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload or {}
    if not data.get("has_data"):
        return {
            "has_data": False,
            "message": data.get("message") or "Недостаточно данных для предметной справки.",
        }

    et = (data.get("exam_type") or "ege").lower()
    is_oge = et == "oge"
    exam_label = "ОГЭ" if is_oge else "ЕГЭ"
    avg_label = "Средняя оценка" if is_oge else "Средний балл"
    subject = str(data.get("subject") or "Предмет")
    year = data.get("year")
    formed = str(data.get("generated_at") or date.today().strftime("%d.%m.%Y"))
    district = str(data.get("district_name") or "Муниципалитет")

    total = int(data.get("total") or 0)
    participants = int(data.get("participants") or 0) or total
    avg_score = float(data.get("avg_score") or 0)
    pass_rate = float(data.get("pass_rate") or 0)
    quality_rate = data.get("quality_rate")
    high_count = data.get("high_count")
    republic_avg = data.get("republic_avg")
    avg_delta = data.get("avg_delta")
    subject_rank = data.get("subject_rank")
    subjects_total = data.get("subjects_total")

    school_rows_raw = list(data.get("school_rows") or [])
    task_rows_raw = list(data.get("task_rows") or [])
    schools_count = len(school_rows_raw)

    tasks = _tasks(task_rows_raw)
    by_success = sorted(tasks, key=lambda x: float(x["success_rate"]))
    critical = [t for t in tasks if t["success_rate"] < 30]
    weak = [t for t in tasks if t["success_rate"] < 50]
    strong = [t for t in tasks if t["success_rate"] >= 80]
    best = sorted(tasks, key=lambda x: (-float(x["success_rate"]), x["number"]))[:8]
    problem = sorted(weak, key=lambda x: (float(x["success_rate"]), x["number"]))[:10]

    topics = _topics(tasks)
    topic_strong = [t for t in topics if t["avg_success"] >= 70][:8]
    topic_weak = [t for t in topics if t["avg_success"] < 50][:10]

    deficits = _deficits(problem)
    strengths = _strengths(best, topic_strong)

    schools = _schools(school_rows_raw)
    republic_delta = (
        round(avg_score - float(republic_avg), 2) if republic_avg is not None else None
    )

    rank_value = "—"
    if subject_rank is not None:
        rank_value = (
            f"{subject_rank} из {subjects_total}"
            if subjects_total
            else str(subject_rank)
        )

    passport = [
        {"icon": "👤", "label": "Участники", "value": str(participants), "tone": "sky"},
        {"icon": "⌂", "label": "Образовательные организации", "value": str(schools_count), "tone": "sky"},
        {
            "icon": "Σ",
            "label": avg_label,
            "value": _num(avg_score),
            "tone": _tone_avg(avg_score, et),
        },
        {
            "icon": "%",
            "label": "Успеваемость",
            "value": f"{_num(pass_rate)}%",
            "tone": _tone_pct(pass_rate, 85, 70),
        },
        {
            "icon": "Q",
            "label": "Качество знаний",
            "value": f"{_num(quality_rate)}%" if quality_rate is not None else "—",
            "tone": _tone_pct(quality_rate, 40, 25) if quality_rate is not None else "sky",
        },
        {
            "icon": "★",
            "label": "Высокобалльники",
            "value": str(high_count) if high_count is not None else "—",
            "tone": "sky",
        },
        {
            "icon": "↔",
            "label": "Отклонение от республики",
            "value": _fmt_delta(republic_delta) if republic_delta is not None else "—",
            "tone": _delta_tone(republic_delta),
        },
        {
            "icon": "↗",
            "label": "Динамика",
            "value": _fmt_delta(avg_delta) if avg_delta is not None else "—",
            "tone": _delta_tone(avg_delta),
        },
        {
            "icon": "#",
            "label": "Место среди предметов района",
            "value": rank_value,
            "tone": "sky",
        },
    ]

    level = _prep_level(pass_rate, avg_score, et, weak_n=len(weak), strong_n=len(strong))
    resume = _resume(
        subject=subject,
        exam_label=exam_label,
        avg_label=avg_label,
        avg_score=avg_score,
        pass_rate=pass_rate,
        level=level,
        strong=strong,
        weak=weak,
        topic_strong=topic_strong,
        topic_weak=topic_weak,
        ai_insights=list(data.get("ai_insights") or data.get("insights") or []),
    )

    republic_pass_rate = data.get("republic_pass_rate")
    republic_quality_rate = data.get("republic_quality_rate")

    comparison = [
        {
            "indicator": avg_label,
            "municipality": _num(avg_score),
            "republic": _num(republic_avg) if republic_avg is not None else "—",
            "delta": _fmt_delta(republic_delta) if republic_delta is not None else "—",
            "tone": _delta_tone(republic_delta),
        },
        {
            "indicator": "Успеваемость, %",
            "municipality": _num(pass_rate),
            "republic": _num(republic_pass_rate) if republic_pass_rate is not None else "—",
            "delta": (
                _fmt_delta(round(pass_rate - float(republic_pass_rate), 2))
                if republic_pass_rate is not None
                else "—"
            ),
            "tone": _delta_tone(
                round(pass_rate - float(republic_pass_rate), 2) if republic_pass_rate is not None else None
            ),
        },
        {
            "indicator": "Качество знаний, %",
            "municipality": _num(quality_rate) if quality_rate is not None else "—",
            "republic": _num(republic_quality_rate) if republic_quality_rate is not None else "—",
            "delta": (
                _fmt_delta(round(float(quality_rate) - float(republic_quality_rate), 2))
                if quality_rate is not None and republic_quality_rate is not None
                else "—"
            ),
            "tone": _delta_tone(
                round(float(quality_rate) - float(republic_quality_rate), 2)
                if quality_rate is not None and republic_quality_rate is not None
                else None
            ),
        },
    ]

    recommendations = _recommendations(
        subject=subject,
        deficits=deficits,
        topic_weak=topic_weak,
        ai_recs=list(data.get("recommendations") or []),
    )
    practice = _practice(deficits=deficits, topic_weak=topic_weak, weak=weak)
    conclusion = _conclusion(
        subject=subject,
        level=level,
        avg_label=avg_label,
        avg_score=avg_score,
        pass_rate=pass_rate,
        strong=strong,
        weak=weak,
        topic_strong=topic_strong,
        topic_weak=topic_weak,
        ai_conclusions=list(data.get("conclusions") or []),
    )

    dist_bins = _task_distribution(tasks)

    return {
        "has_data": True,
        "doc_version": DOC_VERSION,
        "district": district,
        "subject": subject,
        "exam_label": exam_label,
        "exam_type": et,
        "year": year,
        "generated_at": formed,
        "avg_label": avg_label,
        "passport": passport,
        "level": level,
        "resume": resume,
        "tasks": tasks,
        "best_tasks": best,
        "problem_tasks": problem,
        "critical_tasks": critical,
        "topics": topics,
        "topic_strong": topic_strong,
        "topic_weak": topic_weak,
        "deficits": deficits,
        "strengths": strengths,
        "comparison": comparison,
        "schools": schools,
        "distribution": dist_bins,
        "recommendations": recommendations,
        "practice": practice,
        "conclusion": conclusion,
        "kpi": {
            "total": total,
            "participants": participants,
            "schools_count": schools_count,
            "avg_score": avg_score,
            "pass_rate": pass_rate,
            "quality_rate": quality_rate,
            "high_count": high_count,
            "tasks_count": len(tasks),
            "weak_count": len(weak),
            "strong_count": len(strong),
            "critical_count": len(critical),
        },
    }


def _tasks(rows: list[dict]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        rate = float(row.get("success_rate") or 0)
        num = int(row.get("task_number") or 0)
        out.append(
            {
                "number": num,
                "success_rate": rate,
                "max_score": row.get("max_score") if row.get("max_score") is not None else "—",
                "difficulty": row.get("difficulty") or _difficulty(rate),
                "topic": str(row.get("topic") or f"Задание №{num}"),
                "total": int(row.get("total") or 0),
                "plus": int(row.get("plus") or 0),
                "tone": "good" if rate >= 80 else ("warn" if rate >= 50 else ("risk" if rate >= 30 else "critical")),
                "bar": min(max(rate, 0), 100),
            }
        )
    return sorted(out, key=lambda x: x["number"])


def _topics(tasks: list[dict]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict]] = {}
    for t in tasks:
        buckets.setdefault(t["topic"], []).append(t)
    out = []
    for topic, items in buckets.items():
        rates = [float(i["success_rate"]) for i in items]
        avg = round(sum(rates) / len(rates), 1) if rates else 0.0
        out.append(
            {
                "topic": topic,
                "tasks": [f"№{i['number']}" for i in items],
                "tasks_count": len(items),
                "avg_success": avg,
                "tone": "good" if avg >= 70 else ("warn" if avg >= 50 else "risk"),
                "status": "усвоено" if avg >= 70 else ("требует усиления" if avg >= 50 else "дефицит"),
            }
        )
    return sorted(out, key=lambda x: float(x["avg_success"]))


def _deficits(problem: list[dict]) -> list[dict[str, Any]]:
    out = []
    for i, t in enumerate(problem[:10], start=1):
        rate = float(t["success_rate"])
        if rate < 30:
            risk, priority = "критический", "высокий"
        elif rate < 40:
            risk, priority = "высокий", "высокий"
        else:
            risk, priority = "средний", "средний"
        out.append(
            {
                "rank": i,
                "title": f"Низкая успешность задания №{t['number']}",
                "description": (
                    f"Тема «{t['topic']}»: выполнение { _num(rate) }%. "
                    f"Уровень сложности (по факту выполнения): {t['difficulty']}."
                ),
                "tasks": f"№{t['number']}",
                "risk": risk,
                "priority": priority,
                "success_rate": rate,
                "tone": t["tone"],
            }
        )
    return out


def _strengths(best: list[dict], topic_strong: list[dict]) -> list[dict[str, Any]]:
    out = []
    for t in topic_strong:
        out.append(
            {
                "title": t["topic"],
                "detail": f"Среднее выполнение { _num(t['avg_success']) }% · задания: {', '.join(t['tasks'][:6])}",
                "tone": "good",
            }
        )
    if not out:
        for t in best[:5]:
            out.append(
                {
                    "title": f"Задание №{t['number']}",
                    "detail": f"{t['topic']} · выполнение { _num(t['success_rate']) }%",
                    "tone": "good",
                }
            )
    return out[:8]


def _schools(rows: list[dict]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        avg = round(float(row.get("avg") or 0), 2)
        pr = float(row.get("pass_rate") or 0)
        qr = row.get("quality_rate")
        out.append(
            {
                "name": str(row.get("student__school__name") or "—"),
                "code": str(row.get("student__school__code") or "—"),
                "participants": int(row.get("participants") or 0),
                "avg": avg,
                "pass_rate": pr,
                "quality_rate": float(qr) if qr is not None else None,
                "pass_tone": "good" if pr >= 85 else ("risk" if pr < 70 else "warn"),
            }
        )
    return sorted(out, key=lambda x: (-float(x["avg"]), x["name"]))


def _task_distribution(tasks: list[dict]) -> list[dict[str, Any]]:
    bins = [
        ("0–29%", 0, 30),
        ("30–49%", 30, 50),
        ("50–69%", 50, 70),
        ("70–84%", 70, 85),
        ("85–100%", 85, 101),
    ]
    out = []
    total = len(tasks) or 1
    for label, lo, hi in bins:
        n = sum(1 for t in tasks if lo <= float(t["success_rate"]) < hi)
        pct = round(100.0 * n / total, 1) if tasks else 0.0
        out.append({"label": label, "value": n, "percent": pct, "bar": pct})
    return out


def _prep_level(pass_rate: float, avg: float, et: str, *, weak_n: int, strong_n: int) -> dict[str, str]:
    if pass_rate >= 90 and weak_n <= 2:
        return {"label": "высокий", "tone": "good", "icon": "◆"}
    if pass_rate >= 80 and weak_n <= 5:
        return {"label": "устойчивый", "tone": "good", "icon": "◆"}
    if pass_rate >= 70:
        return {"label": "средний", "tone": "warn", "icon": "◆"}
    if pass_rate >= 55:
        return {"label": "ниже среднего", "tone": "warn", "icon": "⚠"}
    return {"label": "требует усиления", "tone": "risk", "icon": "⚠"}


def _resume(
    *,
    subject: str,
    exam_label: str,
    avg_label: str,
    avg_score: float,
    pass_rate: float,
    level: dict,
    strong: list,
    weak: list,
    topic_strong: list,
    topic_weak: list,
    ai_insights: list,
) -> dict[str, list[str]]:
    level_txt = [
        f"Общий уровень подготовки по предмету «{subject}» ({exam_label}): {level['label']}.",
        f"{avg_label}: {_num(avg_score)}; успеваемость: {_num(pass_rate)}%.",
    ]
    achievements = []
    if strong:
        achievements.append(
            "Наиболее успешно выполняются задания: "
            + ", ".join(f"№{t['number']}" for t in strong[:5])
            + "."
        )
    if topic_strong:
        achievements.append(
            "Устойчивые темы: " + "; ".join(t["topic"] for t in topic_strong[:4]) + "."
        )
    if not achievements:
        achievements.append("Стабильные зоны зафиксированы на уровне отдельных заданий с высокой успешностью.")

    problems = []
    if weak:
        problems.append(
            "Основные затруднения по заданиям: "
            + ", ".join(f"№{t['number']} ({_num(t['success_rate'])}%)" for t in weak[:5])
            + "."
        )
    if topic_weak:
        problems.append(
            "Темы, требующие усиления: " + "; ".join(t["topic"] for t in topic_weak[:4]) + "."
        )
    if not problems:
        problems.append("Критических предметных дефицитов по порогу <50% не выявлено.")

    assessment = [
        f"Итоговая оценка предметной подготовки: {level['label']}.",
        f"Соотношение сильных и проблемных заданий: {len(strong)} / {len(weak)}.",
    ]
    # краткие факты из AI (если есть), без раздувания
    extra = [_clean(x) for x in ai_insights[:2] if str(x).strip()]
    if extra:
        assessment.extend(extra)

    return {
        "level": level_txt,
        "achievements": achievements[:4],
        "problems": problems[:4],
        "assessment": assessment[:4],
    }


def _recommendations(*, subject: str, deficits: list, topic_weak: list, ai_recs: list) -> list[dict[str, Any]]:
    if not deficits and not topic_weak and not ai_recs:
        return []

    deficit_link = deficits[0]["title"] if deficits else "предметные дефициты КИМ"
    topics = "; ".join(t["topic"] for t in topic_weak[:3]) if topic_weak else ""

    groups: list[dict[str, Any]] = []
    teacher_items = []
    if topics:
        teacher_items.append(
            {
                "text": f"Включить в текущее планирование отработку тем: {topics}.",
                "priority": "высокий",
                "effect": "рост выполнения проблемных заданий",
                "deficit": deficit_link,
            }
        )
    if deficits:
        teacher_items.append(
            {
                "text": "Проводить короткие диагностики по заданиям с успешностью ниже 50% и разбор типичных ошибок.",
                "priority": "высокий",
                "effect": "снижение доли критических дефицитов",
                "deficit": deficit_link,
            }
        )
    if teacher_items:
        groups.append({"audience": "Учитель-предметник", "items": teacher_items})

    if topics or deficits:
        groups.append(
            {
                "audience": "Руководитель МО / РМО",
                "items": [
                    {
                        "text": f"На заседании МО по предмету «{subject}» утвердить единый перечень заданий для межшкольной отработки.",
                        "priority": "высокий",
                        "effect": "синхронизация методических подходов",
                        "deficit": deficit_link,
                    },
                    {
                        "text": "Организовать взаимопосещение уроков и обмен успешными практиками по сильным темам.",
                        "priority": "средний",
                        "effect": "тиражирование сильных сторон",
                        "deficit": "карта сильных сторон",
                    },
                ],
            }
        )
        groups.append(
            {
                "audience": "Администрация школы",
                "items": [
                    {
                        "text": "Включить предмет в внутришкольный мониторинг с контролем динамики по проблемным заданиям.",
                        "priority": "средний",
                        "effect": "управляемость качества подготовки",
                        "deficit": deficit_link,
                    },
                    {
                        "text": "Обеспечить часы консультаций и ресурсную поддержку групп риска по предмету.",
                        "priority": "высокий",
                        "effect": "рост успеваемости",
                        "deficit": deficit_link,
                    },
                ],
            }
        )
        groups.append(
            {
                "audience": "Муниципальный методический центр",
                "items": [
                    {
                        "text": f"Провести муниципальный семинар/воркшоп по дефицитам КИМ предмета «{subject}».",
                        "priority": "высокий",
                        "effect": "методическая поддержка сети ОО",
                        "deficit": deficit_link,
                    },
                    {
                        "text": "Сформировать банк типовых разборов проблемных заданий и критериев оценивания.",
                        "priority": "средний",
                        "effect": "единые стандарты подготовки",
                        "deficit": deficit_link,
                    },
                ],
            }
        )

    extra = [_clean(x) for x in ai_recs[:3] if str(x).strip()]
    if extra:
        if not groups or groups[-1].get("audience") != "Муниципальный методический центр":
            groups.append({"audience": "Муниципальный методический центр", "items": []})
        for text in extra:
            groups[-1]["items"].append(
                {
                    "text": text,
                    "priority": "средний",
                    "effect": "уточнение адресных мер",
                    "deficit": deficit_link,
                }
            )
    return [g for g in groups if g.get("items")]


def _practice(*, deficits: list, topic_weak: list, weak: list) -> dict[str, list[str]]:
    if not deficits and not topic_weak and not weak:
        return {"process": [], "diagnostics": [], "revision": [], "tasks": []}

    topics = [t["topic"] for t in topic_weak[:4]]
    tasks = [f"№{t['number']}" for t in weak[:6]]
    out = {
        "process": [],
        "diagnostics": [],
        "revision": [],
        "tasks": [],
    }
    if topics:
        out["process"].append(f"Перераспределить учебное время в пользу тем: {'; '.join(topics)}.")
        out["process"].append("Ввести еженедельные мини-практикумы по заданиям с низкой успешностью.")
    if tasks:
        out["diagnostics"].append(f"Использовать срезовые работы, включающие задания {', '.join(tasks)}.")
        out["diagnostics"].append(
            "Фиксировать динамику выполнения по каждому дефицитному заданию не реже 1 раза в месяц."
        )
        out["tasks"].append(
            f"Сформировать тренажёр по заданиям {', '.join(tasks)} с обязательным самоанализом ошибок."
        )
        out["tasks"].append("Чередовать форматы: устный разбор, письменный тренинг, взаимопроверка по критериям.")
    if topics or tasks:
        out["revision"].append(
            "Построить спираль повторения: базовые умения → комбинированные задания → задания повышенного уровня."
        )
        out["revision"].append("В повторение включать разбор эталонных решений и критериев оценивания.")
    return out


def _conclusion(
    *,
    subject: str,
    level: dict,
    avg_label: str,
    avg_score: float,
    pass_rate: float,
    strong: list,
    weak: list,
    topic_strong: list,
    topic_weak: list,
    ai_conclusions: list,
) -> list[str]:
    items = [
        f"По предмету «{subject}» уровень подготовки оценивается как «{level['label']}».",
        f"{avg_label}: {_num(avg_score)}; успеваемость: {_num(pass_rate)}%.",
    ]
    if topic_strong:
        items.append("Сильные стороны: " + "; ".join(t["topic"] for t in topic_strong[:3]) + ".")
    elif strong:
        items.append("Сильные стороны: задания " + ", ".join(f"№{t['number']}" for t in strong[:4]) + ".")
    if topic_weak:
        items.append("Ключевые проблемы: " + "; ".join(t["topic"] for t in topic_weak[:3]) + ".")
    elif weak:
        items.append("Ключевые проблемы: задания " + ", ".join(f"№{t['number']}" for t in weak[:4]) + ".")
    if topic_weak or weak:
        items.append(
            "Основные направления развития: адресная отработка дефицитов КИМ, "
            "усиление диагностики и методическая синхронизация на уровне МО."
        )
    for line in ai_conclusions[:2]:
        cleaned = _clean(line)
        if cleaned and cleaned not in items:
            items.append(cleaned)
    return items[:8]


def _difficulty(rate: float) -> str:
    if rate < 50:
        return "повышенный"
    if rate < 80:
        return "базовый"
    return "рабочий"


def _clean(text: Any) -> str:
    return " ".join(str(text or "").split())


def _num(v) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return f"{f:.2f}".rstrip("0").rstrip(".")


def _fmt_delta(v) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if f > 0:
        return f"+{_num(f)}"
    return _num(f)


def _delta_tone(v) -> str:
    if v is None:
        return "neutral"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "neutral"
    if f > 0:
        return "good"
    if f < 0:
        return "risk"
    return "neutral"


def _tone_avg(v, et: str) -> str:
    try:
        f = float(v or 0)
    except (TypeError, ValueError):
        return "sky"
    if et == "oge":
        if f >= 4:
            return "good"
        if f < 3.5:
            return "risk"
        return "warn"
    if f >= 60:
        return "good"
    if f < 45:
        return "risk"
    return "warn"


def _tone_pct(v, high: float, mid: float) -> str:
    if v is None:
        return "sky"
    try:
        f = float(v or 0)
    except (TypeError, ValueError):
        return "sky"
    if f >= high:
        return "good"
    if f < mid:
        return "risk"
    return "warn"
