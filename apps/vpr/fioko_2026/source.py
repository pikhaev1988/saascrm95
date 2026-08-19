"""Источник истины FIOKO 2026 — метаданные и цитаты требований."""

from __future__ import annotations

from typing import Any, TypedDict


class FiokoRequirement(TypedDict, total=False):
    source: str
    section: str
    page: int | str
    requirement: str


FIOKO_2026_SOURCE = "FIOKO_2026"
SOURCE_SYSTEM = "SYSTEM_ENHANCEMENT"

FIOKO_DOCUMENT = {
    "title": (
        "Обеспечение функционирования внутренней системы оценки качества образования "
        "для эффективного управления качеством образования в общеобразовательной организации. "
        "Рекомендации по проведению анализа результатов Всероссийских проверочных работ"
    ),
    "year": 2026,
    "short_title": "Рекомендации по проведению анализа результатов Всероссийских проверочных работ",
    "publisher": "ФИОКО",
}


def req(
    *,
    section: str,
    page: int | str,
    requirement: str,
    source: str = FIOKO_2026_SOURCE,
) -> FiokoRequirement:
    return {
        "source": source,
        "section": section,
        "page": page,
        "requirement": requirement,
    }


# Подтверждённые требования (по PDF Рекомендации_для_ОО.pdf)
FIOKO_REQUIREMENTS: dict[str, FiokoRequirement] = {
    "individual_results": req(
        section="1",
        page=5,
        requirement="Индивидуальные результаты: первичный балл, отметка ВПР, отметка по журналу, % Б/П/В",
    ),
    "difficulty_levels": req(
        section="1",
        page=5,
        requirement="Уровни сложности заданий Б/П/В из раздела 6 описания ВПР (кодификатор)",
    ),
    "basic_thresholds": req(
        section="1/5",
        page="6/17",
        requirement="Б: достаточный ≥60%; недостаточный <57%; зона 60±3%",
    ),
    "advanced_thresholds": req(
        section="1/5",
        page="6/17",
        requirement="П/В: достаточный ≥30%; недостаточный <28,5%; зона 30±1,5%",
    ),
    "marks_statistics": req(
        section="2",
        page=7,
        requirement="Статистика по отметкам 2–5; динамика % «2» за 3–5 лет",
    ),
    "mark2_dynamics": req(
        section="2",
        page=8,
        requirement="Динамика = текущий %«2» − прошлый %«2»; +10 п.п. — отрицательная",
    ),
    "journal_gap_ge_2": req(
        section="3",
        page=11,
        requirement="Анализировать расхождения ВПР↔журнал ≥2 балла",
    ),
    "primary_distribution": req(
        section="4",
        page=13,
        requirement="Гистограмма первичных баллов; пики на границах перехода отметок",
    ),
    "distribution_sample": req(
        section="4",
        page=13,
        requirement="Выборка ≥50 информативна; 20–30 приблизительный минимум; <20 ограничена",
    ),
    "boundary_peaks": req(
        section="4",
        page=15,
        requirement="Выраженные пики — возможный маркер нарушения объективности, требует доп. анализа",
    ),
    "task_performance": req(
        section="5",
        page=16,
        requirement="Выполнение заданий с уровнем сложности и маркировкой FIOKO",
    ),
    "skill_system_deficit": req(
        section="5",
        page=19,
        requirement="Большинство заданий умения красным — признак системного дефицита",
    ),
    "cross_year_comparable": req(
        section="5",
        page=19,
        requirement="Сравнение лет только при идентичности тематических блоков/умений по кодификатору",
    ),
    "cross_subject": req(
        section="5",
        page=19,
        requirement="Сравнительный анализ по предметам в разрезе параллелей с предыдущим годом",
    ),
    "planned_results": req(
        section="6",
        page=20,
        requirement="Достижение планируемых результатов по позициям кодификатора",
    ),
    "groups_by_marks": req(
        section="7",
        page=23,
        requirement="Выполнение заданий группами участников (по отметкам)",
    ),
    "groups_sample_min": req(
        section="7",
        page=24,
        requirement="Минимум выборки для информативного группового анализа ≥10",
    ),
    "group_anomalies": req(
        section="7",
        page=26,
        requirement="Пересечения/аномалии групп требуют детального изучения причин",
    ),
    "problem_oriented_management": req(
        section="Организация анализа ВПР",
        page=27,
        requirement="Проблемно-ориентированный анализ «от результата к условиям»",
    ),
}


def methodology_basis_text() -> str:
    d = FIOKO_DOCUMENT
    return (
        f"Методологическая основа анализа (подтверждённые элементы): {d['publisher']}. "
        f"«{d['short_title']}», {d['year']} год."
    )


def source_tag(code: str) -> dict[str, Any]:
    item = FIOKO_REQUIREMENTS.get(code)
    if not item:
        return {"source": SOURCE_SYSTEM, "requirement_code": code}
    return dict(item)
