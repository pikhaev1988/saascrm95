"""Выявление тематических и уменийных закономерностей (кластеры дефицитов)."""

from __future__ import annotations

from collections import defaultdict

from apps.vpr.conclusion.rules import classify_mastery
from apps.vpr.expert_analysis.competences import PLACEHOLDER_SKILLS, PLACEHOLDER_TOPICS
from apps.vpr.expert_analysis.result import PatternInsight


def _is_weak(pct: float | None) -> bool:
    if pct is None:
        return False
    band = classify_mastery(pct)
    return band in {"problem", "critical"}


def _is_strong(pct: float | None) -> bool:
    if pct is None:
        return False
    band = classify_mastery(pct)
    return band in {"high", "sufficient"}


def analyze_patterns(analysis, competences) -> tuple[list[PatternInsight], list[str]]:
    patterns: list[PatternInsight] = []
    paragraphs: list[str] = []

    # 1) Кластеры по разделам программы
    section_stats: dict[str, list[float]] = defaultdict(list)
    for row in analysis.task_rows or []:
        section = (row.get("program_section") or "").strip()
        pct = row.get("completion_percent")
        if not section or pct is None:
            continue
        section_stats[section].append(float(pct))

    weak_sections = []
    strong_sections = []
    for section, values in section_stats.items():
        if len(values) < 2:
            continue
        avg = sum(values) / len(values)
        if _is_weak(avg):
            weak_sections.append((section, avg, len(values)))
        elif _is_strong(avg):
            strong_sections.append((section, avg, len(values)))

    if weak_sections:
        weak_sections.sort(key=lambda x: x[1])
        for section, avg, n in weak_sections[:3]:
            patterns.append(
                PatternInsight(
                    kind="thematic",
                    title=f"Тематический образовательный дефицит раздела «{section}»",
                    explanation=(
                        f"Совокупность результатов по разделу «{section}» "
                        f"свидетельствует о едином тематическом образовательном дефиците: "
                        f"затруднения наблюдаются устойчиво по группе связанных заданий "
                        f"({n} проявлений), а не как изолированные случайные ошибки. "
                        f"Это снижает результат всей содержательной линии."
                    ),
                    evidence=[f"раздел «{section}»"],
                )
            )
        paragraphs.append(
            "Выявлены устойчивые тематические кластеры риска: низкие результаты "
            "по нескольким заданиям одного раздела указывают на единый содержательный дефицит."
        )

    if len(weak_sections) >= 3:
        patterns.append(
            PatternInsight(
                kind="systemic",
                title="Системная проблема предметной подготовки",
                explanation=(
                    f"Проблемными оказываются сразу {len(weak_sections)} разделов программы. "
                    "Это системный образовательный дефицит: потери выходят за рамки "
                    "локальной темы и формируют межраздельную недостаточность "
                    "предметной подготовки класса."
                ),
                evidence=[f"«{s}»" for s, a, _ in weak_sections[:5]],
            )
        )
        paragraphs.append(
            "Одновременные затруднения по нескольким разделам свидетельствуют "
            "о системной проблеме предметной подготовки, а не о случайных пробелах."
        )

    # 2) Кластеры по умениям
    weak_skills = []
    for row in analysis.skill_rows or []:
        skill = (getattr(row, "checked_skill", None) or "").strip()
        if skill in PLACEHOLDER_SKILLS:
            continue
        pct = getattr(row, "avg_completion_percent", None)
        if _is_weak(pct):
            weak_skills.append((skill, float(pct)))
    if len(weak_skills) >= 2:
        patterns.append(
            PatternInsight(
                kind="competence",
                title="Недостаточная сформированность группы умений",
                explanation=(
                    f"Сразу {len(weak_skills)} проверяемых умений находятся в зоне риска. "
                    "Совокупность однотипных уменийных дефицитов указывает на "
                    "недостаточную сформированность соответствующей компетенции."
                ),
                evidence=[f"«{s}» ({p:.0f}%)" for s, p in weak_skills[:5]],
            )
        )
        paragraphs.append(
            "Низкие результаты по нескольким умениям образуют уменийный кластер риска "
            "и снижают устойчивость предметной компетенции в целом."
        )

    # 3) Массовые темы из topic_analysis
    topic_profile = getattr(analysis, "topic_analysis", None)
    mass = list(getattr(topic_profile, "mass_deficits", None) or []) if topic_profile else []
    mass = [t for t in mass if t and t not in PLACEHOLDER_TOPICS]
    if mass:
        patterns.append(
            PatternInsight(
                kind="thematic",
                title="Массовые тематические дефициты",
                explanation=(
                    "Темы с массовым характером дефицита определяют устойчивое снижение "
                    "результата у значительной части класса и требуют приоритетной коррекции."
                ),
                evidence=[f"«{t}»" for t in mass[:5]],
            )
        )
        paragraphs.append(
            f"Массовые тематические дефициты ({', '.join(f'«{t}»' for t in mass[:4])}) "
            "формируют ядро проблемной зоны подготовки."
        )

    # 4) Компетенции
    weak_comp = [c for c in competences if c.status == "weak"]
    formed_comp = [c for c in competences if c.status == "formed"]
    if weak_comp:
        paragraphs.append(
            "По предметной модели компетенций наиболее уязвимы: "
            + ", ".join(f"«{c.name}»" for c in weak_comp[:4])
            + ". Их слабость объясняет снижение результатов в связанных заданиях."
        )
    if formed_comp:
        paragraphs.append(
            "Устойчиво проявляются компетенции: "
            + ", ".join(f"«{c.name}»" for c in formed_comp[:4])
            + ". Они образуют ресурсную основу предметной подготовки класса."
        )

    if strong_sections and not paragraphs:
        paragraphs.append(
            "По ряду разделов программы наблюдается устойчиво высокий результат, "
            "что подтверждает наличие сформированных содержательных опор."
        )

    if not patterns and not paragraphs:
        paragraphs.append(
            "Выраженных тематических или уменийных кластеров риска не выявлено: "
            "результаты распределены без устойчивой концентрации дефицитов в одном разделе."
        )

    return patterns[:8], paragraphs
