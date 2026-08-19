"""
Презентационный слой «Аналитическая справка по итогам ГИА».

Только UI поверх готового analytic_note_payload.
Без SQL, пересчётов и изменения бизнес-логики.

Экспертные тексты строятся по 4 категориям:
1) подтверждённый факт
2) аналитический вывод
3) гипотеза
4) управленческое решение
"""

from __future__ import annotations

import json
from typing import Any

KIND_FACT = "fact"
KIND_CONCLUSION = "conclusion"
KIND_HYPOTHESIS = "hypothesis"
KIND_DECISION = "decision"

KIND_LABELS = {
    KIND_FACT: "Подтверждённый факт",
    KIND_CONCLUSION: "Аналитический вывод",
    KIND_HYPOTHESIS: "Гипотеза",
    KIND_DECISION: "Управленческое решение",
}

_FORBIDDEN_CAUSE_MARKERS = (
    "низкая мотивация",
    "плохая методика",
    "недостаточная подготовка педагог",
    "низкое качество преподавания",
    "слабая квалификация",
    "плохая работа учител",
    "причиной является",
    "причина заключается",
)


def build_analytic_note_presentation(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload or {}
    if not data.get("has_data"):
        return {"has_data": False, "message": data.get("message") or "Недостаточно данных."}

    et = (data.get("exam_type") or "ege").lower()
    is_oge = et == "oge"
    exam_label = "ОГЭ" if is_oge else "ЕГЭ"
    avg_label = "Средняя оценка" if is_oge else "Средний балл"
    high_hint = "оценка 5" if is_oge else "балл ≥ 70"

    total = int(data.get("total") or 0)
    participants = int(data.get("participants") or 0) or total
    subjects_count = int(data.get("subjects_count") or 0)
    avg = float(data.get("avg_score") or 0)
    quality = float(data.get("quality_rate") or 0)
    pass_rate = float(data.get("pass_rate") or 0)
    high_count = int(data.get("high_count") or 0)
    risk_count = int(data.get("risk_count") or 0)

    subjects = []
    max_avg = max((float(r.get("avg") or 0) for r in (data.get("subject_rows") or [])), default=1) or 1
    for row in data.get("subject_rows") or []:
        pr = float(row.get("pass_rate") or 0)
        av = float(row.get("avg") or 0)
        tone = _subject_tone(pr, av, is_oge=is_oge)
        subjects.append(
            {
                "name": row.get("exam__subject") or "Предмет",
                "participants": int(row.get("participants") or 0),
                "avg": round(av, 2),
                "pass_rate": pr,
                "min_v": row.get("min_v"),
                "max_v": row.get("max_v"),
                "tone": tone,
                "status": _status_label(tone),
                "icon": _status_icon(tone),
                "pass_bar": min(max(pr, 0), 100),
                "avg_bar": min(100.0, round(100.0 * av / max_avg, 1)) if max_avg else 0,
            }
        )

    classes = []
    for row in data.get("class_rows") or []:
        pr = float(row.get("pass_rate") or 0)
        classes.append(
            {
                "name": row.get("student__grade") or "Класс не указан",
                "participants": int(row.get("participants") or 0),
                "avg": round(float(row.get("avg") or 0), 2),
                "pass_rate": pr,
                "pass_bar": min(max(pr, 0), 100),
                "tone": _pct_tone(pr, high=85, mid=70),
            }
        )

    dynamics = []
    for row in data.get("dynamics") or []:
        pr = float(row.get("pass_rate") or 0)
        participants_y = int(row.get("participants") or 0)
        results_y = int(row.get("results") or 0) or participants_y
        dynamics.append(
            {
                "year": row.get("year"),
                "participants": participants_y,
                "results": results_y,
                "avg": row.get("avg"),
                "pass_rate": pr,
                "pass_bar": min(max(pr, 0), 100),
            }
        )

    weak_zones = []
    for row in data.get("weak_subjects") or []:
        pr = float(row.get("pass_rate") or 0)
        av = float(row.get("avg") or 0)
        if pr < 60:
            risk, tone = "Критический", "low"
        elif pr < 75:
            risk, tone = "Средний", "warn"
        else:
            risk, tone = "Мониторинг", "mid"
        weak_zones.append(
            {
                "name": row.get("exam__subject") or "Предмет",
                "avg": round(av, 2),
                "pass_rate": pr,
                "risk": risk,
                "tone": tone,
                "pass_bar": min(max(pr, 0), 100),
                "statements": [
                    _stmt(
                        KIND_FACT,
                        f"Средний результат {round(av, 2)}, успеваемость {pr}%.",
                    ),
                    _stmt(
                        KIND_DECISION,
                        "Организовать дополнительную диагностику и анализ выполнения заданий по предмету.",
                    ),
                ],
                "text": (
                    f"[Факт] Средний результат {round(av, 2)}, успеваемость {pr}%. "
                    f"[Решение] Организовать дополнительную диагностику и анализ выполнения заданий по предмету."
                ),
            }
        )

    high_statements = [
        _stmt(
            KIND_FACT,
            f"Высокобалльных результатов ({high_hint}): {high_count}.",
        )
    ]
    if high_count > 0:
        high_statements.append(
            _stmt(
                KIND_CONCLUSION,
                "В выборке присутствует сегмент высоких результатов, который можно использовать как ориентир успешных практик.",
            )
        )
        high_statements.append(
            _stmt(
                KIND_DECISION,
                "Зафиксировать и тиражировать рабочие приёмы подготовки по предметам с высокими результатами.",
            )
        )
    else:
        high_statements.append(
            _stmt(
                KIND_CONCLUSION,
                "Сегмент высоких достижений в текущем периоде не сформирован.",
            )
        )
        high_statements.append(
            _stmt(
                KIND_DECISION,
                "Организовать диагностику потенциально сильных обучающихся и оценить эффективность подготовки к заданиям повышенной сложности.",
            )
        )

    expert = _build_expert_sections(
        exam_label=exam_label,
        is_oge=is_oge,
        year=data.get("year"),
        participants=participants,
        total_results=total,
        subjects_count=subjects_count,
        avg=avg,
        pass_rate=pass_rate,
        quality=quality,
        high_count=high_count,
        high_hint=high_hint,
        risk_count=risk_count,
        subjects=subjects,
        weak_zones=weak_zones,
        dynamics=dynamics,
    )

    conclusions = {
        "strengths": [s["text"] for s in expert.get("conclusion_strengths") or []],
        "attention": [s["text"] for s in expert.get("conclusion_attention") or []],
        "overall": [s["text"] for s in expert.get("conclusion_overall") or []],
    }
    reco_groups = _group_recommendations([s["text"] for s in expert.get("decision_bank") or []])
    methodological = _present_methodological(data.get("methodological") or {}, is_oge=is_oge)

    return {
        "has_data": True,
        "exam_label": exam_label,
        "year": data.get("year"),
        "avg_label": avg_label,
        "kind_labels": KIND_LABELS,
        "kpi": {
            "participants": participants,
            "total_results": total,
            "subjects_count": subjects_count,
            "avg_score": data.get("avg_score"),
            "quality_rate": quality,
            "pass_rate": pass_rate,
            "high_count": high_count,
            "risk_count": risk_count,
            "tones": {
                "participants": "neutral",
                "subjects": "neutral",
                "avg": _pct_tone_avg(avg, is_oge=is_oge),
                "quality": _pct_tone(quality, high=45, mid=25),
                "pass": _pct_tone(pass_rate, high=85, mid=70),
                "high": "high" if high_count > 0 else "neutral",
            },
        },
        "subjects": subjects,
        "classes": classes,
        "weak_zones": weak_zones,
        "has_weak_zones": bool(weak_zones),
        "high_scorers": {
            "count": high_count,
            "tone": "high" if high_count > 0 else "neutral",
            "threshold_hint": high_hint,
            "statements": high_statements,
            "insight": " ".join(f"[{s['label']}] {s['text']}" for s in high_statements),
        },
        "dynamics": dynamics,
        "conclusions": conclusions,
        "reco_groups": reco_groups,
        "expert": expert,
        "methodological": methodological,
        "charts_json": json.dumps(
            {
                "dynYears": [str(r["year"]) for r in dynamics],
                "dynAvg": [float(r["avg"] or 0) for r in dynamics],
                "dynPass": [float(r["pass_rate"] or 0) for r in dynamics],
                "avgMax": 5 if is_oge else 100,
            },
            ensure_ascii=False,
        ),
    }


def _stmt(kind: str, text: str) -> dict[str, str]:
    return {
        "kind": kind,
        "label": KIND_LABELS.get(kind, kind),
        "text": str(text or "").strip(),
    }


def _present_methodological(raw: dict[str, Any], *, is_oge: bool) -> dict[str, Any]:
    data = raw or {}
    exam_label = "ОГЭ" if is_oge else "ЕГЭ"
    subject_blocks = []
    for block in data.get("subject_blocks") or []:
        subject_blocks.append(
            {
                "subject": block.get("subject"),
                "has_task_data": bool(block.get("has_task_data")),
                "message": block.get("message") or "",
                "school_task_avg": block.get("school_task_avg"),
                "analysis_text": block.get("analysis_text") or "",
                "sections": (block.get("sections") or [])[:4],
                "topics": (block.get("topics") or [])[:6],
            }
        )
    return {
        "exam_label": exam_label,
        "year": data.get("year"),
        "has_any_task_data": bool(data.get("has_any_task_data")),
        "methodology_note": data.get("methodology_note")
        or f"Анализ по спецификации и кодификатору ФИПИ ({exam_label}): агрегация по темам.",
        "aggregation_overview": data.get("aggregation_overview") or [],
        "subject_blocks": subject_blocks,
        "topics": data.get("topics") or [],
        "priority_topics": data.get("priority_topics") or [],
        "class_analysis": data.get("class_analysis") or [],
        "recommendations_by_topic": data.get("recommendations_by_topic") or [],
        "correction_plan": data.get("correction_plan") or [],
        "school_deficit_map": data.get("school_deficit_map") or [],
        "methodological_conclusion": data.get("methodological_conclusion") or [],
        "appendix_note": (
            (data.get("technical_appendix") or {}).get("note")
            or "Полные списки заданий и кодов вынесены в техническое приложение и не включаются в основную справку."
        ),
        "empty_message": (
            "Предметный анализ по КЭС и темам невозможен: отсутствуют данные выполнения заданий КИМ "
            f"по выбранному периоду ({exam_label})."
        ),
    }


def _subject_tone(pass_rate: float, avg: float, *, is_oge: bool) -> str:
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


def _status_label(tone: str) -> str:
    return {
        "high": "Высокий уровень",
        "mid": "Средний",
        "warn": "Требует внимания",
        "low": "Проблемный",
    }.get(tone, "Средний")


def _status_icon(tone: str) -> str:
    return {"high": "🟢", "mid": "🟡", "warn": "🟠", "low": "🔴"}.get(tone, "🟡")


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


def _group_recommendations(items: list[str]) -> list[dict[str, Any]]:
    groups = {
        "Диагностика и мониторинг": [],
        "Методическая работа": [],
        "Работа с обучающимися": [],
        "Контроль администрации": [],
    }
    for raw in items:
        text = str(raw or "").strip()
        if not text:
            continue
        low = text.lower()
        if any(k in low for k in ("администрац", "контроль", "утвердить", "закрепить", "ответственн")):
            groups["Контроль администрации"].append(text)
        elif any(k in low for k in ("диагност", "мониторинг", "анализ выполнен", "проверк", "оцен")):
            groups["Диагностика и мониторинг"].append(text)
        elif any(k in low for k in ("обучающ", "учащ", "маршрут", "консультац", "групп")):
            groups["Работа с обучающимися"].append(text)
        else:
            groups["Методическая работа"].append(text)
    icons = {
        "Диагностика и мониторинг": "🔎",
        "Методическая работа": "📘",
        "Работа с обучающимися": "🧑‍🎓",
        "Контроль администрации": "🏛",
    }
    return [
        {"title": title, "icon": icons[title], "items": lines}
        for title, lines in groups.items()
        if lines
    ]


def _build_expert_sections(
    *,
    exam_label: str,
    is_oge: bool,
    year,
    participants: int,
    total_results: int,
    subjects_count: int,
    avg: float,
    pass_rate: float,
    quality: float,
    high_count: int,
    high_hint: str,
    risk_count: int,
    subjects: list[dict[str, Any]],
    weak_zones: list[dict[str, Any]],
    dynamics: list[dict[str, Any]],
) -> dict[str, Any]:
    best_subjects = sorted(
        subjects, key=lambda x: (float(x.get("pass_rate") or 0), float(x.get("avg") or 0)), reverse=True
    )[:3]
    worst_subjects = sorted(
        subjects, key=lambda x: (float(x.get("pass_rate") or 0), float(x.get("avg") or 0))
    )[:3]
    avg_unit = "оценки" if is_oge else "балла"
    year_label = str(year) if year else "текущий период"
    subjects_below_75 = [s for s in subjects if float(s.get("pass_rate") or 0) < 75]
    concentration_near_threshold = len(subjects_below_75)

    delta_avg = None
    delta_pass = None
    delta_participants = None
    if len(dynamics) >= 2:
        delta_avg = float(dynamics[-1].get("avg") or 0) - float(dynamics[-2].get("avg") or 0)
        delta_pass = float(dynamics[-1].get("pass_rate") or 0) - float(dynamics[-2].get("pass_rate") or 0)
        delta_participants = int(dynamics[-1].get("participants") or 0) - int(dynamics[-2].get("participants") or 0)

    dyn_lines = [
        (
            f"{row.get('year')}: участников {row.get('participants')}, результатов {row.get('results')}, "
            f"средний {row.get('avg')}, успеваемость {row.get('pass_rate')}%"
        )
        for row in dynamics
    ]

    # --- 01 Управленческое резюме ---
    executive_summary = [
        _stmt(
            KIND_FACT,
            f"По итогам {exam_label} за {year_label} в экзамене приняли участие {participants} обучающихся; "
            f"учтено {total_results} предметных результатов по {subjects_count} предметам.",
        ),
        _stmt(
            KIND_FACT,
            f"Средний результат: {avg:.2f} {avg_unit}; успеваемость: {pass_rate:.1f}%; "
            f"качество знаний: {quality:.1f}%; высокобалльные результаты ({high_hint}): {high_count}; "
            f"обучающихся в группе риска: {risk_count}.",
        ),
    ]
    if delta_participants is not None:
        executive_summary.append(
            _stmt(KIND_FACT, f"Число участников изменилось на {delta_participants:+d} относительно предыдущего года.")
        )
    if delta_avg is not None:
        if delta_avg > 0:
            executive_summary.append(
                _stmt(KIND_FACT, f"Средний результат увеличился на {delta_avg:.2f} {avg_unit} к предыдущему году.")
            )
        elif delta_avg < 0:
            executive_summary.append(
                _stmt(KIND_FACT, f"Средний результат снизился на {abs(delta_avg):.2f} {avg_unit} к предыдущему году.")
            )
        else:
            executive_summary.append(
                _stmt(KIND_FACT, "Средний результат сохранился на уровне предыдущего года.")
            )
    if weak_zones:
        names = ", ".join((z.get("name") or "предмет") for z in weak_zones[:3])
        executive_summary.append(_stmt(KIND_FACT, f"В группу риска по предметам входят: {names}."))
        executive_summary.append(
            _stmt(
                KIND_CONCLUSION,
                "Основные риски периода локализуются в отдельных предметах с пониженной успеваемостью.",
            )
        )
    else:
        executive_summary.append(
            _stmt(KIND_FACT, "По заданным критериям предметы группы риска не выявлены.")
        )
    if best_subjects:
        executive_summary.append(
            _stmt(
                KIND_FACT,
                "Лучшие предметные позиции периода: "
                + ", ".join((s.get("name") or "предмет") for s in best_subjects)
                + ".",
            )
        )

    # --- 02 Комплексный анализ ---
    comprehensive = []
    if participants:
        comprehensive.append(
            _stmt(
                KIND_FACT,
                f"Структура периода: {participants} участников и {total_results} результатов "
                f"(в среднем {(total_results / participants):.1f} предмета на участника).",
            )
        )
    if delta_avg is not None:
        comprehensive.append(_stmt(KIND_FACT, f"Изменение среднего результата к предыдущему году: {delta_avg:+.2f} {avg_unit}."))
    if delta_pass is not None:
        comprehensive.append(_stmt(KIND_FACT, f"Изменение успеваемости к предыдущему году: {delta_pass:+.1f} п.п."))
        if delta_pass < 0 and delta_avg is not None and delta_avg > 0:
            comprehensive.append(
                _stmt(
                    KIND_CONCLUSION,
                    "Рост среднего результата сопровождается снижением успеваемости: "
                    "профиль результатов неоднороден.",
                )
            )
        elif pass_rate >= 80 and quality < 30:
            comprehensive.append(
                _stmt(
                    KIND_CONCLUSION,
                    "Высокая успеваемость при низком качестве знаний свидетельствует о преобладании "
                    "минимально достаточного уровня подготовки.",
                )
            )
        elif delta_pass > 0 and delta_avg is not None and delta_avg > 0:
            comprehensive.append(
                _stmt(
                    KIND_CONCLUSION,
                    "Одновременный рост среднего результата и успеваемости указывает на улучшение общего профиля результатов.",
                )
            )
    if subjects_below_75:
        comprehensive.append(
            _stmt(
                KIND_FACT,
                "Предметы с успеваемостью ниже 75%: "
                + ", ".join(s.get("name") or "предмет" for s in subjects_below_75)
                + ".",
            )
        )
    else:
        comprehensive.append(_stmt(KIND_FACT, "Предметы с успеваемостью ниже 75% отсутствуют."))
    if dyn_lines:
        comprehensive.append(_stmt(KIND_FACT, "Ряд динамики по годам: " + "; ".join(dyn_lines) + "."))

    # --- 03 Предметный анализ ---
    subject_analysis = []
    for s in subjects:
        pr = float(s.get("pass_rate") or 0)
        av = float(s.get("avg") or 0)
        min_v = s.get("min_v")
        max_v = s.get("max_v")
        items = [
            _stmt(
                KIND_FACT,
                f"Участников: {s.get('participants')}; средний результат: {av}; успеваемость: {pr}%; "
                f"диапазон: {min_v}–{max_v}; статус по данным: «{s.get('status')}».",
            )
        ]
        if pr < 75:
            items.append(
                _stmt(
                    KIND_CONCLUSION,
                    "Предмет входит в зону повышенного внимания по критерию успеваемости.",
                )
            )
            items.append(
                _stmt(
                    KIND_HYPOTHESIS,
                    "Возможной причиной может являться неравномерная отработка заданий базового уровня; "
                    "для подтверждения требуется анализ выполнения заданий.",
                )
            )
            items.append(
                _stmt(
                    KIND_DECISION,
                    "Провести анализ выполнения заданий и организовать дополнительную диагностику по предмету.",
                )
            )
        elif pr >= 85:
            items.append(
                _stmt(
                    KIND_CONCLUSION,
                    "По фактическим показателям предмет формирует устойчивый вклад в общий профиль результатов.",
                )
            )
            items.append(
                _stmt(
                    KIND_DECISION,
                    "Зафиксировать успешные практики подготовки по предмету для возможного тиражирования.",
                )
            )
        else:
            items.append(
                _stmt(
                    KIND_CONCLUSION,
                    "Показатели предмета находятся в рабочей зоне и требуют планового мониторинга.",
                )
            )
        subject_analysis.append({"name": s.get("name"), "items": items, "text": _join_stmt_text(items)})

    # --- 04 Сильные стороны ---
    strengths_analysis = []
    if best_subjects:
        strengths_analysis.append(
            _stmt(
                KIND_FACT,
                "Предметы с наиболее высокими показателями: "
                + ", ".join(
                    f"{s.get('name')} (усп. {s.get('pass_rate')}%, ср. {s.get('avg')})" for s in best_subjects
                )
                + ".",
            )
        )
        strengths_analysis.append(
            _stmt(
                KIND_CONCLUSION,
                "Эти предметы формируют фактическое ядро относительно более высоких результатов периода.",
            )
        )
        strengths_analysis.append(
            _stmt(
                KIND_DECISION,
                "Оценить эффективность подготовки по лидирующим предметам и тиражировать подтверждённые практики.",
            )
        )
    else:
        strengths_analysis.append(
            _stmt(KIND_FACT, "Выраженное ядро лидирующих предметов по данным периода не сформировано.")
        )

    # --- 05 Проблемные зоны ---
    problems_analysis = []
    if weak_zones:
        for z in weak_zones:
            problems_analysis.append(
                _stmt(
                    KIND_FACT,
                    f"Предмет «{z.get('name')}»: средний результат {z.get('avg')}, успеваемость {z.get('pass_rate')}%, "
                    f"уровень риска по данным — {z.get('risk')}.",
                )
            )
            problems_analysis.append(
                _stmt(
                    KIND_CONCLUSION,
                    f"Предмет «{z.get('name')}» входит в группу риска по критерию успеваемости.",
                )
            )
            problems_analysis.append(
                _stmt(
                    KIND_HYPOTHESIS,
                    f"Возможной причиной снижения по «{z.get('name')}» может быть неоднородность подготовки "
                    f"или недостаточная адресность сопровождения; требуется дополнительный анализ.",
                )
            )
            problems_analysis.append(
                _stmt(
                    KIND_DECISION,
                    f"По предмету «{z.get('name')}» провести диагностику, анализ выполнения заданий "
                    f"и экспертную проверку рабочих программ.",
                )
            )
    else:
        problems_analysis.append(
            _stmt(KIND_FACT, "Критических проблемных зон по заданным критериям не выявлено.")
        )
        problems_analysis.append(
            _stmt(
                KIND_DECISION,
                "Сохранить плановый мониторинг предметов с успеваемостью ближе к нижней границе рабочей зоны.",
            )
        )

    # --- 07 Группа риска ---
    risk_group_analysis = [
        _stmt(
            KIND_FACT,
            (
                f"В группе риска {risk_count} обучающихся "
                f"({(100.0 * risk_count / participants):.1f}% от {participants} участников)."
                if participants
                else f"В группе риска {risk_count} обучающихся."
            ),
        )
    ]
    weak_names = ", ".join((z.get("name") or "предмет") for z in weak_zones[:4]) or "не выделены"
    risk_group_analysis.append(_stmt(KIND_FACT, f"Основные предметы риска по данным: {weak_names}."))
    if risk_count > 0:
        risk_group_analysis.append(
            _stmt(
                KIND_CONCLUSION,
                "Сегмент риска определяет устойчивость итоговой успешности и требует приоритетного сопровождения.",
            )
        )
        risk_group_analysis.append(
            _stmt(
                KIND_DECISION,
                "Организовать дополнительную диагностику и индивидуальные маршруты для обучающихся группы риска.",
            )
        )
    else:
        risk_group_analysis.append(
            _stmt(KIND_CONCLUSION, "Численность группы риска минимальна.")
        )
        risk_group_analysis.append(
            _stmt(
                KIND_DECISION,
                "Сохранить профилактический мониторинг обучающихся с результатами около порога.",
            )
        )

    # --- 13 Динамика ---
    dynamics_analysis = []
    if dyn_lines:
        dynamics_analysis.append(_stmt(KIND_FACT, "Фактический ряд динамики: " + "; ".join(dyn_lines) + "."))
    else:
        dynamics_analysis.append(
            _stmt(KIND_FACT, "Сопоставимый многолетний ряд для анализа динамики отсутствует.")
        )
    if delta_participants is not None:
        dynamics_analysis.append(
            _stmt(KIND_FACT, f"Численность участников изменилась на {delta_participants:+d} к предыдущему году.")
        )
    if delta_avg is not None and delta_pass is not None:
        dynamics_analysis.append(
            _stmt(
                KIND_FACT,
                f"Средний результат изменился на {delta_avg:+.2f}, успеваемость — на {delta_pass:+.1f} п.п.",
            )
        )
        if delta_avg < 0 or delta_pass < 0:
            dynamics_analysis.append(
                _stmt(
                    KIND_CONCLUSION,
                    "Динамика указывает на ухудшение хотя бы одного ключевого показателя периода.",
                )
            )
        elif delta_avg > 0 and delta_pass > 0:
            dynamics_analysis.append(
                _stmt(
                    KIND_CONCLUSION,
                    "Динамика указывает на улучшение среднего результата и успеваемости.",
                )
            )

    # --- 09 Факторный анализ (выводы + гипотезы, без выдуманных причин) ---
    factors = [
        {
            "factor": "Качество знаний",
            "impact": "Высокое" if quality < 40 else "Среднее",
            "kind": KIND_CONCLUSION,
            "why": (
                "Низкая доля высоких результатов ограничивает вклад сильного сегмента в итоговый средний показатель."
                if quality < 40
                else "Текущий уровень качества поддерживает стабильность профиля, но не гарантирует ускоренный рост."
            ),
        },
        {
            "factor": "Предметная неоднородность",
            "impact": "Высокое" if len(weak_zones) >= 2 else "Среднее",
            "kind": KIND_CONCLUSION,
            "why": (
                "Разрыв между предметами формирует неравномерный общий профиль результатов."
                if len(weak_zones) >= 1
                else "Межпредметный разрыв по критериям риска выражен слабо."
            ),
        },
        {
            "factor": "Высокобалльные результаты",
            "impact": "Среднее" if high_count > 0 else "Высокое",
            "kind": KIND_FACT if high_count == 0 else KIND_CONCLUSION,
            "why": (
                f"Количество высокобалльных результатов отсутствует ({high_hint})."
                if high_count == 0
                else f"Зафиксировано {high_count} высокобалльных результатов ({high_hint})."
            ),
        },
        {
            "factor": "Пороговая зона",
            "impact": "Высокое" if concentration_near_threshold >= 2 else "Среднее",
            "kind": KIND_HYPOTHESIS if concentration_near_threshold >= 2 else KIND_CONCLUSION,
            "why": (
                "Не исключено влияние концентрации результатов около минимального порога; "
                "для подтверждения требуется анализ распределения по заданиям."
                if concentration_near_threshold >= 2
                else "По данным периода предметы с успеваемостью ниже 75% не определяют общий профиль."
            ),
        },
    ]

    # --- 10 Управленческие риски ---
    management_risks = [
        {
            "type": "Образовательный риск по предметам группы риска",
            "probability": "Высокая" if weak_zones else "Низкая",
            "impact": "Высокое" if weak_zones else "Среднее",
            "priority": "1" if weak_zones else "3",
        },
        {
            "type": "Риск расширения группы риска",
            "probability": "Высокая" if risk_count > max(2, participants * 0.15) else "Средняя",
            "impact": "Высокое",
            "priority": "1" if risk_count > 0 else "3",
        },
        {
            "type": "Риск снижения результатов в следующем цикле",
            "probability": "Высокая" if delta_avg is not None and delta_avg < 0 else "Средняя",
            "impact": "Высокое",
            "priority": "1" if delta_avg is not None and delta_avg < 0 else "2",
        },
        {
            "type": "Риск сохранения низкой доли высоких результатов",
            "probability": "Высокая" if high_count == 0 else "Средняя",
            "impact": "Среднее",
            "priority": "2",
        },
    ]

    # --- 11 Прогноз (только гипотезы) ---
    forecast = [
        _stmt(
            KIND_HYPOTHESIS,
            "Вероятно сохранение текущего уровня результатов при сохранении контроля за предметами риска.",
        ),
        _stmt(
            KIND_HYPOTHESIS,
            "Не исключено улучшение профиля при переносе подтверждённых практик лидирующих предметов в зоны дефицита.",
        ),
        _stmt(
            KIND_HYPOTHESIS,
            "Вероятность ухудшения повышается при ослаблении адресной работы с группой риска; "
            "утверждение требует мониторинга в следующем цикле.",
        ),
        _stmt(
            KIND_DECISION,
            "Постоянно контролировать долю неуспешных результатов, динамику качества знаний и предметную вариативность.",
        ),
    ]

    # --- Управленческие решения ---
    decisions = [
        {
            "role": "Директор",
            "actions": [
                "Утвердить карту рисков по предметам с ежемесячным контролем индикаторов.",
                "Закрепить ответственность за динамику предметов группы риска.",
            ],
        },
        {
            "role": "Заместитель директора",
            "actions": [
                "Организовать дополнительную диагностику обучающихся группы риска.",
                "Обеспечить анализ выполнения заданий по предметам с пониженной успеваемостью.",
            ],
        },
        {
            "role": "Руководители МО и предметные комиссии",
            "actions": [
                "Провести экспертную проверку рабочих программ по предметам риска.",
                "Оценить эффективность подготовки и зафиксировать практики предметов-лидеров.",
            ],
        },
        {
            "role": "Классные руководители",
            "actions": [
                "Согласовать индивидуальные маршруты для обучающихся из группы риска.",
                "Обеспечить регулярную обратную связь по контрольным точкам подготовки.",
            ],
        },
    ]

    # --- План: проблема (факт), гипотеза, решение ---
    plan_rows = [
        {
            "problem": "Неоднородность предметных результатов",
            "cause": "Возможной причиной может быть различие в содержании и контроле подготовки; требуется дополнительный анализ.",
            "action": "Единый цикл разборов результатов и адресных диагностических модулей",
            "owner": "Заместитель директора, руководители МО",
            "effect": "Снижение межпредметного разрыва по фактическим индикаторам",
            "priority": "Высокий",
        },
        {
            "problem": "Наличие обучающихся в группе риска" if risk_count else "Профилактика попадания в группу риска",
            "cause": "Причины на уровне имеющихся данных не подтверждены; требуется дополнительная диагностика.",
            "action": "Индивидуальные маршруты и промежуточная диагностика каждые 3–4 недели",
            "owner": "Предметные комиссии, классные руководители",
            "effect": "Снижение доли результатов около порога",
            "priority": "Срочный" if risk_count else "Средний",
        },
        {
            "problem": (
                "Отсутствие высокобалльных результатов"
                if high_count == 0
                else "Ограниченный сегмент высоких достижений"
            ),
            "cause": "Вероятно, подготовка сосредоточена на преодолении порога; гипотеза требует проверки.",
            "action": "Диагностика потенциально сильных обучающихся и оценка подготовки к заданиям повышенной сложности",
            "owner": "Руководители МО, предметные комиссии",
            "effect": "Рост доли высоких результатов по установленному критерию",
            "priority": "Средний",
        },
    ]

    # --- 14 Итоговое заключение ---
    readiness = "достаточное" if pass_rate >= 80 else "напряжённое"
    final_conclusion = [
        _stmt(
            KIND_CONCLUSION,
            f"По фактическим данным {exam_label} за {year_label} качество подготовки оценивается как {readiness} "
            f"(успеваемость {pass_rate:.1f}%, качество знаний {quality:.1f}%).",
        ),
        _stmt(
            KIND_CONCLUSION,
            "Эффективность управления определяется способностью работать со структурой рисков "
            "и предметной неоднородностью, а не только со средними величинами.",
        ),
        _stmt(
            KIND_DECISION,
            "Система подготовки к следующему циклу должна включать диагностику группы риска, "
            "анализ выполнения заданий по предметам риска и контроль индикаторов динамики.",
        ),
    ]

    conclusion_strengths = [s for s in strengths_analysis if s["kind"] in {KIND_FACT, KIND_CONCLUSION}]
    conclusion_attention = [
        s
        for s in (problems_analysis + risk_group_analysis)
        if s["kind"] in {KIND_FACT, KIND_CONCLUSION}
    ][:6]
    conclusion_overall = [s for s in final_conclusion if s["kind"] in {KIND_FACT, KIND_CONCLUSION}]

    decision_bank = []
    for block in decisions:
        decision_bank.extend(_stmt(KIND_DECISION, a) for a in block["actions"])
    for row in plan_rows:
        decision_bank.append(_stmt(KIND_DECISION, str(row["action"])))

    quality_checks = _quality_self_check(
        sections=[
            executive_summary,
            comprehensive,
            strengths_analysis,
            problems_analysis,
            dynamics_analysis,
            risk_group_analysis,
            forecast,
            final_conclusion,
        ]
        + [sa["items"] for sa in subject_analysis],
        plan_rows=plan_rows,
        decisions=decisions,
    )

    return {
        "executive_summary": executive_summary,
        "comprehensive_analysis": comprehensive,
        "subject_analysis": subject_analysis,
        "strengths_analysis": strengths_analysis,
        "problems_analysis": problems_analysis,
        "dynamics_analysis": dynamics_analysis,
        "risk_group_analysis": risk_group_analysis,
        "factor_analysis": factors,
        "management_risks": management_risks,
        "forecast": forecast,
        "management_decisions": decisions,
        "plan_rows": plan_rows,
        "final_expert_conclusion": final_conclusion,
        "quality_self_check": quality_checks,
        "conclusion_strengths": conclusion_strengths,
        "conclusion_attention": conclusion_attention,
        "conclusion_overall": conclusion_overall,
        "decision_bank": decision_bank,
        "ready": all(c.get("ok") for c in quality_checks),
    }


def _join_stmt_text(items: list[dict[str, str]]) -> str:
    return " ".join(f"[{s['label']}] {s['text']}" for s in items)


def _quality_self_check(
    *,
    sections: list[list[dict[str, str]]],
    plan_rows: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    all_stmts: list[dict[str, str]] = []
    for block in sections:
        all_stmts.extend(block or [])

    texts = [str(s.get("text") or "").lower() for s in all_stmts]
    has_forbidden = any(any(m in t for m in _FORBIDDEN_CAUSE_MARKERS) for t in texts)
    for row in plan_rows:
        cause = str(row.get("cause") or "").lower()
        if any(m in cause for m in ("причиной является", "причина заключается")) and "возможн" not in cause:
            has_forbidden = True

    kinds = {s.get("kind") for s in all_stmts}
    hyp_ok = True
    for s in all_stmts:
        if s.get("kind") == KIND_HYPOTHESIS:
            t = (s.get("text") or "").lower()
            if not any(
                m in t
                for m in (
                    "возможн",
                    "не исключено",
                    "требует",
                    "вероятн",
                    "гипотез",
                    "дополнительн",
                )
            ):
                hyp_ok = False
                break

    plan_actions_ok = all(bool(str(r.get("action") or "").strip()) for r in plan_rows)
    decisions_ok = any(bool(d.get("actions")) for d in decisions)
    facts_ok = KIND_FACT in kinds
    conclusions_ok = KIND_CONCLUSION in kinds
    decisions_kind_ok = KIND_DECISION in kinds or decisions_ok

    checks = [
        ("Все факты подтверждены данными", facts_ok and not has_forbidden),
        ("Все выводы логически следуют из фактов", conclusions_ok and not has_forbidden),
        ("Все причины оформлены как гипотезы", hyp_ok and not has_forbidden),
        ("Все рекомендации направлены на устранение риска", plan_actions_ok and decisions_kind_ok),
        ("Нет неподтверждённых утверждений", not has_forbidden),
        ("Нет шаблонных неподтверждённых причин", not has_forbidden),
        ("Нет логических противоречий категорий", facts_ok and conclusions_ok and decisions_kind_ok),
    ]
    return [{"label": label, "ok": bool(ok)} for label, ok in checks]
