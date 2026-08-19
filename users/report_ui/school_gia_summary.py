"""
Презентационный слой отчёта «Свод результатов ГИА (ОО)».

Только тексты, ранжирование для UI и визуальные агрегаты
поверх уже рассчитанных показателей. Без SQL и пересчётов.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

MIN_RANK_PARTICIPANTS = 5


def build_gia_summary_presentation(
    *,
    exam_type: str,
    year: str | int | None,
    kpis: dict[str, Any] | None,
    distribution: list[dict[str, Any]] | None,
    subject_rows: list[dict[str, Any]] | None,
    dynamics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    kpis = kpis or {}
    distribution = list(distribution or [])
    subjects = list(subject_rows or [])
    is_oge = (exam_type or "").lower() == "oge"
    exam_label = "ОГЭ" if is_oge else "ЕГЭ"
    avg_label = kpis.get("avg_label") or ("Средняя оценка" if is_oge else "Средний балл")

    eligible = [r for r in subjects if int(r.get("participants") or 0) >= MIN_RANK_PARTICIPANTS]
    thin = [r for r in subjects if int(r.get("participants") or 0) < MIN_RANK_PARTICIPANTS]

    ranked = sorted(
        eligible,
        key=lambda r: (_composite_score(r, is_oge=is_oge), float(r.get("pass_rate") or 0), float(r.get("avg") or 0)),
        reverse=True,
    )
    best, worst = _pick_best_worst(ranked, is_oge=is_oge)
    best_name = (best[0].get("exam__subject") if best else None) or None
    worst_name = (worst[0].get("exam__subject") if worst else None) or None

    total_dist = sum(int(r.get("value") or 0) for r in distribution) or 0
    total_results = int(kpis.get("total_results") or total_dist or 0)
    participants = int(kpis.get("participants") or 0)
    if not participants and total_results:
        participants = total_results

    dist_ui = []
    max_dist = max((int(r.get("value") or 0) for r in distribution), default=0) or 1
    for row in distribution:
        value = int(row.get("value") or 0)
        pct = round(100.0 * value / total_dist, 1) if total_dist else 0.0
        dist_ui.append(
            {
                "label": str(row.get("label") or "-"),
                "value": value,
                "percent": pct,
                "bar": round(100.0 * value / max_dist, 1) if max_dist else 0.0,
            }
        )

    dominant = max(dist_ui, key=lambda x: x["value"]) if dist_ui else None
    high_bucket = dist_ui[-1] if dist_ui else None
    low_bucket = dist_ui[0] if dist_ui else None

    pass_rate = float(kpis.get("pass_rate") or 0)
    quality_rate = float(kpis.get("quality_rate") or 0)
    avg_score = float(kpis.get("avg_score") or 0)

    school_grade = _school_grade(pass_rate=pass_rate, quality=quality_rate, avg=avg_score, is_oge=is_oge)

    count_label = "Результатов"
    subject_count_label = "Результатов"

    subject_cards = []
    for idx, row in enumerate(subjects):
        name = row.get("exam__subject") or "Предмет"
        avg = float(row.get("avg") or 0)
        pr = float(row.get("pass_rate") or 0)
        n = int(row.get("participants") or 0)
        tone = _subject_tone(pr, avg, is_oge=is_oge)
        status = _status_label(tone)
        thin_sample = n < MIN_RANK_PARTICIPANTS
        subject_cards.append(
            {
                "name": name,
                "participants": n,
                "avg": round(avg, 2),
                "pass_rate": pr,
                "tone": tone,
                "status": status,
                "thin_sample": thin_sample,
                "avg_bar": _avg_bar(avg, is_oge=is_oge),
                "pass_bar": min(max(pr, 0), 100),
                "conclusion": (
                    f"{name}: недостаточно статистики для объективной оценки."
                    if thin_sample
                    else _subject_conclusion(name, pr, avg, tone=tone, is_oge=is_oge, idx=idx)
                ),
                "recommendation": (
                    f"{name}: выборка слишком мала, корректные выводы пока недоступны."
                    if thin_sample
                    else _subject_recommendation(name, pr, avg, tone=tone, is_oge=is_oge, idx=idx)
                ),
            }
        )

    max_avg = max((float(c["avg"]) for c in subject_cards), default=1) or 1
    chart_subjects = [c for c in subject_cards if not c["thin_sample"]] or subject_cards

    dynamics_ui = []
    for row in list(dynamics or []):
        dynamics_ui.append(
            {
                "year": row.get("year"),
                "avg": row.get("avg"),
                "pass_rate": row.get("pass_rate"),
                "students": int(row.get("students") or row.get("participants") or 0),
                "results": int(row.get("results") or 0),
                "pass_bar": min(max(float(row.get("pass_rate") or 0), 0), 100),
            }
        )

    executive = {
        "participants": participants,
        "total_results": total_results,
        "avg_score": kpis.get("avg_score"),
        "quality_rate": kpis.get("quality_rate"),
        "pass_rate": kpis.get("pass_rate"),
        "best_subject": best_name,
        "worst_subject": worst_name,
        "main_risk": _main_risk(quality_rate, pass_rate, worst_name, kpis.get("failed_count")),
        "overall": school_grade["label"],
        "text": _executive_text(
            exam_label=exam_label,
            participants=participants,
            total_results=total_results,
            avg_score=avg_score,
            avg_label=avg_label,
            quality_rate=quality_rate,
            pass_rate=pass_rate,
            best_subject=best_name,
            worst_subject=worst_name,
            grade_label=school_grade["label"],
        ),
        "kpi_tones": {
            "participants": "neutral",
            "results": "neutral",
            "avg": _kpi_tone_avg(avg_score, is_oge=is_oge),
            "quality": _kpi_tone_pct(quality_rate, high=45, mid=25),
            "pass": _kpi_tone_pct(pass_rate, high=85, mid=70),
        },
    }

    panels = _final_panels(
        exam_label=exam_label,
        kpis=kpis,
        best_name=best_name,
        worst_name=worst_name,
        avg_label=avg_label,
        school_grade=school_grade,
    )

    return {
        "exam_label": exam_label,
        "year": year,
        "avg_label": avg_label,
        "count_label": count_label,
        "subject_count_label": subject_count_label,
        "executive": executive,
        "school_grade": school_grade,
        "distribution": dist_ui,
        "distribution_total": total_dist,
        "distribution_analysis": _distribution_analysis(
            exam_label=exam_label,
            dominant=dominant,
            high_bucket=high_bucket,
            low_bucket=low_bucket,
            total=total_dist,
            high_count=kpis.get("high_count"),
            failed_count=kpis.get("failed_count"),
            is_oge=is_oge,
        ),
        "subject_cards": subject_cards,
        "best_subjects": [_rank_item(r) for r in best],
        "worst_subjects": [_rank_item(r) for r in worst],
        "thin_subjects": [
            {
                "name": r.get("exam__subject") or "Предмет",
                "participants": int(r.get("participants") or 0),
            }
            for r in thin
        ],
        "dynamics": dynamics_ui,
        "recommendations": [
            c["recommendation"] for c in subject_cards if c.get("recommendation") and not c.get("thin_sample")
        ][:8],
        "next_steps": panels["next_steps"],
        "panels": panels,
        "final_conclusion": panels,
        "charts": {
            "distribution_labels": [d["label"] for d in dist_ui],
            "distribution_values": [d["value"] for d in dist_ui],
            "subject_labels": [c["name"] for c in chart_subjects],
            "subject_avg": [c["avg"] for c in chart_subjects],
            "subject_pass": [c["pass_rate"] for c in chart_subjects],
            "best_labels": [r.get("exam__subject") or "-" for r in best],
            "best_values": [round(float(r.get("avg") or 0), 2) for r in best],
            "worst_labels": [r.get("exam__subject") or "-" for r in worst],
            "worst_values": [round(float(r.get("avg") or 0), 2) for r in worst],
            "avg_max": round(max_avg * 1.15, 1) if not is_oge else 5,
        },
        "charts_json": json.dumps(
            {
                "labels": [c["name"] for c in chart_subjects],
                "avg": [c["avg"] for c in chart_subjects],
                "pass": [c["pass_rate"] for c in chart_subjects],
                "avgMax": round(max_avg * 1.15, 1) if not is_oge else 5,
            },
            ensure_ascii=False,
        ),
    }


def _rank_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": row.get("exam__subject") or "-",
        "avg": round(float(row.get("avg") or 0), 2),
        "pass_rate": float(row.get("pass_rate") or 0),
        "participants": int(row.get("participants") or 0),
        "avg_bar": min(100.0, round(float(row.get("avg") or 0), 2)),
        "pass_bar": min(100.0, float(row.get("pass_rate") or 0)),
    }


def _composite_score(row: dict[str, Any], *, is_oge: bool) -> float:
    """Презентационный рейтинг по успеваемости и среднему без изменения исходных метрик."""
    avg = float(row.get("avg") or 0)
    pr = float(row.get("pass_rate") or 0)
    if is_oge or avg <= 5:
        avg_norm = (avg / 5.0) * 100.0
    else:
        avg_norm = min(avg, 100.0)
    return round(pr * 0.55 + avg_norm * 0.45, 3)


def _pick_best_worst(ranked: list[dict[str, Any]], *, is_oge: bool) -> tuple[list, list]:
    if not ranked:
        return [], []
    if len(ranked) == 1:
        return ranked[:1], []

    best: list[dict[str, Any]] = []
    for row in ranked:
        tone = _subject_tone(float(row.get("pass_rate") or 0), float(row.get("avg") or 0), is_oge=is_oge)
        if tone == "low":
            continue
        best.append(row)
        if len(best) >= 3:
            break
    if not best:
        best = ranked[:1]

    best_names = {r.get("exam__subject") for r in best}
    worst: list[dict[str, Any]] = []
    for row in reversed(ranked):
        name = row.get("exam__subject")
        if name in best_names:
            continue
        pr = float(row.get("pass_rate") or 0)
        tone = _subject_tone(pr, float(row.get("avg") or 0), is_oge=is_oge)
        # Не помещаем в «проблемные» предметы с почти полной успеваемостью без реального риска.
        if tone == "high":
            continue
        if pr >= 98 and tone != "low":
            continue
        if tone == "mid" and pr >= 95:
            # средний балл чуть ниже, но успеваемость высокая — не считаем проблемным блоком
            avg = float(row.get("avg") or 0)
            avg_level = avg if is_oge or avg > 5 else (avg / 5.0) * 100.0
            if (is_oge and avg >= 3.6) or (not is_oge and avg_level >= 45):
                continue
        worst.append(row)
        if len(worst) >= 3:
            break
    return best, worst


def _participants_phrase(n: int) -> str:
    n = int(n or 0)
    mod10 = n % 10
    mod100 = n % 100
    if mod10 == 1 and mod100 != 11:
        word = "участник"
    elif mod10 in {2, 3, 4} and mod100 not in {12, 13, 14}:
        word = "участника"
    else:
        word = "участников"
    return f"{n} {word}"


def _avg_bar(avg: float, *, is_oge: bool) -> float:
    if is_oge:
        return min(100.0, round((avg / 5.0) * 100, 1))
    return min(100.0, round(avg, 1))


def _subject_tone(pass_rate: float, avg: float, *, is_oge: bool) -> str:
    avg_level = avg
    if not is_oge and avg <= 5:
        avg_level = (avg / 5.0) * 100.0
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


def _status_label(tone: str) -> str:
    return {
        "high": "Высокий уровень",
        "mid": "Средний уровень",
        "warn": "Требует внимания",
        "low": "Критическая зона",
    }.get(tone, "Средний уровень")


def _kpi_tone_pct(value: float, *, high: float, mid: float) -> str:
    if value >= high:
        return "high"
    if value >= mid:
        return "mid"
    return "low"


def _kpi_tone_avg(avg: float, *, is_oge: bool) -> str:
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


def _school_grade(*, pass_rate: float, quality: float, avg: float, is_oge: bool) -> dict[str, Any]:
    score = 0
    if pass_rate >= 90:
        score += 2
    elif pass_rate >= 80:
        score += 1.5
    elif pass_rate >= 70:
        score += 1
    elif pass_rate >= 55:
        score += 0.5

    if quality >= 50:
        score += 2
    elif quality >= 35:
        score += 1.5
    elif quality >= 20:
        score += 1
    elif quality >= 10:
        score += 0.5

    avg_ok = avg >= (4.0 if is_oge else 55)
    avg_mid = avg >= (3.5 if is_oge else 40)
    if avg_ok:
        score += 1
    elif avg_mid:
        score += 0.5

    if score >= 4.5:
        stars, label, tone = 5, "Высокий уровень", "high"
    elif score >= 3.5:
        stars, label, tone = 4, "Хороший уровень", "high"
    elif score >= 2.5:
        stars, label, tone = 3, "Удовлетворительный", "mid"
    elif score >= 1.5:
        stars, label, tone = 2, "Ниже среднего", "low"
    else:
        stars, label, tone = 1, "Критический", "low"

    return {
        "stars": stars,
        "stars_display": "★" * stars + "☆" * (5 - stars),
        "label": label,
        "tone": tone,
        "score": round(score, 1),
    }


def _pick(variants: list[str], key: str) -> str:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return variants[int(digest[:8], 16) % len(variants)]


def _subject_conclusion(name: str, pass_rate: float, avg: float, *, tone: str, is_oge: bool, idx: int) -> str:
    avg_s = f"{avg:.2f}".replace(".", ",")
    pass_s = f"{pass_rate:.1f}".replace(".", ",")
    metric = "средняя оценка" if is_oge else "средний тестовый балл"
    key = f"{name}:{tone}:{idx}"

    if tone == "high":
        return _pick(
            [
                f"Результаты по предмету {name} находятся на высоком уровне. Минимальный порог преодолели {pass_s}% участников, {metric} составил {avg_s}.",
                f"По {name} школа показывает уверенный результат: успеваемость {pass_s}%, {metric} {avg_s}.",
                f"{name} входит в число сильных позиций. Доля преодолевших порог — {pass_s}%, {metric} — {avg_s}.",
            ],
            key,
        )
    if tone == "low":
        return _pick(
            [
                f"По {name} зафиксирован пониженный результат. Успеваемость {pass_s}%, {metric} {avg_s} — требуется адресная коррекция.",
                f"Предмет {name} формирует зону риска: порог преодолели только {pass_s}% участников при показателе {avg_s}.",
                f"Результаты по {name} заметно отстают от целевого уровня. Успеваемость {pass_s}%, {metric} {avg_s}.",
            ],
            key,
        )
    return _pick(
        [
            f"По {name} результат стабильный, но есть запас роста. Успеваемость {pass_s}%, {metric} {avg_s}.",
            f"{name}: показатели близки к среднему уровню. Минимальный порог преодолели {pass_s}% участников, {metric} — {avg_s}.",
            f"По предмету {name} сохраняется умеренный профиль: успеваемость {pass_s}%, {metric} {avg_s}.",
        ],
        key,
    )


def _subject_recommendation(name: str, pass_rate: float, avg: float, *, tone: str, is_oge: bool, idx: int) -> str:
    avg_level = avg if is_oge or avg > 5 else (avg / 5.0) * 100.0
    low_avg = avg_level < (3.5 if is_oge else 45)
    low_pass = pass_rate < 70
    key = f"rec:{name}:{tone}:{idx}:{int(low_avg)}:{int(low_pass)}"

    if tone == "high":
        return _pick(
            [
                f"{name}: закрепить успешные практики на заседании МО и использовать их как образец для смежных предметов.",
                f"{name}: сохранить текущую модель подготовки и тиражировать подходы учителя на параллели.",
                f"{name}: поддерживать высокий уровень через углублённые задания и работу с мотивированными обучающимися.",
            ],
            key,
        )
    if low_pass and low_avg:
        return _pick(
            [
                f"{name}: одновременно усилить базовую подготовку и открыть дополнительные занятия для группы риска.",
                f"{name}: выстроить индивидуальные маршруты для неуспевающих и пересмотреть отработку ключевых тем КИМ.",
                f"{name}: провести диагностику пробелов и организовать интенсив по заданиям базового уровня.",
            ],
            key,
        )
    if low_pass:
        return _pick(
            [
                f"{name}: организовать дополнительные занятия и еженедельный контроль преодоления минимального порога.",
                f"{name}: усилить сопровождение обучающихся с риском неуспеваемости и провести повторные тренировочные работы.",
                f"{name}: сфокусировать подготовку на заданиях, где фиксируется наибольшая доля ошибок.",
            ],
            key,
        )
    if low_avg:
        return _pick(
            [
                f"{name}: усилить подготовку к заданиям повышенного уровня, чтобы подтянуть средний результат.",
                f"{name}: расширить практику решения типовых и усложнённых заданий КИМ.",
                f"{name}: пересмотреть тематическое планирование с акцентом на слабые содержательные блоки.",
            ],
            key,
        )
    return _pick(
        [
            f"{name}: поддерживать текущий уровень и точечно отрабатывать темы с пониженной успешностью.",
            f"{name}: провести разбор типичных ошибок и скорректировать подготовку на ближайший период.",
            f"{name}: сохранить динамику за счёт регулярных тренировочных срезов и методической поддержки.",
        ],
        key,
    )


def _executive_text(
    *,
    exam_label: str,
    participants: int,
    total_results: int,
    avg_score: float,
    avg_label: str,
    quality_rate: float,
    pass_rate: float,
    best_subject,
    worst_subject,
    grade_label: str,
) -> str:
    avg_s = f"{avg_score:.2f}".replace(".", ",")
    q_s = f"{quality_rate:.1f}".replace(".", ",")
    p_s = f"{pass_rate:.1f}".replace(".", ",")
    if total_results and total_results != participants:
        head = _pick(
            [
                f"В {exam_label} приняли участие {participants} обучающихся, всего учтено {total_results} результатов по предметам.",
                f"Экзамен {exam_label}: {participants} участников и {total_results} предметных результатов.",
                f"В свод включены {participants} обучающихся и {total_results} результатов {exam_label}.",
            ],
            f"ex-p-{participants}-{total_results}-{exam_label}",
        )
    else:
        head = _pick(
            [
                f"В {exam_label} приняли участие {participants} обучающихся.",
                f"Экзамен {exam_label} сдали {participants} обучающихся школы.",
                f"В свод включены результаты {participants} участников {exam_label}.",
            ],
            f"ex-p-{participants}-{exam_label}",
        )
    parts = [
        head,
        _pick(
            [
                (
                    f"{avg_label} составила {avg_s}."
                    if "оценка" in avg_label.lower()
                    else f"{avg_label} составил {avg_s}."
                ),
                f"Ключевой показатель — {avg_label.lower()} {avg_s}.",
                f"По школе {avg_label.lower()} — {avg_s}.",
            ],
            f"ex-a-{avg_s}",
        ),
    ]
    if best_subject and worst_subject and best_subject != worst_subject:
        parts.append(
            _pick(
                [
                    f"Наиболее уверенно выглядит {best_subject}, основная зона внимания — {worst_subject}.",
                    f"Лучший предмет — {best_subject}, наиболее проблемный — {worst_subject}.",
                    f"Сильная позиция: {best_subject}. Приоритет коррекции: {worst_subject}.",
                ],
                f"ex-bw-{best_subject}-{worst_subject}",
            )
        )
    elif best_subject:
        parts.append(f"Лучший результат показан по предмету {best_subject}.")

    if quality_rate < 40:
        parts.append(
            _pick(
                [
                    f"Качество знаний {q_s}% при успеваемости {p_s}% указывает на необходимость усиления подготовки.",
                    f"Успеваемость держится на уровне {p_s}%, однако качество знаний {q_s}% остаётся низким.",
                    f"Общая оценка: {grade_label.lower()}. Качество знаний {q_s}% требует управленческого внимания.",
                ],
                f"ex-q-{q_s}-{p_s}",
            )
        )
    else:
        parts.append(
            f"Качество знаний {q_s}%, успеваемость {p_s}%. Общая оценка: {grade_label.lower()}."
        )
    return " ".join(parts)


def _main_risk(quality: float, pass_rate: float, worst_subject, failed_count) -> str:
    if worst_subject and quality < 30:
        return f"Низкое качество знаний и слабые результаты по предмету {worst_subject}"
    if worst_subject:
        return f"Снижение общего профиля из-за предмета {worst_subject}"
    if quality < 30:
        return "Системно низкое качество знаний"
    if pass_rate < 70:
        return "Недостаточная успеваемость по школе"
    if failed_count:
        return f"Группа с неудовлетворительными результатами: {failed_count}"
    return "Локальные предметные колебания"


def _distribution_analysis(
    *,
    exam_label: str,
    dominant,
    high_bucket,
    low_bucket,
    total: int,
    high_count,
    failed_count,
    is_oge: bool,
) -> list[str]:
    texts: list[str] = []
    if not total:
        return texts
    if dominant:
        texts.append(
            _pick(
                [
                    f"В распределении результатов {exam_label} преобладает диапазон {dominant['label']}: {_results_phrase(dominant['value'])} ({dominant['percent']}%).",
                    f"Наибольшая доля результатов сосредоточена в группе {dominant['label']} — {dominant['percent']}%.",
                    f"Доминирующая группа — {dominant['label']} ({_results_phrase(dominant['value'])}, {dominant['percent']}%).",
                ],
                f"dist-dom-{dominant['label']}",
            )
        )
    if high_bucket and high_bucket["value"]:
        kind = "отличных отметок" if is_oge else "высоких баллов"
        texts.append(
            f"Группа {kind} ({high_bucket['label']}): {_results_phrase(high_bucket['value'])} ({high_bucket['percent']}%)."
        )
    elif high_count:
        texts.append(f"Результатов с высокими показателями: {high_count}.")
    if low_bucket and low_bucket["value"]:
        texts.append(
            f"Низкие результаты ({low_bucket['label']}): {_results_phrase(low_bucket['value'])} ({low_bucket['percent']}%)."
        )
        if low_bucket["percent"] >= 30:
            texts.append("Доля низких результатов высока и формирует управленческий риск.")
    elif failed_count:
        texts.append(f"Неудовлетворительных результатов: {failed_count}.")
    return texts


def _results_phrase(n: int) -> str:
    n = int(n or 0)
    mod10 = n % 10
    mod100 = n % 100
    if mod10 == 1 and mod100 != 11:
        word = "результат"
    elif mod10 in {2, 3, 4} and mod100 not in {12, 13, 14}:
        word = "результата"
    else:
        word = "результатов"
    return f"{n} {word}"


def _final_panels(
    *,
    exam_label: str,
    kpis: dict[str, Any],
    best_name,
    worst_name,
    avg_label: str,
    school_grade: dict[str, Any],
) -> dict[str, list[str]]:
    pass_rate = float(kpis.get("pass_rate") or 0)
    quality = float(kpis.get("quality_rate") or 0)
    avg = float(kpis.get("avg_score") or 0)
    risk = int(kpis.get("risk_students") or 0)

    strengths = []
    if best_name:
        strengths.append(f"Сильная предметная зона: {best_name}.")
    if pass_rate >= 80:
        strengths.append(f"Успеваемость по школе высокая: {pass_rate}%.")
    if quality >= 40:
        strengths.append(f"Качество знаний на приемлемом уровне: {quality}%.")
    if not strengths:
        strengths.append("Сохранена база участников и возможность адресной коррекции.")

    weaknesses = []
    if worst_name:
        weaknesses.append(f"Проблемная предметная зона: {worst_name}.")
    if quality < 40:
        weaknesses.append(f"Низкое качество знаний: {quality}%.")
    if pass_rate < 75:
        weaknesses.append(f"Недостаточная успеваемость: {pass_rate}%.")
    if risk:
        weaknesses.append(f"Группа риска: {risk} обучающихся.")
    if not weaknesses:
        weaknesses.append("Выраженных системных дефицитов не выявлено.")

    risks = []
    if risk:
        risks.append("Закрепление группы риска без индивидуальных маршрутов.")
    if worst_name:
        risks.append(f"Давление на средний результат школы со стороны предмета {worst_name}.")
    if quality < 30:
        risks.append("Системный дефицит подготовки повышенного уровня.")
    if not risks:
        risks.append("Локальные колебания при общей управляемости процесса.")

    assessment = [
        f"Общая оценка результатов {exam_label}: {school_grade['label'].lower()}.",
        f"{avg_label}: {avg}. Успеваемость: {pass_rate}%. Качество знаний: {quality}%.",
    ]

    next_steps = []
    if worst_name:
        next_steps.append(f"Приоритет: программа повышения результатов по предмету {worst_name}.")
    if best_name and worst_name and best_name != worst_name:
        next_steps.append(f"Перенести практики сильного предмета «{best_name}» на «{worst_name}».")
    next_steps.append(
        f"Зафиксировать целевые показатели: успеваемость ≥ текущего {pass_rate}%, качество ≥ {quality}%."
    )
    next_steps.append("Запустить адресные консультации для обучающихся группы риска по предметам с низким статусом.")

    recommendations = []
    if worst_name:
        recommendations.append(f"Сконцентрировать ресурс на предмете «{worst_name}».")
    recommendations.append(
        f"Усилить подготовку с опорой на фактические показатели: средний {avg}, успеваемость {pass_rate}%."
    )
    if risk:
        recommendations.append(f"Выстроить маршруты для группы риска ({risk} обучающихся).")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "risks": risks,
        "assessment": assessment,
        "recommendations": recommendations[:6],
        "next_steps": next_steps[:4],
        "priorities": next_steps[:4],
    }
