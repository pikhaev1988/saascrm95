"""
Презентационный слой «Аналитическая справка ГИА — муниципалитет».

Управленческий документ: факт → вывод → гипотеза → решение → эффект.
Только генерация данной справки.
"""

from __future__ import annotations

import json
from typing import Any

from users.report_ui.school_analytic_note import (
    KIND_CONCLUSION,
    KIND_DECISION,
    KIND_FACT,
    KIND_HYPOTHESIS,
    KIND_LABELS,
    _pct_tone,
    _pct_tone_avg,
    _status_icon,
    _status_label,
    _stmt,
    _subject_tone,
)

KIND_EFFECT = "effect"
KIND_LABELS_EXT = {
    **KIND_LABELS,
    KIND_EFFECT: "Ожидаемый эффект",
}


def build_district_analytic_note_presentation(payload: dict[str, Any] | None) -> dict[str, Any]:
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
    subjects_count = int(data.get("subjects_count") or len(data.get("subject_rows") or []) or 0)
    schools_count = int(data.get("schools_count") or len(data.get("school_rows") or []) or 0)
    avg = float(data.get("avg_score") or 0)
    quality = float(data.get("quality_rate") or 0)
    pass_rate = float(data.get("pass_rate") or 0)
    high_count = int(data.get("high_count") or 0)
    risk_count = int(data.get("risk_count") or 0)
    failed_count = int(data.get("failed_count") or 0)
    republic_avg = data.get("republic_avg")
    avg_delta = data.get("avg_delta")
    district_name = data.get("district_name") or "Муниципалитет"

    subjects = []
    max_avg = max((float(r.get("avg") or 0) for r in (data.get("subject_rows") or [])), default=1) or 1
    for row in data.get("subject_rows") or []:
        pr = float(row.get("pass_rate") or 0)
        av = float(row.get("avg") or 0)
        n = int(row.get("participants") or 0)
        tone = _subject_tone(pr, av, is_oge=is_oge)
        subjects.append(
            {
                "name": row.get("exam__subject") or "Предмет",
                "participants": n,
                "avg": round(av, 2),
                "pass_rate": pr,
                "min_v": row.get("min_v"),
                "max_v": row.get("max_v"),
                "tone": tone,
                "status": _status_label(tone),
                "icon": _status_icon(tone),
                "pass_bar": min(max(pr, 0), 100),
                "avg_bar": min(100.0, round(100.0 * av / max_avg, 1)) if max_avg else 0,
                "statistically_stable": n >= 5,
                "weight": round((n / total) * 100, 1) if total else 0.0,
            }
        )

    schools = []
    for row in data.get("school_rows") or []:
        pr = float(row.get("pass_rate") or 0)
        schools.append(
            {
                "name": row.get("student__school__name") or "ОО",
                "code": row.get("student__school__code") or "—",
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

    # Вклад школ/предметов (массовость) — база для паспорта, системного анализа и приоритизации
    for s in schools:
        n = int(s.get("participants") or 0)
        s["weight"] = round((n / participants) * 100, 1) if participants else 0.0
        s["pull"] = round((float(s.get("avg") or 0) - avg) * (n / participants), 3) if participants else 0.0

    clusters = data.get("school_clusters") or _fallback_clusters(schools, participants)
    system_level = _system_level(pass_rate=pass_rate, quality=quality, risk_count=risk_count, schools_count=schools_count)
    regional = data.get("regional_position") if (data.get("regional_position") or {}).get("has_data") else None
    contribution = _contribution_analysis(schools, subjects, avg, participants, total)
    school_deviation = _school_deviation_analysis(schools, avg, participants)
    system_profile = _system_profile(clusters, schools, subjects, participants)
    subject_structure = _subject_structure(subjects, is_oge=is_oge)
    statistical_stability = _statistical_stability(subjects)
    mentoring = _mentoring_pairs(clusters)
    system_analysis = _system_deep_analysis(
        contribution=contribution,
        clusters=clusters,
        subjects=subjects,
        pass_rate=pass_rate,
        avg=avg,
    )
    priorities = _priority_tasks(
        district_name=district_name,
        risk_count=risk_count,
        clusters=clusters,
        subjects=subjects,
        regional=regional,
        avg=avg,
        republic_avg=republic_avg,
        pass_rate=pass_rate,
        contribution=contribution,
    )
    risk_map = _risk_map(clusters, subjects, pass_rate, republic_avg, avg, risk_count)
    expected_effects = _expected_effects(priorities)
    decision_map = _decision_map(priorities)

    achievements = []
    if clusters["leaders"]["count"]:
        achievements.append(f"Школ-лидеров: {clusters['leaders']['count']} (доля участников {clusters['leaders']['share']}%).")
    if high_count:
        achievements.append(f"Высокобалльных результатов ({high_hint}): {high_count}.")
    if avg_delta is not None and float(avg_delta) > 0:
        achievements.append(f"Положительная динамика среднего результата: +{avg_delta}.")
    if not achievements:
        achievements.append("Явные точки превосходства в текущем срезе ограничены.")

    main_risks = []
    if clusters["risk"]["count"]:
        main_risks.append(f"Школ зоны риска: {clusters['risk']['count']}.")
    if subject_structure["priority_attention"]:
        main_risks.append(
            "Предметы приоритетного внимания: "
            + ", ".join(s["name"] for s in subject_structure["priority_attention"][:3])
            + "."
        )
    if republic_avg is not None and avg < float(republic_avg):
        main_risks.append("Средний результат муниципалитета ниже республиканского ориентира.")
    if not main_risks:
        main_risks.append("Критические риски по заданным критериям не выявлены.")

    main_conclusion = (
        f"Муниципальная система {exam_label} оценивается как «{system_level['label']}»: "
        f"средний {avg}, успеваемость {pass_rate}%, школ риска {risk_count}."
    )

    passport = _management_passport(
        district_name=district_name,
        exam_label=exam_label,
        year=data.get("year"),
        system_level=system_level,
        regional=regional,
        achievements=achievements,
        risks=main_risks,
        subjects=subjects,
        clusters=clusters,
        contribution=contribution,
        priorities=priorities,
        avg=avg,
        pass_rate=pass_rate,
        avg_delta=avg_delta,
        republic_avg=republic_avg,
    )

    executive_chain = [
        _stmt(
            KIND_FACT,
            f"Муниципалитет «{district_name}»: участников {participants}, ОО {schools_count}, "
            f"предметов {subjects_count}, средний {avg}, успеваемость {pass_rate}%.",
        ),
        _stmt(KIND_CONCLUSION, main_conclusion),
    ]
    if clusters["risk"]["count"] or clusters["attention"]["count"]:
        executive_chain.append(
            _stmt(
                KIND_HYPOTHESIS,
                "Неоднородность сети ОО может усиливать разрыв между лидерами и школами зоны риска.",
            )
        )
    executive_chain.append(
        _stmt(
            KIND_DECISION,
            "Сфокусировать муниципальное управление на кластерах «Требуют внимания» и «Зона риска» "
            "при сохранении практик школ-лидеров.",
        )
    )
    executive_chain.append(
        _fx("Высокий эффект", "Снижение неоднородности сети и выравнивание предметных зон риска.")
    )

    ui = {
        "has_data": True,
        "scope": "district",
        "district_name": district_name,
        "exam_label": exam_label,
        "year": data.get("year"),
        "avg_label": avg_label,
        "kind_labels": KIND_LABELS_EXT,
        "system_level": system_level,
        "passport": passport,
        "executive": {
            "achievements": achievements,
            "risks": main_risks,
            "main_conclusion": main_conclusion,
            "chain": executive_chain,
        },
        "contribution": contribution,
        "system_analysis": system_analysis,
        "kpi": {
            "participants": participants,
            "total_results": total,
            "subjects_count": subjects_count,
            "schools_count": schools_count,
            "avg_score": data.get("avg_score"),
            "quality_rate": quality,
            "pass_rate": pass_rate,
            "high_count": high_count,
            "risk_count": risk_count,
            "failed_count": failed_count,
            "tones": {
                "participants": "neutral",
                "subjects": "neutral",
                "schools": "neutral",
                "avg": _pct_tone_avg(avg, is_oge=is_oge),
                "quality": _pct_tone(quality, high=45, mid=25),
                "pass": _pct_tone(pass_rate, high=85, mid=70),
                "high": "high" if high_count > 0 else "neutral",
                "risk": "low" if risk_count > 0 else "high",
            },
        },
        "regional_position": regional,
        "has_regional_position": bool(regional),
        "clusters": [
            clusters["leaders"],
            clusters["stable"],
            clusters["attention"],
            clusters["risk"],
        ],
        "school_deviation": school_deviation,
        "system_profile": system_profile,
        "subject_structure": subject_structure,
        "statistical_stability": statistical_stability,
        "mentoring": mentoring,
        "priorities": priorities,
        "risk_map": risk_map,
        "expected_effects": expected_effects,
        "decision_map": decision_map,
        "subjects": subjects,
        "schools": schools,
        "dynamics": dynamics,
        "comparison": {
            "republic_avg": republic_avg,
            "avg_delta": avg_delta,
            "republic_delta": round(avg - float(republic_avg), 2) if republic_avg is not None else None,
        },
        "high_scorers": {
            "count": high_count,
            "tone": "high" if high_count > 0 else "neutral",
            "threshold_hint": high_hint,
        },
        "charts_json": json.dumps(
            {
                "dynYears": [str(r["year"]) for r in dynamics],
                "dynAvg": [float(r["avg"] or 0) for r in dynamics],
                "dynPass": [float(r["pass_rate"] or 0) for r in dynamics],
                "avgMax": 5 if is_oge else 100,
            },
            ensure_ascii=False,
        ),
        "audit": {},
    }
    ui["audit"] = _audit_presentation(ui)
    if not ui["audit"]["ok"]:
        ui = _autofix_presentation(ui)
        ui["audit"] = _audit_presentation(ui)
    return ui


def _fx(level: str, text: str) -> dict[str, str]:
    return {"kind": KIND_EFFECT, "label": KIND_LABELS_EXT[KIND_EFFECT], "text": f"{level}. {text}", "effect_level": level}


def _contribution_analysis(
    schools: list[dict],
    subjects: list[dict],
    municipal_avg: float,
    participants: int,
    total_results: int,
) -> dict[str, Any]:
    """Относительный вклад ОО и предметов с учётом массовости."""
    school_rows = sorted(schools, key=lambda x: float(x.get("weight") or 0), reverse=True)
    subject_rows = sorted(subjects, key=lambda x: float(x.get("weight") or 0), reverse=True)

    # Школы, формирующие основной результат: накопленная доля ≥60% или топ-3
    core_schools = []
    cum = 0.0
    for s in school_rows:
        if not school_rows:
            break
        core_schools.append(s)
        cum += float(s.get("weight") or 0)
        if cum >= 60.0 and len(core_schools) >= 2:
            break
        if len(core_schools) >= max(3, min(5, len(school_rows))):
            break
    if not core_schools and school_rows:
        core_schools = school_rows[:1]

    low_influence = [s for s in school_rows if float(s.get("weight") or 0) < 2.0]
    # Предметы с максимальным влиянием: топ по весу среди устойчивых
    max_influence_subjects = [s for s in subject_rows if s.get("statistically_stable")][:5] or subject_rows[:5]
    # Высокий риск при высокой массовости
    mass_threshold = 8.0
    if subject_rows:
        weights = [float(s.get("weight") or 0) for s in subject_rows]
        median_w = sorted(weights)[len(weights) // 2]
        mass_threshold = max(8.0, median_w)
    high_risk_mass = [
        s
        for s in subject_rows
        if s.get("statistically_stable")
        and s.get("tone") in {"low", "warn"}
        and float(s.get("weight") or 0) >= mass_threshold
    ]

    # Вклад в средний: pull = (avg - municipal_avg) * share
    for s in subject_rows:
        n = int(s.get("participants") or 0)
        share = (n / total_results) if total_results else 0.0
        s["pull"] = round((float(s.get("avg") or 0) - municipal_avg) * share, 3)

    top_pull_up = sorted(school_rows, key=lambda x: float(x.get("pull") or 0), reverse=True)[:3]
    top_pull_down = sorted(school_rows, key=lambda x: float(x.get("pull") or 0))[:3]
    subject_pull_down = sorted(
        [s for s in subject_rows if s.get("statistically_stable")],
        key=lambda x: float(x.get("pull") or 0),
    )[:3]

    large_schools = [s for s in school_rows if float(s.get("weight") or 0) >= 5.0] or school_rows[:5]
    significant_subjects = [s for s in subject_rows if float(s.get("weight") or 0) >= 5.0] or subject_rows[:5]

    chain = [
        _stmt(
            KIND_FACT,
            f"Топ школ по доле участников: "
            + ", ".join(f'{s["name"]} ({s["weight"]}%)' for s in core_schools[:4])
            + f"; накопленная доля ядра ≈ {round(sum(float(s.get('weight') or 0) for s in core_schools), 1)}%.",
        ),
        _stmt(
            KIND_CONCLUSION,
            "Основной результат муниципалитета формируют школы с наибольшей массовостью; "
            "ОО с долей участников <2% практически не влияют на муниципальный средний.",
        ),
        _stmt(
            KIND_CONCLUSION,
            (
                "Максимальное влияние на муниципальный средний оказывают предметы: "
                + ", ".join(f'{s["name"]} (вклад {s["weight"]}%)' for s in max_influence_subjects[:3])
                + "."
            )
            if max_influence_subjects
            else "Недостаточно данных для выделения предметов максимального влияния.",
        ),
    ]
    if high_risk_mass:
        chain.append(
            _stmt(
                KIND_CONCLUSION,
                "Предметы с высоким риском при высокой массовости: "
                + ", ".join(f'{s["name"]} (усп. {s["pass_rate"]}%, вклад {s["weight"]}%)' for s in high_risk_mass[:3])
                + ".",
            )
        )
    chain.append(
        _stmt(
            KIND_DECISION,
            "Приоритизировать управленческие меры по объектам с сочетанием высокой массовости и отрицательного вклада.",
        )
    )
    chain.append(_fx("Высокий эффект", "Рост муниципального среднего за счёт коррекции зон с наибольшим вкладом участников."))

    return {
        "core_schools": core_schools,
        "low_influence_schools": low_influence[:8],
        "large_schools": large_schools,
        "significant_subjects": significant_subjects,
        "max_influence_subjects": max_influence_subjects,
        "high_risk_mass_subjects": high_risk_mass,
        "top_pull_up": top_pull_up,
        "top_pull_down": top_pull_down,
        "subject_pull_down": subject_pull_down,
        "core_share": round(sum(float(s.get("weight") or 0) for s in core_schools), 1),
        "chain": chain,
    }


def _system_deep_analysis(
    *,
    contribution: dict,
    clusters: dict,
    subjects: list[dict],
    pass_rate: float,
    avg: float,
) -> dict[str, Any]:
    """Дополнительный системный уровень анализа муниципалитета."""
    core = contribution.get("core_schools") or []
    low = contribution.get("low_influence_schools") or []
    max_subj = contribution.get("max_influence_subjects") or []
    risk_mass = contribution.get("high_risk_mass_subjects") or []
    pull_down = contribution.get("top_pull_down") or []

    risk_share = float(clusters.get("risk", {}).get("share") or 0)
    att_share = float(clusters.get("attention", {}).get("share") or 0)
    lead_share = float(clusters.get("leaders", {}).get("share") or 0)

    local_problems = []
    systemic_problems = []

    for s in pull_down:
        w = float(s.get("weight") or 0)
        if w < 5.0 and float(s.get("pass_rate") or 100) < 70:
            local_problems.append(
                f'ОО «{s["name"]}»: низкий результат при доле участников {w}% — проблема локальная.'
            )
        elif w >= 5.0 and float(s.get("pass_rate") or 100) < 75:
            systemic_problems.append(
                f'ОО «{s["name"]}»: отрицательный вклад при доле {w}% — влияет на муниципальный средний.'
            )

    for s in risk_mass:
        systemic_problems.append(
            f'Предмет «{s["name"]}»: усп. {s["pass_rate"]}% при вкладе {s["weight"]}% — системный предметный риск.'
        )

    weak_low_mass = [
        s
        for s in subjects
        if s.get("statistically_stable")
        and s.get("tone") in {"low", "warn"}
        and float(s.get("weight") or 0) < 5.0
    ]
    for s in weak_low_mass[:3]:
        local_problems.append(
            f'Предмет «{s["name"]}»: дефицит при малой доле ({s["weight"]}%) — локальный предметный риск.'
        )

    if risk_share + att_share >= 15:
        systemic_problems.append(
            f"Кластеры внимания/риска охватывают {round(risk_share + att_share, 1)}% участников — системная неоднородность сети."
        )
    if lead_share >= 40:
        systemic_problems.append(
            f"Доля участников школ-лидеров {lead_share}% — результат сконцентрирован, система уязвима к смене контингента лидеров."
        )

    if not local_problems:
        local_problems.append("Локальные проблемы с подтверждённым малым вкладом в текущем срезе не выделены.")
    if not systemic_problems:
        systemic_problems.append("Системные проблемы по критерию массовость×дефицит в текущем срезе ограничены.")

    high_effect_decisions = []
    if risk_mass:
        names = ", ".join(s["name"] for s in risk_mass[:2])
        high_effect_decisions.append(
            f"Коррекция массовых проблемных предметов ({names}) — наибольший ожидаемый вклад в муниципальный средний."
        )
    if systemic_problems and any("отрицательный вклад" in p for p in systemic_problems):
        high_effect_decisions.append(
            "Адресное сопровождение крупных ОО с отрицательным вкладом — прямое влияние на муниципальный результат."
        )
    if clusters.get("risk", {}).get("count"):
        high_effect_decisions.append(
            "Стабилизация школ зоны риска при ненулевой доле участников — снижение системного провала снизу."
        )
    if not high_effect_decisions:
        high_effect_decisions.append(
            "Тиражирование практик лидеров на кластер внимания — потенциал роста без критических провалов."
        )

    chain = [
        _stmt(
            KIND_FACT,
            f"Ядро результата: {len(core)} ОО (доля ≈ {contribution.get('core_share')}%); "
            f"слабо влияющих ОО (<2%): {len(low)}; "
            f"предметов макс. влияния: {len(max_subj)}; "
            f"риск×массовость: {len(risk_mass)}.",
        ),
        _stmt(
            KIND_CONCLUSION,
            "Школы, формирующие основной результат: "
            + (", ".join(s["name"] for s in core[:5]) if core else "не выделены")
            + ".",
        ),
        _stmt(
            KIND_CONCLUSION,
            "Школы с практически нулевым влиянием на общий результат: "
            + (", ".join(s["name"] for s in low[:5]) if low else "не выделены")
            + ".",
        ),
        _stmt(
            KIND_CONCLUSION,
            "Локальные проблемы: " + " ".join(local_problems[:3]),
        ),
        _stmt(
            KIND_CONCLUSION,
            "Системные проблемы: " + " ".join(systemic_problems[:3]),
        ),
        _stmt(
            KIND_DECISION,
            "Сосредоточить ресурсы на решениях с наибольшим эффектом: " + " ".join(high_effect_decisions[:2]),
        ),
        _fx("Высокий эффект", "Смещение фокуса с локальных точечных кейсов на системные зоны массового вклада."),
    ]
    return {
        "core_schools": core,
        "low_influence_schools": low,
        "max_influence_subjects": max_subj,
        "high_risk_mass_subjects": risk_mass,
        "local_problems": local_problems,
        "systemic_problems": systemic_problems,
        "high_effect_decisions": high_effect_decisions,
        "chain": chain,
    }


def _management_passport(
    *,
    district_name: str,
    exam_label: str,
    year,
    system_level: dict,
    regional: dict | None,
    achievements: list[str],
    risks: list[str],
    subjects: list[dict],
    clusters: dict,
    contribution: dict,
    priorities: list[dict],
    avg: float,
    pass_rate: float,
    avg_delta,
    republic_avg,
) -> dict[str, Any]:
    """Одностраничный управленческий паспорт (до основной справки)."""
    rating_lines = []
    if regional and regional.get("positions"):
        pos = regional["positions"]
        labels = {
            "avg_score": "средний",
            "quality_rate": "качество",
            "pass_rate": "успеваемость",
            "high_count": "высокобалльники",
            "avg_delta": "динамика",
        }
        for key, title in labels.items():
            p = pos.get(key)
            if p:
                rating_lines.append(f"{title}: {p.get('place')} из {p.get('total')}")
    else:
        rating_lines.append("Межмуниципальный рейтинг недоступен (недостаточно данных по региону).")

    key_subjects = []
    for s in (contribution.get("max_influence_subjects") or subjects)[:4]:
        key_subjects.append(
            {
                "name": s.get("name"),
                "pass_rate": s.get("pass_rate"),
                "weight": s.get("weight"),
                "tone": s.get("tone"),
                "status": s.get("status"),
            }
        )

    leaders = list(clusters.get("leaders", {}).get("schools") or [])[:5]
    if not leaders:
        leaders = list(contribution.get("top_pull_up") or [])[:5]

    support = list(clusters.get("risk", {}).get("schools") or [])[:3]
    support += list(clusters.get("attention", {}).get("schools") or [])[:3]
    if not support:
        support = list(contribution.get("top_pull_down") or [])[:5]
    # unique by name
    seen = set()
    support_unique = []
    for s in support:
        name = s.get("name")
        if name in seen:
            continue
        seen.add(name)
        support_unique.append(s)

    growth = []
    if clusters.get("attention", {}).get("count"):
        growth.append(
            f"Потенциал роста: вывод {clusters['attention']['count']} ОО кластера внимания "
            f"(доля участников {clusters['attention']['share']}%) в стабильный коридор."
        )
    risk_mass = contribution.get("high_risk_mass_subjects") or []
    if risk_mass:
        growth.append(
            "Потенциал роста по массовым предметам: "
            + ", ".join(s["name"] for s in risk_mass[:3])
            + "."
        )
    if avg_delta is not None and float(avg_delta) < 0:
        growth.append(f"Восстановление динамики среднего (текущее отклонение {avg_delta}).")
    if republic_avg is not None and avg < float(republic_avg):
        growth.append(f"Сокращение отставания от республики (муниципалитет {avg}, республика {republic_avg}).")
    if not growth:
        growth.append("Потенциал роста — закрепление уровня лидеров и профилактика перехода внимания → риск.")

    top3 = []
    for t in (priorities or [])[:3]:
        top3.append(
            {
                "priority": t.get("priority"),
                "problem": t.get("problem"),
                "action": t.get("action"),
                "effect": t.get("expected_effect") or t.get("effect_level"),
                "impact_scale": t.get("impact_scale"),
            }
        )

    return {
        "district_name": district_name,
        "exam_label": exam_label,
        "year": year,
        "system_level": system_level,
        "rating_lines": rating_lines,
        "achievements": achievements[:4],
        "risks": risks[:4],
        "key_subjects": key_subjects,
        "leader_schools": leaders,
        "support_schools": support_unique[:5],
        "growth_potential": growth[:4],
        "top_decisions": top3,
        "snapshot": f"Средний {avg} · успеваемость {pass_rate}% · оценка «{system_level.get('label')}»",
    }


def _system_level(*, pass_rate: float, quality: float, risk_count: int, schools_count: int) -> dict[str, str]:
    risk_share = (risk_count / schools_count) if schools_count else 0
    if pass_rate >= 85 and quality >= 40 and risk_share <= 0.05:
        return {"code": "high", "label": "Высокий", "icon": "🟢", "tone": "high"}
    if pass_rate >= 75 and risk_share <= 0.15:
        return {"code": "sufficient", "label": "Достаточный", "icon": "🟡", "tone": "mid"}
    if pass_rate >= 60 or risk_share <= 0.3:
        return {"code": "attention", "label": "Требует внимания", "icon": "🟠", "tone": "warn"}
    return {"code": "critical", "label": "Критический", "icon": "🔴", "tone": "low"}


def _fallback_clusters(schools: list[dict], total_participants: int) -> dict:
    buckets = {"leaders": [], "stable": [], "attention": [], "risk": []}
    for s in schools:
        pr = float(s.get("pass_rate") or 0)
        item = {**s}
        if pr >= 85:
            buckets["leaders"].append(item)
        elif pr >= 70:
            buckets["stable"].append(item)
        elif pr >= 50:
            buckets["attention"].append(item)
        else:
            buckets["risk"].append(item)

    def pack(key, title, feature):
        rows = buckets[key]
        parts = sum(int(r.get("participants") or 0) for r in rows)
        avg = round(sum(float(r.get("avg") or 0) for r in rows) / len(rows), 2) if rows else None
        share = round((parts / total_participants) * 100, 1) if total_participants and rows else 0.0
        return {
            "key": key,
            "title": title,
            "count": len(rows),
            "avg": avg,
            "participants": parts,
            "share": share,
            "feature": feature,
            "schools": rows[:8],
        }

    return {
        "leaders": pack("leaders", "Лидеры", "Высокая успеваемость и устойчивый средний результат."),
        "stable": pack("stable", "Стабильные", "Результаты в пределах приемлемого муниципального коридора."),
        "attention": pack("attention", "Требуют внимания", "Успеваемость ниже целевого уровня."),
        "risk": pack("risk", "Зона риска", "Критически низкая успеваемость."),
    }


def _school_deviation_analysis(schools: list[dict], municipal_avg: float, participants: int) -> dict[str, Any]:
    if not schools:
        return {"has_data": False, "chain": []}
    sorted_by_avg = sorted(schools, key=lambda x: float(x.get("avg") or 0), reverse=True)
    top = sorted_by_avg[: max(1, min(3, len(sorted_by_avg)))]
    bottom = list(reversed(sorted_by_avg[-max(1, min(3, len(sorted_by_avg))) :]))
    top_share = round(sum(int(s.get("participants") or 0) for s in top) / participants * 100, 1) if participants else 0
    bottom_share = round(sum(int(s.get("participants") or 0) for s in bottom) / participants * 100, 1) if participants else 0
    top_names = ", ".join(s["name"] for s in top)
    bottom_names = ", ".join(s["name"] for s in bottom)

    if top_share >= 35 and float(top[0].get("avg") or 0) > municipal_avg:
        core = (
            f"Высокие результаты муниципалитета в значительной мере обеспечиваются ограниченной группой "
            f"школ-лидеров ({top_names}; доля участников {top_share}%)."
        )
    elif bottom_share >= 25 and float(bottom[0].get("avg") or 0) < municipal_avg:
        core = (
            f"Основную часть отклонения муниципального среднего результата вниз формируют "
            f"несколько образовательных организаций ({bottom_names}; доля участников {bottom_share}%)."
        )
    else:
        core = (
            "Отклонение муниципального среднего распределено между несколькими ОО; "
            "нет доминирующего вклада одной-двух школ."
        )

    chain = [
        _stmt(KIND_FACT, f"Муниципальный средний: {municipal_avg}. Лидеры по среднему: {top_names}."),
        _stmt(KIND_CONCLUSION, core),
        _stmt(
            KIND_HYPOTHESIS,
            "Концентрация результата в узкой группе школ повышает уязвимость муниципальной системы к смене контингента.",
        )
        if top_share >= 35
        else _stmt(
            KIND_HYPOTHESIS,
            "При сохранении вклада школ с низким результатом муниципальный средний будет удерживаться снизу.",
        ),
        _stmt(
            KIND_DECISION,
            "Сочетать тиражирование практик лидеров с адресным сопровождением ОО, формирующих отрицательное отклонение.",
        ),
        _fx("Средний эффект", "Снижение зависимости муниципалитета от узкой группы школ."),
    ]
    return {
        "has_data": True,
        "top_share": top_share,
        "bottom_share": bottom_share,
        "top_names": top_names,
        "bottom_names": bottom_names,
        "chain": chain,
    }


def _system_profile(clusters: dict, schools: list[dict], subjects: list[dict], participants: int) -> dict[str, Any]:
    risk_n = int(clusters["risk"]["count"])
    att_n = int(clusters["attention"]["count"])
    lead_n = int(clusters["leaders"]["count"])
    total_n = max(len(schools), 1)
    lead_share = float(clusters["leaders"].get("share") or 0)
    risk_share = float(clusters["risk"].get("share") or 0)
    weak_subjects = [s for s in subjects if s.get("tone") in {"low", "warn"} and s.get("statistically_stable")]

    traits = []
    if risk_n + att_n >= max(2, total_n * 0.35):
        traits.append("неоднородными")
    else:
        traits.append("относительно сбалансированными")
    if lead_share >= 35:
        traits.append("сконцентрированными у лидеров")
    if risk_n == 0 and att_n <= max(1, total_n * 0.2):
        traits.append("устойчивыми")
    else:
        traits.append("требующими стабилизации")

    chain = [
        _stmt(
            KIND_FACT,
            f"Кластеры: лидеры {lead_n}, стабильные {clusters['stable']['count']}, "
            f"внимание {att_n}, риск {risk_n}; доля участников лидеров {lead_share}%, риска {risk_share}%.",
        ),
        _stmt(
            KIND_CONCLUSION,
            "Результаты муниципальной системы являются " + ", ".join(traits) + ".",
        ),
        _stmt(
            KIND_HYPOTHESIS,
            "При сохранении текущей структуры кластеров разрыв между лидерами и зоной риска может закрепиться."
            if risk_n or att_n
            else "При сохранении текущей структуры система способна удерживать достигнутый уровень.",
        ),
        _stmt(
            KIND_DECISION,
            "Утвердить дифференцированную муниципальную политику: поддержка риска/внимания и методический обмен с лидерами.",
        ),
        _fx("Высокий эффект", "Повышение сбалансированности муниципальной сети ОО."),
    ]
    return {
        "traits": traits,
        "weak_subjects_count": len(weak_subjects),
        "chain": chain,
    }


def _subject_structure(subjects: list[dict], *, is_oge: bool) -> dict[str, Any]:
    stable = [s for s in subjects if s.get("statistically_stable")]
    strong = [s for s in stable if s.get("tone") == "high"]
    attention = [s for s in stable if s.get("tone") in {"warn", "low"}]
    # influence by participant weight among weak/strong
    priority_attention = sorted(
        attention,
        key=lambda x: (0 if x.get("tone") == "low" else 1, -float(x.get("weight") or 0), float(x.get("pass_rate") or 0)),
    )[:5]
    priority_strong = sorted(strong, key=lambda x: (-float(x.get("weight") or 0), -float(x.get("pass_rate") or 0)))[:5]
    unstable = [s for s in subjects if not s.get("statistically_stable")]

    why = []
    for s in priority_attention[:3]:
        why.append(
            f'{s["name"]}: успеваемость {s["pass_rate"]}%, доля результатов {s["weight"]}% — '
            "предмет одновременно слабый и заметный по вкладу в муниципальный срез."
        )

    chain = [
        _stmt(
            KIND_FACT,
            f"Статистически устойчивых предметов: {len(stable)}; сильных: {len(strong)}; "
            f"требующих внимания: {len(attention)}; с малой выборкой: {len(unstable)}.",
        ),
        _stmt(
            KIND_CONCLUSION,
            (
                "Приоритетные предметы внимания: " + ", ".join(s["name"] for s in priority_attention) + "."
                if priority_attention
                else "Предметы критического внимания среди устойчивых выборок не выделены."
            ),
        ),
    ]
    if why:
        chain.append(_stmt(KIND_CONCLUSION, "Почему приоритетны: " + " ".join(why)))
    if attention:
        chain.append(
            _stmt(
                KIND_HYPOTHESIS,
                "Слабые предметы с высокой долей участников могут удерживать муниципальный средний снизу.",
            )
        )
    chain.append(
        _stmt(
            KIND_DECISION,
            "Сконцентрировать муниципальные методические сессии на приоритетных предметах внимания "
            "и закрепить практики сильных предметов.",
        )
    )
    chain.append(_fx("Высокий эффект", "Рост успеваемости по предметам с наибольшим вкладом в муниципальный результат."))
    return {
        "strong": priority_strong,
        "priority_attention": priority_attention,
        "unstable": unstable,
        "chain": chain,
    }


def _statistical_stability(subjects: list[dict]) -> dict[str, Any]:
    unstable = [s for s in subjects if not s.get("statistically_stable")]
    chain = [
        _stmt(
            KIND_FACT,
            f"Предметов с числом участников менее 5: {len(unstable)}"
            + (
                " (" + ", ".join(s["name"] for s in unstable[:6]) + ")."
                if unstable
                else "."
            ),
        )
    ]
    if unstable:
        chain.append(
            _stmt(
                KIND_CONCLUSION,
                "Полученные результаты по указанным предметам не позволяют сделать статистически устойчивые выводы "
                "вследствие малого количества участников.",
            )
        )
        chain.append(
            _stmt(
                KIND_DECISION,
                "Не использовать малые выборки как основание для жёстких управленческих санкций; "
                "применять мониторинговый режим.",
            )
        )
        chain.append(_fx("Ограниченный эффект", "Снижение риска ошибочных решений по малым выборкам."))
    else:
        chain.append(
            _stmt(
                KIND_CONCLUSION,
                "Все предметы текущего среза имеют выборку ≥5 участников и допускают устойчивую интерпретацию.",
            )
        )
    return {"unstable": unstable, "has_unstable": bool(unstable), "chain": chain}


def _mentoring_pairs(clusters: dict) -> dict[str, Any]:
    mentors = list(clusters.get("leaders", {}).get("schools") or [])
    mentees = list(clusters.get("risk", {}).get("schools") or []) + list(
        clusters.get("attention", {}).get("schools") or []
    )
    pairs = []
    for i, mentee in enumerate(mentees[:5]):
        if not mentors:
            break
        mentor = mentors[i % len(mentors)]
        pairs.append(
            {
                "mentor": mentor.get("name"),
                "mentor_avg": mentor.get("avg"),
                "mentor_pass": mentor.get("pass_rate"),
                "mentee": mentee.get("name"),
                "mentee_avg": mentee.get("avg"),
                "mentee_pass": mentee.get("pass_rate"),
                "basis": (
                    f"Наставник имеет успеваемость {mentor.get('pass_rate')}% при среднем {mentor.get('avg')}; "
                    f"сопровождаемая ОО — успеваемость {mentee.get('pass_rate')}% при среднем {mentee.get('avg')}."
                ),
            }
        )
    chain = [
        _stmt(
            KIND_FACT,
            f"Потенциальных наставников (лидеры): {len(mentors)}; ОО, нуждающихся в сопровождении: {len(mentees)}.",
        )
    ]
    if pairs:
        chain.append(
            _stmt(
                KIND_CONCLUSION,
                "Возможно сформировать пары наставничества на основе фактического разрыва результатов.",
            )
        )
        chain.append(
            _stmt(
                KIND_DECISION,
                "Утвердить муниципальную модель наставничества по предложенным парам и закрепить кураторов.",
            )
        )
        chain.append(_fx("Средний эффект", "Перенос рабочих практик лидеров в школы зоны внимания/риска."))
    else:
        chain.append(
            _stmt(
                KIND_CONCLUSION,
                "Недостаточно оснований для формирования пар наставничества в текущем срезе.",
            )
        )
    return {"pairs": pairs, "has_pairs": bool(pairs), "chain": chain}


def _priority_tasks(
    *,
    district_name: str,
    risk_count: int,
    clusters: dict,
    subjects: list[dict],
    regional: dict | None,
    avg: float,
    republic_avg,
    pass_rate: float,
    contribution: dict | None = None,
) -> list[dict[str, Any]]:
    """Системная приоритизация: тяжесть проблемы × масштаб влияния (массовость)."""
    tasks: list[dict[str, Any]] = []
    contribution = contribution or {}
    risk_share = float(clusters.get("risk", {}).get("share") or 0)
    att_share = float(clusters.get("attention", {}).get("share") or 0)
    lead_share = float(clusters.get("leaders", {}).get("share") or 0)
    risk_mass = contribution.get("high_risk_mass_subjects") or []
    core_share = float(contribution.get("core_share") or 0)
    pull_down = contribution.get("top_pull_down") or []

    effect_score = {"Высокий эффект": 3, "Средний эффект": 2, "Ограниченный эффект": 1}

    def add(
        problem: str,
        basis: str,
        owner: str,
        effect: str,
        action: str,
        *,
        impact_share: float,
        severity: float,
        term: str = "30–60 дней",
    ):
        # impact_score: масштаб (доля участников/вклада) × тяжесть × качественный эффект
        scale_pts = min(3.0, max(0.5, impact_share / 10.0))
        sev_pts = min(3.0, max(0.5, severity))
        score = round(scale_pts * sev_pts * effect_score.get(effect, 1), 2)
        if impact_share >= 20:
            impact_scale = "Муниципальный"
        elif impact_share >= 8:
            impact_scale = "Существенный"
        elif impact_share >= 3:
            impact_scale = "Локально-значимый"
        else:
            impact_scale = "Ограниченный"
        tasks.append(
            {
                "problem": problem,
                "basis": basis,
                "owner": owner,
                "expected_effect": effect,
                "action": action,
                "term": term,
                "status": "К запуску",
                "effect_level": effect,
                "impact_share": round(impact_share, 1),
                "impact_scale": impact_scale,
                "impact_score": score,
                "justification": (
                    f"Масштаб влияния {impact_scale} (охват ≈ {round(impact_share, 1)}%); "
                    f"ожидаемый эффект «{effect}»; основание подтверждено показателями среза."
                ),
            }
        )

    if clusters["risk"]["count"] and risk_share > 0:
        add(
            "Школы зоны риска удерживают муниципальный результат снизу",
            f"Кластер риска: {clusters['risk']['count']} ОО, доля участников {risk_share}%.",
            "Руководитель управления образования",
            "Высокий эффект",
            "Запустить адресное сопровождение школ зоны риска с ежемесячным мониторингом.",
            impact_share=risk_share,
            severity=3.0,
            term="14–45 дней",
        )
    if clusters["attention"]["count"] and att_share > 0:
        add(
            "Группа ОО «требуют внимания» может перейти в зону риска",
            f"Кластер внимания: {clusters['attention']['count']} ОО, доля участников {att_share}%.",
            "Кураторы муниципалитета",
            "Высокий эффект",
            "Утвердить профилактические планы коррекции для каждой ОО кластера внимания.",
            impact_share=att_share,
            severity=2.2,
        )
    if risk_mass:
        names = ", ".join(s["name"] for s in risk_mass[:3])
        mass = sum(float(s.get("weight") or 0) for s in risk_mass[:3])
        add(
            "Массовые проблемные предметы снижают муниципальный средний",
            f"Предметы риск×массовость: {names} (суммарный вклад ≈ {round(mass, 1)}%).",
            "Методические объединения",
            "Высокий эффект",
            "Провести муниципальные предметные сессии по предметам с сочетанием низкой успеваемости и высокой доли участников.",
            impact_share=mass,
            severity=2.8,
        )
    else:
        weak = [s for s in subjects if s.get("statistically_stable") and s.get("tone") in {"low", "warn"}]
        if weak:
            names = ", ".join(s["name"] for s in weak[:3])
            mass = sum(float(s.get("weight") or 0) for s in weak[:3])
            add(
                "Предметные зоны снижают муниципальную успеваемость",
                f"Проблемные устойчивые предметы: {names} (вклад ≈ {round(mass, 1)}%).",
                "Методические объединения",
                "Высокий эффект" if mass >= 8 else "Средний эффект",
                "Провести муниципальные предметные сессии и анализ типичных дефицитов по приоритетным предметам.",
                impact_share=max(mass, 3.0),
                severity=2.0 if mass < 8 else 2.5,
            )

    large_negative = [s for s in pull_down if float(s.get("weight") or 0) >= 5 and float(s.get("pull") or 0) < 0]
    if large_negative:
        names = ", ".join(s["name"] for s in large_negative[:3])
        mass = sum(float(s.get("weight") or 0) for s in large_negative[:3])
        add(
            "Крупные ОО с отрицательным вкладом тянут муниципальный средний вниз",
            f"ОО: {names}; суммарная доля участников ≈ {round(mass, 1)}%.",
            "Руководитель управления образования",
            "Высокий эффект",
            "Утвердить адресные планы для крупных ОО с отрицательным вкладом в муниципальный средний.",
            impact_share=mass,
            severity=2.7,
        )

    if clusters["leaders"]["count"] and lead_share > 0:
        add(
            "Практики лидеров не тиражируются системно",
            f"Лидеров: {clusters['leaders']['count']}, доля участников {lead_share}%.",
            "Методические службы",
            "Средний эффект",
            "Организовать наставничество «лидер → школа сопровождения» по утверждённым парам.",
            impact_share=min(lead_share, 25.0),
            severity=1.5,
        )
    if republic_avg is not None and avg < float(republic_avg):
        add(
            "Отставание от республиканского среднего",
            f"Муниципалитет {avg}, республика {republic_avg}.",
            "Руководитель управления образования",
            "Средний эффект",
            "Включить целевой показатель сокращения отставания в муниципальный план ГИА.",
            impact_share=max(core_share, 15.0),
            severity=2.0,
        )
    if regional and regional.get("positions", {}).get("pass_rate"):
        pos = regional["positions"]["pass_rate"]
        if int(pos.get("place") or 99) > max(3, int(pos.get("total") or 1) // 2):
            add(
                "Низкая позиция муниципалитета по успеваемости среди районов",
                f"Место {pos['place']} из {pos['total']} по успеваемости.",
                "Аналитическая служба муниципалитета",
                "Средний эффект",
                "Разобрать факторы отставания относительно сопоставимых муниципалитетов региона.",
                impact_share=12.0,
                severity=1.8,
            )
    if pass_rate < 75:
        add(
            "Муниципальная успеваемость ниже целевого коридора",
            f"Успеваемость {pass_rate}%.",
            "Заместитель руководителя по качеству образования",
            "Высокий эффект",
            "Ввести единый график пробных работ и разборов ошибок по ОО внимания/риска.",
            impact_share=max(risk_share + att_share, 20.0),
            severity=2.4,
        )
    add(
        "Недостаточная прозрачность исполнения планов коррекции",
        "Требуется единая карта управленческих решений с ответственными и сроками.",
        "Аппарат управления образования",
        "Средний эффект",
        "Ввести ежемесячный статус исполнения карты управленческих решений.",
        impact_share=10.0,
        severity=1.2,
        term="30 дней",
    )
    unstable = [s for s in subjects if not s.get("statistically_stable")]
    if unstable:
        add(
            "Риск решений по малым предметным выборкам",
            f"Предметов с выборкой <5: {len(unstable)}.",
            "Аналитическая служба муниципалитета",
            "Ограниченный эффект",
            "Разделить предметы на устойчивые и мониторинговые при принятии решений.",
            impact_share=max(sum(float(s.get("weight") or 0) for s in unstable), 1.0),
            severity=1.0,
        )
    add(
        "Недостаточная связка «предмет — школа — мероприятие»",
        f"Муниципалитет «{district_name}» требует пакетной модели управления качеством ГИА.",
        "Руководитель управления образования",
        "Высокий эффект",
        "Утвердить пакетную модель: кластер ОО + приоритетный предмет + куратор + срок.",
        impact_share=max(core_share, 18.0),
        severity=1.6,
        term="45 дней",
    )

    fillers = [
        (
            "Недостаточный мониторинг динамики по ОО",
            "Требуется регулярное сопоставление динамики кластеров между циклами ГИА.",
            "Аналитическая служба муниципалитета",
            "Средний эффект",
            "Закрепить квартальный мониторинг динамики кластеров ОО.",
            8.0,
            1.1,
        ),
        (
            "Слабая координация предметных методических объединений",
            f"В срезе {len(subjects)} предметов; нужна единая муниципальная повестка.",
            "Методические объединения",
            "Средний эффект",
            "Утвердить единый календарь муниципальных предметных разборов.",
            10.0,
            1.2,
        ),
        (
            "Риск потери практик школ-лидеров",
            f"Лидеров: {clusters['leaders']['count']}.",
            "Методические службы",
            "Ограниченный эффект",
            "Зафиксировать и тиражировать 2–3 рабочие практики лидеров.",
            min(lead_share, 15.0) or 5.0,
            1.0,
        ),
    ]
    used = {t["problem"] for t in tasks}
    for problem, basis, owner, effect, action, share, sev in fillers:
        if len(tasks) >= 12:
            break
        if problem in used:
            continue
        add(problem, basis, owner, effect, action, impact_share=share, severity=sev)
        used.add(problem)

    # Ранжирование по ожидаемому влиянию на муниципальный результат
    tasks.sort(key=lambda x: (-float(x.get("impact_score") or 0), -float(x.get("impact_share") or 0)))
    for i, t in enumerate(tasks[:10], start=1):
        t["priority"] = i
    return tasks[:10]


def _risk_map(clusters, subjects, pass_rate, republic_avg, avg, risk_count) -> list[dict[str, Any]]:
    rows = []
    if clusters["risk"]["count"]:
        rows.append(
            {
                "category": "образовательные",
                "risk": "Критически низкая успеваемость в школах зоны риска",
                "probability": "Высокая",
                "impact": "Высокое",
                "priority": 1,
            }
        )
    weak = [s for s in subjects if s.get("statistically_stable") and s.get("tone") in {"low", "warn"}]
    if weak:
        rows.append(
            {
                "category": "методические",
                "risk": "Устойчивые предметные дефициты муниципалитета",
                "probability": "Высокая",
                "impact": "Высокое",
                "priority": 1,
            }
        )
    if clusters["attention"]["count"]:
        rows.append(
            {
                "category": "организационные",
                "risk": "Переход школ кластера внимания в зону риска",
                "probability": "Средняя",
                "impact": "Высокое",
                "priority": 2,
            }
        )
    if republic_avg is not None and avg < float(republic_avg):
        rows.append(
            {
                "category": "управленческие",
                "risk": "Закрепление отставания от республиканского уровня",
                "probability": "Средняя",
                "impact": "Среднее",
                "priority": 2,
            }
        )
    if pass_rate < 70:
        rows.append(
            {
                "category": "управленческие",
                "risk": "Недостаточная управляемость качества подготовки к ГИА",
                "probability": "Высокая" if risk_count else "Средняя",
                "impact": "Высокое",
                "priority": 1,
            }
        )
    if not rows:
        rows.append(
            {
                "category": "управленческие",
                "risk": "Риск потери динамики без профилактического контроля",
                "probability": "Низкая",
                "impact": "Среднее",
                "priority": 3,
            }
        )
    rows.sort(key=lambda x: int(x["priority"]))
    return rows


def _expected_effects(priorities: list[dict]) -> list[dict[str, Any]]:
    out = []
    for t in priorities[:8]:
        out.append(
            {
                "action": t["action"],
                "improves": t["problem"],
                "reduces_risks": t["basis"],
                "effect_level": t["effect_level"],
                "chain": [
                    _stmt(KIND_FACT, t["basis"]),
                    _stmt(KIND_CONCLUSION, f"Проблема: {t['problem']}."),
                    _stmt(KIND_DECISION, t["action"]),
                    _fx(t["effect_level"], "Качественный эффект от реализации мероприятия."),
                ],
            }
        )
    return out


def _decision_map(priorities: list[dict]) -> list[dict[str, Any]]:
    return [
        {
            "priority": t["priority"],
            "problem": t["problem"],
            "action": t["action"],
            "owner": t["owner"],
            "term": t["term"],
            "effect": t["effect_level"],
            "status": t["status"],
            "impact_scale": t.get("impact_scale"),
            "justification": t.get("justification"),
        }
        for t in priorities
    ]


def _audit_presentation(ui: dict[str, Any]) -> dict[str, Any]:
    issues = []
    if not ui.get("passport"):
        issues.append("нет управленческого паспорта")
    if not ui.get("executive", {}).get("main_conclusion"):
        issues.append("нет главного управленческого вывода")
    if not ui.get("decision_map"):
        issues.append("нет карты решений")
    if not ui.get("priorities"):
        issues.append("нет приоритетных задач")
    if not ui.get("risk_map"):
        issues.append("нет карты рисков")
    if not ui.get("contribution"):
        issues.append("нет анализа вклада")
    if not ui.get("system_analysis"):
        issues.append("нет системного анализа")
    banned = ("необходимо улучшить качество", "усилить работу", "продолжить работу в том же направлении")
    blob = json.dumps(ui.get("priorities") or [], ensure_ascii=False).lower()
    if any(b in blob for b in banned):
        issues.append("шаблонные рекомендации")
    for key in ("school_deviation", "system_profile", "subject_structure", "contribution", "system_analysis"):
        chain = (ui.get(key) or {}).get("chain") or []
        kinds = {c.get("kind") for c in chain}
        if KIND_FACT not in kinds or KIND_DECISION not in kinds:
            issues.append(f"нарушена цепочка в {key}")
    # системная приоритизация: у задач должны быть масштаб и обоснование
    for t in (ui.get("priorities") or [])[:3]:
        if not t.get("impact_scale") or not t.get("justification"):
            issues.append("нет системной приоритизации задач")
            break
    return {"ok": not issues, "issues": issues}


def _autofix_presentation(ui: dict[str, Any]) -> dict[str, Any]:
    if not ui.get("decision_map") and ui.get("priorities"):
        ui["decision_map"] = _decision_map(ui["priorities"])
    if not ui.get("risk_map"):
        ui["risk_map"] = [
            {
                "category": "управленческие",
                "risk": "Недостаточная формализация управленческих решений",
                "probability": "Средняя",
                "impact": "Среднее",
                "priority": 2,
            }
        ]
    exec_ = ui.setdefault("executive", {})
    if not exec_.get("main_conclusion"):
        exec_["main_conclusion"] = "Требуется сфокусировать управление на зонах риска и приоритетных предметах."
    if not ui.get("passport"):
        ui["passport"] = {
            "district_name": ui.get("district_name"),
            "exam_label": ui.get("exam_label"),
            "year": ui.get("year"),
            "system_level": ui.get("system_level") or {},
            "rating_lines": ["Рейтинг уточняется"],
            "achievements": exec_.get("achievements") or [],
            "risks": exec_.get("risks") or [],
            "key_subjects": [],
            "leader_schools": [],
            "support_schools": [],
            "growth_potential": ["Требуется уточнение потенциала роста по данным среза."],
            "top_decisions": (ui.get("priorities") or [])[:3],
            "snapshot": exec_.get("main_conclusion") or "",
        }
    for t in ui.get("priorities") or []:
        t.setdefault("impact_scale", "Существенный")
        t.setdefault(
            "justification",
            "Приоритет определён по сочетанию подтверждённой проблемы и ожидаемого влияния на муниципальный результат.",
        )
    return ui
