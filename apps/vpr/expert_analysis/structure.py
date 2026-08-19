"""Анализ структуры подготовки и причинно-следственных цепочек."""

from __future__ import annotations

from apps.vpr.conclusion.rules import classify_spread
from apps.vpr.expert_analysis.competences import PLACEHOLDER_SKILLS, PLACEHOLDER_TOPICS
from apps.vpr.expert_analysis.result import CauseChain


def analyze_structure(analysis, summary, groups) -> list[str]:
    texts: list[str] = []
    topic_pcts = []
    for row in analysis.topic_rows or []:
        topic = (getattr(row, "topic", None) or "").strip()
        if topic in PLACEHOLDER_TOPICS:
            continue
        pct = getattr(row, "avg_completion_percent", None)
        if pct is not None:
            topic_pcts.append(float(pct))

    if topic_pcts:
        spread_topics = max(topic_pcts) - min(topic_pcts)
        if spread_topics <= 15:
            texts.append(
                "Подготовка по темам относительно равномерна: разброс средних "
                "процентов выполнения между темами невелик, выраженного дисбаланса разделов нет."
            )
        elif spread_topics >= 35:
            texts.append(
                "Фиксируется выраженный дисбаланс между разделами и темами: "
                f"разница средних результатов достигает {spread_topics:.0f} п.п. "
                "Это снижает устойчивость общего предметного результата."
            )
        else:
            texts.append(
                "Структура подготовки умеренно неоднородна: отдельные темы "
                "освоены заметно лучше других, но системного разрыва ещё нет."
            )

    cv = getattr(summary, "cv_primary_score_percent", None) if summary else None
    spread = classify_spread(cv)
    if spread == "homogeneous":
        texts.append(
            "Индивидуальные результаты относительно однородны, что повышает "
            "устойчивость среднего показателя класса."
        )
    elif spread == "heterogeneous":
        texts.append(
            "Высокая вариативность индивидуальных результатов указывает на "
            "неоднородность класса и снижает предсказуемость итогового профиля."
        )

    if groups:
        gmap = getattr(groups, "groups", None) or {}
        risk = gmap.get("risk")
        high = gmap.get("high")
        risk_pct = float(getattr(risk, "percent", 0) or 0) if risk else 0.0
        high_pct = float(getattr(high, "percent", 0) or 0) if high else 0.0
        if risk_pct >= 20:
            texts.append(
                f"Выраженная группа риска ({risk_pct:.0f}%) формирует нижний полюс "
                "распределения и тянет вниз общий результат."
            )
        if high_pct >= 20:
            texts.append(
                f"Группа высокого уровня ({high_pct:.0f}%) подтверждает наличие "
                "ресурса для повышения качества подготовки."
            )
        if risk_pct < 10 and high_pct < 10:
            texts.append(
                "Класс в основном сосредоточен в средней группе: крайние полюса "
                "выражены слабо."
            )

    if not texts:
        texts.append(
            "Структура подготовки определяется сочетанием тематического профиля "
            "и распределения обучающихся по группам достижений."
        )
    return texts


def build_cause_chains(analysis, patterns, competences) -> tuple[list[CauseChain], list[str]]:
    chains: list[CauseChain] = []
    paragraphs: list[str] = []
    causes = getattr(analysis, "causes", None)

    # Цепочки из тематических паттернов
    for pattern in patterns:
        if pattern.kind == "thematic":
            chains.append(
                CauseChain(
                    steps=[
                        pattern.title,
                        "несформированность связанной предметной компетенции",
                        "снижение результата по группе заданий одного раздела",
                        "влияние на общий средний результат класса",
                    ],
                    summary=pattern.explanation,
                )
            )
        elif pattern.kind == "systemic":
            chains.append(
                CauseChain(
                    steps=[
                        "дефициты в нескольких разделах программы",
                        "системная недостаточность предметной подготовки",
                        "устойчивое снижение качества выполнения работы",
                        "критическое влияние на итоговый профиль класса",
                    ],
                    summary=pattern.explanation,
                )
            )
        elif pattern.kind == "competence":
            chains.append(
                CauseChain(
                    steps=[
                        "низкие результаты по группе умений",
                        "недостаточная сформированность компетенции",
                        "ошибки переносятся на смежные задания",
                        "снижение общего результата",
                    ],
                    summary=pattern.explanation,
                )
            )

    weak_comp = [c for c in competences if c.status == "weak"]
    for comp in weak_comp[:2]:
        chains.append(
            CauseChain(
                steps=[
                    f"тематический/уменийный дефицит в зоне «{comp.name}»",
                    f"несформированность компетенции «{comp.name}»",
                    "влияние на выполнение связанных заданий каталога",
                    "снижение итогового результата по предмету",
                ],
                summary=comp.conclusion,
            )
        )

    if causes is not None:
        summary = getattr(causes, "summary", None)
        dominant = getattr(summary, "dominant_cause_type", None) if summary else None
        dominant_scale = getattr(summary, "dominant_scale", None) if summary else None
        if dominant:
            paragraphs.append(
                f"По данным причинно-следственного анализа доминирует фактор "
                f"«{dominant}» масштаба «{dominant_scale or 'не определён'}». "
                "Он связывает локальные дефициты в единую логику снижения результата."
            )
        # Не дублировать сырые списки причин — только цепочки
        findings = list(getattr(causes, "patterns", None) or [])[:3]
        for item in findings:
            cause = str(getattr(item, "cause", "") or "").strip()
            if not cause:
                continue
            topic = str(getattr(item, "topic", "") or "").strip()
            skill = str(getattr(item, "skill", "") or "").strip()
            steps = []
            if topic and topic not in PLACEHOLDER_TOPICS:
                steps.append(f"тематический дефицит «{topic}»")
            if skill and skill not in PLACEHOLDER_SKILLS:
                steps.append(f"несформированность умения «{skill}»")
            steps.append(cause)
            steps.append("влияние на выполнение связанных заданий")
            steps.append("влияние на общий результат")
            chains.append(CauseChain(steps=steps, summary=cause))

    # уникализация по summary
    seen: set[str] = set()
    unique: list[CauseChain] = []
    for chain in chains:
        key = chain.summary or "|".join(chain.steps)
        if key in seen:
            continue
        seen.add(key)
        unique.append(chain)

    if unique:
        paragraphs.append(
            "Причины результатов рассматриваются как цепочки: от тематического "
            "дефицита к несформированной компетенции и далее — к влиянию на "
            "смежные задания и общий результат."
        )
    else:
        paragraphs.append(
            "Выраженных причинно-следственных цепочек по каталогу не построено: "
            "дефициты носят рассеянный характер либо данных сопоставления недостаточно."
        )
    return unique[:6], paragraphs


def build_strengths_expert(
    *,
    subject: str,
    strong_topics: list[str],
    strong_skills: list[str],
    formed_competences: list[str],
    strong_sections: list[str],
    cognitive_label: str,
    profile_label: str,
) -> list[str]:
    items: list[str] = []
    if strong_topics:
        items.append(
            f"По предмету «{subject}» наиболее устойчиво освоены темы "
            + ", ".join(f"«{t}»" for t in strong_topics[:4])
            + ". Они образуют опорный содержательный каркас подготовки."
        )
    if strong_skills:
        items.append(
            "Наиболее устойчиво сформированы умения "
            + ", ".join(f"«{s}»" for s in strong_skills[:4])
            + ", что подтверждает наличие рабочих способов действий."
        )
    if formed_competences:
        items.append(
            "Сильные компетенции: "
            + ", ".join(f"«{c}»" for c in formed_competences[:4])
            + ". Их сохранность поддерживает общий предметный результат."
        )
    if strong_sections:
        items.append(
            "Сильные разделы программы — "
            + ", ".join(f"«{s}»" for s in strong_sections[:3])
            + " — выполняются стабильно большинством участников."
        )
    items.append(
        f"Когнитивный профиль («{cognitive_label}») и общий профиль подготовки "
        f"(«{profile_label}») показывают, за счёт каких зон класс удерживает результат."
    )
    return items[:8]


def build_problems_expert(
    *,
    subject: str,
    weak_topics: list[str],
    weak_skills: list[str],
    weak_competences: list[str],
    patterns,
    profile_label: str,
) -> list[str]:
    items: list[str] = []
    if weak_topics:
        items.append(
            f"Ключевые предметные дефициты по «{subject}» сосредоточены в темах "
            + ", ".join(f"«{t}»" for t in weak_topics[:4])
            + ". Их влияние выходит за рамки отдельных заданий и снижает средний результат."
        )
    if weak_skills:
        items.append(
            "Проблемные умения "
            + ", ".join(f"«{s}»" for s in weak_skills[:4])
            + " ограничивают выполнение смежных заданий и связанных разделов."
        )
    if weak_competences:
        items.append(
            "Проблемные компетенции — "
            + ", ".join(f"«{c}»" for c in weak_competences[:4])
            + " — определяют системный характер затруднений класса."
        )
    thematic = [p for p in patterns if p.kind in {"thematic", "systemic"}]
    if thematic:
        items.append(thematic[0].explanation)
    items.append(
        f"В условиях профиля «{profile_label}» указанные зоны риска "
        "оказывают наибольшее влияние на устойчивость предметной подготовки."
    )
    return items[:8]
