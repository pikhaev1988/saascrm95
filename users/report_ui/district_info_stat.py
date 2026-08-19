"""
Презентационный слой информационно-статистического отчёта муниципалитета.

Только форматирование и ранжирование готовых полей payload.
Без SQL, пересчётов метрик и изменения источников данных.
"""

from __future__ import annotations

from typing import Any


DOC_VERSION = "2.0"


def build_district_info_stat_presentation(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload or {}
    if not data.get("has_data"):
        return {
            "has_data": False,
            "message": data.get("message") or "Недостаточно данных для формирования отчёта.",
        }

    et = (data.get("exam_type") or "ege").lower()
    is_oge = et == "oge"
    exam_label = "ОГЭ" if is_oge else "ЕГЭ"
    avg_label = "Средняя оценка" if is_oge else "Средний балл"
    district = str(data.get("district_name") or "Муниципалитет")
    year = data.get("year")
    formed = str(data.get("generated_at") or "—")

    participants = int(data.get("participants") or 0)
    schools_count = int(data.get("schools_count") or 0)
    avg_score = float(data.get("avg_score") or 0)
    quality_rate = float(data.get("quality_rate") or 0)
    pass_rate = float(data.get("pass_rate") or 0)
    high_count = int(data.get("high_count") or 0)
    failed_count = int(data.get("failed_count") or 0)
    total = int(data.get("total") or 0)
    avg_delta = data.get("avg_delta")
    republic_avg = data.get("republic_avg")
    republic_delta = (
        round(avg_score - float(republic_avg), 2) if republic_avg is not None else None
    )

    subject_rows = list(data.get("subject_rows") or [])
    school_rows = list(data.get("school_rows") or [])
    subjects_count = len(subject_rows)

    subjects = _subjects(subject_rows, avg_score=avg_score, republic_avg=republic_avg)
    schools = _schools(school_rows)
    schools_by_avg = sorted(schools, key=lambda x: (-float(x["avg"]), x["name"]))
    top10 = schools_by_avg[:10]
    bottom10 = list(reversed(schools_by_avg[-10:])) if schools_by_avg else []

    by_avg = sorted(subjects, key=lambda x: (-float(x["avg"]), x["name"]))
    by_quality = sorted(subjects, key=lambda x: (-float(x["quality_rate"]), x["name"]))
    by_mass = sorted(subjects, key=lambda x: (-int(x["participants"]), x["name"]))

    dist = _distribution(data.get("distribution") or [])
    dist_total = sum(r["value"] for r in dist) or 0

    prev_avg = data.get("prev_avg")
    prev_pass_rate = data.get("prev_pass_rate")
    prev_quality_rate = data.get("prev_quality_rate")
    prev_participants = data.get("prev_participants")
    change_rate = None
    if avg_delta is not None and prev_avg is None:
        prev_avg = round(avg_score - float(avg_delta), 2)
    if avg_delta is not None and prev_avg:
        change_rate = round((float(avg_delta) / float(prev_avg)) * 100, 1)

    def _dyn_delta(curr, prev):
        if curr is None or prev is None:
            return None
        return round(float(curr) - float(prev), 2)

    def _dyn_rate(curr, prev):
        if curr is None or prev is None or not float(prev):
            return None
        return round(((float(curr) - float(prev)) / float(prev)) * 100, 1)

    pass_delta = _dyn_delta(pass_rate, prev_pass_rate)
    quality_delta = _dyn_delta(quality_rate, prev_quality_rate)
    part_delta = _dyn_delta(participants, prev_participants)

    dynamics_rows = [
        {
            "indicator": avg_label,
            "current": _num(avg_score),
            "previous": _num(prev_avg) if prev_avg is not None else "—",
            "delta": _fmt_delta(avg_delta),
            "rate": f"{_fmt_delta(change_rate)}%" if change_rate is not None else "—",
        },
        {
            "indicator": "Участники",
            "current": str(participants),
            "previous": str(prev_participants) if prev_participants is not None else "—",
            "delta": _fmt_delta(part_delta),
            "rate": f"{_fmt_delta(_dyn_rate(participants, prev_participants))}%"
            if prev_participants
            else "—",
        },
        {
            "indicator": "Успеваемость, %",
            "current": _num(pass_rate),
            "previous": _num(prev_pass_rate) if prev_pass_rate is not None else "—",
            "delta": _fmt_delta(pass_delta),
            "rate": f"{_fmt_delta(_dyn_rate(pass_rate, prev_pass_rate))}%"
            if prev_pass_rate
            else "—",
        },
        {
            "indicator": "Качество знаний, %",
            "current": _num(quality_rate),
            "previous": _num(prev_quality_rate) if prev_quality_rate is not None else "—",
            "delta": _fmt_delta(quality_delta),
            "rate": f"{_fmt_delta(_dyn_rate(quality_rate, prev_quality_rate))}%"
            if prev_quality_rate
            else "—",
        },
    ]

    republic_pass_rate = data.get("republic_pass_rate")
    republic_quality_rate = data.get("republic_quality_rate")
    republic_high_count = data.get("republic_high_count")
    republic_failed_count = data.get("republic_failed_count")

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
            "delta": _fmt_delta(_dyn_delta(pass_rate, republic_pass_rate))
            if republic_pass_rate is not None
            else "—",
            "tone": _delta_tone(_dyn_delta(pass_rate, republic_pass_rate)),
        },
        {
            "indicator": "Качество знаний, %",
            "municipality": _num(quality_rate),
            "republic": _num(republic_quality_rate) if republic_quality_rate is not None else "—",
            "delta": _fmt_delta(_dyn_delta(quality_rate, republic_quality_rate))
            if republic_quality_rate is not None
            else "—",
            "tone": _delta_tone(_dyn_delta(quality_rate, republic_quality_rate)),
        },
        {
            "indicator": "Высокобалльники",
            "municipality": str(high_count),
            "republic": str(republic_high_count) if republic_high_count is not None else "—",
            "delta": "—",
            "tone": "neutral",
        },
        {
            "indicator": "Неудовлетворительные",
            "municipality": str(failed_count),
            "republic": str(republic_failed_count) if republic_failed_count is not None else "—",
            "delta": "—",
            "tone": "neutral",
        },
    ]

    passport = [
        {
            "icon": "👤",
            "label": "Участники",
            "value": str(participants),
            "tone": "sky",
            "hint": "уникальный контингент среза",
        },
        {
            "icon": "⌂",
            "label": "Образовательные организации",
            "value": str(schools_count),
            "tone": "sky",
            "hint": "ОО в отчётном срезе",
        },
        {
            "icon": "▣",
            "label": "Предметы",
            "value": str(subjects_count),
            "tone": "sky",
            "hint": "позиции среза",
        },
        {
            "icon": "Σ",
            "label": avg_label,
            "value": _num(avg_score),
            "tone": _tone_avg(avg_score, et),
            "hint": "муниципальный средний",
        },
        {
            "icon": "Q",
            "label": "Качество знаний",
            "value": f"{_num(quality_rate)}%",
            "tone": _tone_pct(quality_rate, 40, 25),
            "hint": "доля высоких результатов",
        },
        {
            "icon": "%",
            "label": "Успеваемость",
            "value": f"{_num(pass_rate)}%",
            "tone": _tone_pct(pass_rate, 85, 70),
            "hint": "доля преодолевших порог",
        },
        {
            "icon": "★",
            "label": "Высокобалльники",
            "value": str(high_count),
            "tone": "sky",
            "hint": "высокие результаты",
        },
        {
            "icon": "↗",
            "label": "Динамика",
            "value": _fmt_delta(avg_delta),
            "tone": _delta_tone(avg_delta),
            "hint": "к предыдущему году",
        },
        {
            "icon": "↔",
            "label": "Отклонение от республики",
            "value": _fmt_delta(republic_delta) if republic_delta is not None else "—",
            "tone": _delta_tone(republic_delta),
            "hint": "к республиканскому среднему",
        },
    ]

    notes = {
        "passport": (
            f"В отчётном периоде {year or '—'} по {exam_label} зафиксировано "
            f"{participants} участников в {schools_count} ОО по {subjects_count} предметам."
        ),
        "general": (
            f"Совокупность результатов: {total}. {avg_label}: {_num(avg_score)}; "
            f"качество знаний: {_num(quality_rate)}%; успеваемость: {_num(pass_rate)}%."
        ),
        "subjects": (
            f"Предметная статистика охватывает {subjects_count} позиций. "
            "Показатели приведены без интерпретации причин."
        ),
        "schools": (
            f"В рейтинге образовательных организаций — {schools_count} ОО. "
            "Ранжирование выполнено по среднему результату."
        ),
        "distribution": (
            f"Структура результатов построена по {len(dist)} диапазонам "
            f"на основе {dist_total} записей результатов."
        ),
        "comparison": (
            f"Сравнение с республикой рассчитано по среднему, успеваемости и качеству "
            f"на основе загруженных протоколов ({avg_label})."
            if republic_avg is not None
            else "Республиканский ориентир в загруженном срезе отсутствует."
        ),
        "dynamics": (
            f"Динамика среднего результата к предыдущему году: {_fmt_delta(avg_delta)}."
            if avg_delta is not None
            else "Данные предыдущего года для расчёта динамики среднего результата отсутствуют."
        ),
    }

    conclusions = _conclusions(
        exam_label=exam_label,
        year=year,
        participants=participants,
        schools_count=schools_count,
        subjects_count=subjects_count,
        avg_label=avg_label,
        avg_score=avg_score,
        quality_rate=quality_rate,
        pass_rate=pass_rate,
        high_count=high_count,
        failed_count=failed_count,
        avg_delta=avg_delta,
        republic_delta=republic_delta,
        by_avg=by_avg,
        by_mass=by_mass,
        top10=top10,
        bottom10=bottom10,
    )

    return {
        "has_data": True,
        "doc_version": DOC_VERSION,
        "district": district,
        "exam_label": exam_label,
        "exam_type": et,
        "year": year,
        "generated_at": formed,
        "avg_label": avg_label,
        "passport": passport,
        "notes": notes,
        "subjects": subjects,
        "rank_avg": [{"rank": i, **r} for i, r in enumerate(by_avg, start=1)],
        "rank_quality": [{"rank": i, **r} for i, r in enumerate(by_quality, start=1)],
        "rank_mass": [{"rank": i, **r} for i, r in enumerate(by_mass, start=1)],
        "schools": schools,
        "top10": [{"rank": i, **r} for i, r in enumerate(top10, start=1)],
        "bottom10": [{"rank": i, **r} for i, r in enumerate(bottom10, start=1)],
        "distribution": dist,
        "distribution_total": dist_total,
        "comparison": comparison,
        "dynamics": dynamics_rows,
        "conclusions": conclusions,
        "kpi_summary": {
            "participants": participants,
            "schools_count": schools_count,
            "subjects_count": subjects_count,
            "avg_score": avg_score,
            "quality_rate": quality_rate,
            "pass_rate": pass_rate,
            "high_count": high_count,
            "failed_count": failed_count,
            "total": total,
        },
    }


def _subjects(rows: list[dict], *, avg_score: float, republic_avg) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        avg = round(float(row.get("avg") or 0), 2)
        participants = int(row.get("participants") or 0)
        quality = float(row.get("quality_rate") or 0)
        pass_rate = float(row.get("pass_rate") or 0)
        high = int(row.get("high") or 0)
        mun_delta = round(avg - float(avg_score), 2)
        rep_delta = round(avg - float(republic_avg), 2) if republic_avg is not None else None
        out.append(
            {
                "name": str(row.get("exam__subject") or "—"),
                "participants": participants,
                "avg": avg,
                "quality_rate": quality,
                "pass_rate": pass_rate,
                "high": high,
                "mun_delta": mun_delta,
                "rep_delta": rep_delta,
                "avg_tone": "good" if mun_delta > 0 else ("risk" if mun_delta < 0 else "neutral"),
            }
        )
    return out


def _schools(rows: list[dict]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        avg = round(float(row.get("avg") or 0), 2)
        pass_rate = float(row.get("pass_rate") or 0)
        out.append(
            {
                "name": str(row.get("student__school__name") or "—"),
                "code": str(row.get("student__school__code") or "—"),
                "participants": int(row.get("participants") or 0),
                "avg": avg,
                "pass_rate": pass_rate,
                "pass_tone": "good" if pass_rate >= 85 else ("risk" if pass_rate < 70 else "warn"),
            }
        )
    return out


def _distribution(raw) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pairs: list[tuple[str, int]] = []
    for item in raw or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            pairs.append((str(item[0]), int(item[1] or 0)))
        elif isinstance(item, dict):
            pairs.append((str(item.get("label") or item.get("name") or "—"), int(item.get("value") or 0)))
    total = sum(v for _, v in pairs) or 0
    max_v = max((v for _, v in pairs), default=0) or 1
    for label, value in pairs:
        pct = round((value / total) * 100, 1) if total else 0.0
        rows.append(
            {
                "label": label,
                "value": value,
                "percent": pct,
                "bar": round((value / max_v) * 100, 1) if max_v else 0.0,
            }
        )
    return rows


def _conclusions(
    *,
    exam_label: str,
    year,
    participants: int,
    schools_count: int,
    subjects_count: int,
    avg_label: str,
    avg_score: float,
    quality_rate: float,
    pass_rate: float,
    high_count: int,
    failed_count: int,
    avg_delta,
    republic_delta,
    by_avg: list[dict],
    by_mass: list[dict],
    top10: list[dict],
    bottom10: list[dict],
) -> list[str]:
    items: list[str] = [
        f"По итогам {exam_label} {year or '—'} в муниципалитете {participants} участников, {schools_count} ОО, {subjects_count} предметов.",
        f"{avg_label}: {_num(avg_score)}; качество знаний: {_num(quality_rate)}%; успеваемость: {_num(pass_rate)}%.",
        f"Высокобалльники: {high_count}; неудовлетворительные результаты: {failed_count}.",
    ]
    if avg_delta is not None:
        items.append(f"Динамика {avg_label.lower()} к предыдущему году: {_fmt_delta(avg_delta)}.")
    if republic_delta is not None:
        items.append(f"Отклонение от республиканского среднего: {_fmt_delta(republic_delta)}.")
    if by_avg:
        items.append(
            f"Лидер по среднему результату среди предметов: {by_avg[0]['name']} ({_num(by_avg[0]['avg'])})."
        )
        items.append(
            f"Минимальный средний результат среди предметов: {by_avg[-1]['name']} ({_num(by_avg[-1]['avg'])})."
        )
    if by_mass:
        items.append(
            f"Наиболее массовый предмет: {by_mass[0]['name']} ({by_mass[0]['participants']} участников)."
        )
    if top10:
        items.append(f"ТОП-1 ОО по среднему результату: {top10[0]['name']} ({_num(top10[0]['avg'])}).")
    if bottom10:
        items.append(
            f"ОО с наименьшим средним результатом: {bottom10[0]['name']} ({_num(bottom10[0]['avg'])})."
        )
    return items[:10]


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
    try:
        f = float(v or 0)
    except (TypeError, ValueError):
        return "sky"
    if f >= high:
        return "good"
    if f < mid:
        return "risk"
    return "warn"
