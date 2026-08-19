"""
Презентационный слой информационно-статистического отчёта школы.

Только UI поверх готового info_stat_payload. Без SQL и пересчётов.
"""

from __future__ import annotations

import json
from typing import Any


def build_info_stat_presentation(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload or {}
    if not data.get("has_data"):
        return {"has_data": False, "message": data.get("message") or "Недостаточно данных."}

    et = (data.get("exam_type") or "ege").lower()
    is_oge = et == "oge"
    exam_label = "ОГЭ" if is_oge else "ЕГЭ"
    avg_label = "Средняя оценка" if is_oge else "Средний балл"

    total = int(data.get("total") or 0)
    participants = int(data.get("participants") or 0) or total
    avg = float(data.get("avg_score") or 0)
    quality = float(data.get("quality_rate") or 0)
    pass_rate = float(data.get("pass_rate") or 0)

    dist_rows = _dist_rows(data.get("distribution") or [])
    dist_total = sum(r["value"] for r in dist_rows) or 0

    subjects = []
    max_avg = max((float(r.get("avg") or 0) for r in (data.get("subject_rows") or [])), default=1) or 1
    for row in data.get("subject_rows") or []:
        pr = float(row.get("pass_rate") or 0)
        av = float(row.get("avg") or 0)
        tone = _tone(pr, av, is_oge=is_oge)
        subjects.append(
            {
                "name": row.get("exam__subject") or "Предмет",
                "participants": int(row.get("participants") or 0),
                "avg": round(av, 2),
                "quality_rate": float(row.get("quality_rate") or 0),
                "pass_rate": pr,
                "min_v": row.get("min_v"),
                "max_v": row.get("max_v"),
                "failed": int(row.get("failed") or 0),
                "tone": tone,
                "status": _status(tone),
                "pass_bar": min(max(pr, 0), 100),
                "avg_bar": min(100.0, round(100.0 * av / max_avg, 1)) if max_avg else 0,
            }
        )

    classes = [
        {
            "name": row.get("student__grade") or "Класс не указан",
            "participants": int(row.get("participants") or 0),
            "avg": round(float(row.get("avg") or 0), 2),
            "pass_rate": float(row.get("pass_rate") or 0),
            "pass_bar": min(max(float(row.get("pass_rate") or 0), 0), 100),
        }
        for row in data.get("class_rows") or []
    ]

    dynamics = []
    for row in data.get("dynamics") or []:
        pr = float(row.get("pass_rate") or 0)
        results_n = int(row.get("results") or 0) or int(row.get("participants") or 0)
        dynamics.append(
            {
                "year": row.get("year"),
                "participants": int(row.get("participants") or 0),
                "results": results_n,
                "avg": row.get("avg"),
                "pass_rate": pr,
                "pass_bar": min(max(pr, 0), 100),
            }
        )

    avg_delta = data.get("avg_delta")
    pass_delta = data.get("pass_delta")
    district_avg = data.get("district_avg")
    republic_avg = data.get("republic_avg")

    comparison = [
        _delta_card("Средний балл", avg_delta, unit="", kind="delta"),
        _delta_card("Успеваемость", pass_delta, unit=" п.п.", kind="delta"),
        _compare_card("Район", avg, district_avg, avg_label),
        _compare_card("Республика", avg, republic_avg, avg_label),
    ]

    weak_zones = []
    for row in data.get("weak_subjects") or []:
        pr = float(row.get("pass_rate") or 0)
        av = float(row.get("avg") or 0)
        if pr < 60:
            risk, tone = "Критический", "low"
            desc = "Низкая успеваемость формирует зону управленческого риска."
        elif pr < 75:
            risk, tone = "Средний", "warn"
            desc = "Результат нестабилен, требуется адресная методическая поддержка."
        else:
            risk, tone = "Низкий", "mid"
            desc = "Показатели близки к норме, но предмет остаётся в зоне мониторинга."
        weak_zones.append(
            {
                "name": row.get("exam__subject") or "Предмет",
                "avg": round(av, 2),
                "pass_rate": pr,
                "risk": risk,
                "tone": tone,
                "description": desc,
                "pass_bar": min(max(pr, 0), 100),
            }
        )

    insights = _classify_insights(list(data.get("ai_insights") or []))
    reco_groups = _group_recommendations(list(data.get("recommendations") or []))

    return {
        "has_data": True,
        "exam_label": exam_label,
        "year": data.get("year"),
        "generated_at": data.get("generated_at") or "",
        "avg_label": avg_label,
        "kpi": {
            "participants": participants,
            "total_results": total,
            "avg_score": data.get("avg_score"),
            "quality_rate": quality,
            "pass_rate": pass_rate,
            "tones": {
                "participants": "neutral",
                "avg": _pct_tone_avg(avg, is_oge=is_oge),
                "quality": _pct_tone(quality, high=45, mid=25),
                "pass": _pct_tone(pass_rate, high=85, mid=70),
            },
        },
        "extra": [
            {"label": "Минимальный балл", "value": data.get("min_score"), "icon": "⬇", "tone": "neutral"},
            {"label": "Максимальный балл", "value": data.get("max_score"), "icon": "⬆", "tone": "neutral"},
            {"label": "Высокобалльники", "value": data.get("high_count"), "icon": "★", "tone": "high"},
            {"label": "Неудовлетворительные", "value": data.get("failed_count"), "icon": "!", "tone": "low"},
            {"label": "Группа риска", "value": data.get("risk_count"), "icon": "⚠", "tone": "warn"},
            {"label": "Количество предметов", "value": data.get("subjects_count"), "icon": "▦", "tone": "neutral"},
        ],
        "comparison": comparison,
        "insights": insights,
        "distribution": dist_rows,
        "distribution_total": dist_total,
        "dynamics": dynamics,
        "subjects": subjects,
        "classes": classes,
        "weak_zones": weak_zones,
        "reco_groups": reco_groups,
        "charts_json": json.dumps(
            {
                "distLabels": [r["label"] for r in dist_rows],
                "distValues": [r["value"] for r in dist_rows],
                "dynYears": [str(r["year"]) for r in dynamics],
                "dynAvg": [float(r["avg"] or 0) for r in dynamics],
                "dynPass": [float(r["pass_rate"] or 0) for r in dynamics],
                "avgMax": 5 if is_oge else 100,
            },
            ensure_ascii=False,
        ),
    }


def _dist_rows(raw) -> list[dict[str, Any]]:
    rows = []
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            label, value = item[0], int(item[1] or 0)
        elif isinstance(item, dict):
            label = item.get("label") or "-"
            value = int(item.get("value") or 0)
        else:
            continue
        rows.append({"label": str(label), "value": value})
    total = sum(r["value"] for r in rows) or 0
    max_v = max((r["value"] for r in rows), default=0) or 1
    for r in rows:
        r["percent"] = round(100.0 * r["value"] / total, 1) if total else 0.0
        r["bar"] = round(100.0 * r["value"] / max_v, 1)
    return rows


def _delta_card(label: str, delta, *, unit: str, kind: str) -> dict[str, Any]:
    if delta is None:
        return {"label": label, "value": "нет данных", "arrow": "•", "tone": "neutral", "text": "Сравнение с прошлым годом недоступно"}
    d = float(delta)
    if d > 0:
        arrow, tone, word = "▲", "high", "рост"
    elif d < 0:
        arrow, tone, word = "▼", "low", "снижение"
    else:
        arrow, tone, word = "◆", "mid", "без изменений"
    sign = "+" if d > 0 else ""
    return {
        "label": label,
        "value": f"{sign}{d}{unit}",
        "arrow": arrow,
        "tone": tone,
        "text": f"{word.capitalize()} к прошлому году",
    }


def _compare_card(scope: str, school_avg: float, other, avg_label: str) -> dict[str, Any]:
    if other is None:
        return {"label": scope, "value": "—", "arrow": "•", "tone": "neutral", "text": f"Нет данных по уровню «{scope}»"}
    other_f = float(other)
    diff = round(school_avg - other_f, 2)
    if diff > 0:
        arrow, tone = "▲", "high"
        text = f"Выше уровня «{scope}» на {diff}"
    elif diff < 0:
        arrow, tone = "▼", "low"
        text = f"Ниже уровня «{scope}» на {abs(diff)}"
    else:
        arrow, tone = "◆", "mid"
        text = f"На уровне «{scope}»"
    return {"label": scope, "value": str(other_f), "arrow": arrow, "tone": tone, "text": text}


def _classify_insights(items: list[str]) -> list[dict[str, str]]:
    out = []
    for raw in items:
        text = str(raw or "").strip()
        if not text:
            continue
        low = text.lower()
        if any(k in low for k in ("риск", "критич", "снижен", "низк", "проблем", "неудовлетв")):
            tone, title = "low", "Основной риск"
        elif any(k in low for k in ("вниман", "требует", "рекоменд", "необходим", "усилить")):
            tone, title = "warn", "Требует внимания"
        else:
            tone, title = "high", "Сильная сторона"
        out.append({"tone": tone, "title": title, "text": text})
    return out


def _group_recommendations(items: list[str]) -> list[dict[str, Any]]:
    groups = {
        "Методическая работа": [],
        "Работа с учащимися": [],
        "Контроль администрации": [],
        "Работа с группой риска": [],
    }
    for raw in items:
        text = str(raw or "").strip()
        if not text:
            continue
        low = text.lower()
        if any(k in low for k in ("риск", "неуспев", "индивидуальн", "сопровожд")):
            groups["Работа с группой риска"].append(text)
        elif any(k in low for k in ("администрац", "контроль", "мониторинг", "управлен")):
            groups["Контроль администрации"].append(text)
        elif any(k in low for k in ("методич", "мо ", "преподав", "ким", "тем")):
            groups["Методическая работа"].append(text)
        elif any(k in low for k in ("обучающ", "учащ", "занят", "подготовк", "консультац")):
            groups["Работа с учащимися"].append(text)
        else:
            groups["Методическая работа"].append(text)
    icons = {
        "Методическая работа": "📘",
        "Работа с учащимися": "🧑‍🎓",
        "Контроль администрации": "🏛",
        "Работа с группой риска": "🛡",
    }
    return [
        {"title": title, "icon": icons[title], "items": lines}
        for title, lines in groups.items()
        if lines
    ]


def _tone(pass_rate: float, avg: float, *, is_oge: bool) -> str:
    avg_level = avg if is_oge or avg > 5 else (avg / 5.0) * 100.0
    high_avg = 4.2 if is_oge else 60
    mid_avg = 3.8 if is_oge else 50
    low_avg = 3.2 if is_oge else 40
    if pass_rate >= 85 and avg_level >= high_avg:
        return "high"
    if pass_rate < 60 or avg_level < low_avg:
        return "low"
    if pass_rate < 75 or avg_level < mid_avg:
        return "warn"
    return "mid"


def _status(tone: str) -> str:
    return {
        "high": "Высокий уровень",
        "mid": "Средний",
        "warn": "Низкий",
        "low": "Критический",
    }.get(tone, "Средний")


def _pct_tone(value: float, *, high: float, mid: float) -> str:
    if value >= high:
        return "high"
    if value >= mid:
        return "mid"
    return "low"


def _pct_tone_avg(avg: float, *, is_oge: bool) -> str:
    if is_oge:
        if avg >= 4.2:
            return "high"
        if avg >= 3.5:
            return "mid"
        return "low"
    if avg >= 60:
        return "high"
    if avg >= 45:
        return "mid"
    return "low"
