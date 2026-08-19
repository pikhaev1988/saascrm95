from __future__ import annotations

import re
from dataclasses import dataclass

from users.task_topics import (
    domain_from_subject_key,
    is_usable_catalog_topic,
    load_subject_task_catalog,
    manual_task_meta,
    part2_start_task,
    static_task_topic,
    subject_key,
    subject_key_candidates,
)
from users.task_classification import (
    _official_record as _catalog_official_record,
)


@dataclass
class TaskMetadata:
    task_number: int
    topic: str
    section: str
    subsection: str
    fipi_code: str
    skill: str
    skill_name: str
    grade_range: list[int]
    exam_part: int
    max_score: float | None
    difficulty_level: str
    subject_key: str
    domain: str


SUBJECT_SKILL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "russian": ("орфограф", "пунктуац", "лексик", "синтакс", "морфолог", "фонет", "граммат", "текст", "речь", "сочинен"),
    "math": ("алгебр", "геометр", "уравнен", "функц", "вероятност", "вычисл", "график", "тригоном", "производн", "интеграл"),
    "physics": ("механик", "электродинам", "оптик", "термодинам", "кинемат", "динамик", "энерг", "магнит", "квант"),
    "chemistry": ("реакц", "веществ", "раствор", "электрол", "органическ", "неорганическ", "стехиометр", "валентност"),
    "biology": ("клетк", "генет", "эволюц", "эколог", "анatom", "физиолог", "ботан", "зоолог"),
    "history": ("истор", "хронолог", "источник", "революц", "импер", "войн", "культур"),
    "social": ("обществ", "эконом", "прав", "полит", "социолог", "конституц"),
    "informatics": ("алгоритм", "программ", "код", "логик", "баз данных", "информац"),
    "literature": ("литератур", "поэт", "проз", "художествен", "автор", "образ"),
    "geography": ("географ", "карт", "климат", "рельеф", "населен", "хозяйств"),
    "foreign": ("лексик", "граммат", "аудирован", "чтени", "письм", "говорен"),
}

# Маркеры чужого предмета. Не включаем пересекающиеся разделы
# (химия клетки в биологии, физхимия в химии и т.п.).
FORBIDDEN_CROSS_SUBJECT: dict[str, tuple[str, ...]] = {
    "physics": ("орфограф", "пунктуац", "лексиколог", "синтаксис", "литературный анализ", "сочинен"),
    "chemistry": ("орфограф", "пунктуац", "геометр", "планиметр", "литератур", "сочинен"),
    "math": ("орфограф", "пунктуац", "сочинен", "клеточн", "генетик", "историческ источник"),
    "biology": ("орфограф", "пунктуац", "сочинен", "геометр", "планиметр", "алгебраическ"),
    "russian": ("кинемат", "термодинам", "стереометр", "логарифм", "интеграл"),
    "history": ("орфограф", "пунктуац", "логарифм", "кинемат"),
    "social": ("орфограф", "пунктуац", "логарифм", "кинемат", "стереометр"),
}


def _extract_section(topic: str) -> str:
    text = (topic or "").strip()
    if not text:
        return ""
    parts = re.split(r"[;•]", text)
    return parts[0].strip() if parts else text[:120]


def _extract_subsection(topic: str) -> str:
    text = (topic or "").strip()
    if not text:
        return ""
    parts = [p.strip() for p in re.split(r"[;•]", text) if p.strip()]
    return parts[1] if len(parts) > 1 else ""


def _resolve_topic(subject_name: str, task_number: int, exam_type: str) -> str:
    et = (exam_type or "ege").lower()
    manual = manual_task_meta(subject_name, task_number, et)
    if manual and manual.get("topic") and is_usable_catalog_topic(manual["topic"]):
        return manual["topic"]

    topics_index = load_subject_task_catalog(et)
    for candidate in subject_key_candidates(subject_name, et):
        task_meta = topics_index.get(candidate, {}).get(task_number, {})
        if et == "oge":
            topic = (task_meta.get("topic_oge") or task_meta.get("topic") or "").strip()
        else:
            topic = (task_meta.get("topic") or "").strip()
        if is_usable_catalog_topic(topic):
            return topic

    static = static_task_topic(subject_name, task_number, et)
    if static:
        return static

    label = "ОГЭ" if et == "oge" else "ЕГЭ"
    return f"Содержание задания №{task_number} ({label}, {subject_name or 'предмет'})"


def get_task_metadata(subject_name: str, task_number: int, exam_type: str = "ege") -> TaskMetadata:
    et = (exam_type or "ege").lower()
    sk = subject_key(subject_name, et)
    domain = domain_from_subject_key(sk)

    # Priority 1: official task catalog (data/task_catalog_2026/{exam}/{subject}.json)
    official = _catalog_official_record(subject_name, task_number, et, 2026)
    if official:
        kim = official.get("kim") or {}
        theme = official.get("theme") or {}
        program = official.get("school_program") or {}
        fipi = official.get("fipi") or {}
        display_name = str(theme.get("display_name") or "").strip()
        block = str(theme.get("block") or "").strip()
        topic = display_name if is_usable_catalog_topic(display_name) else _resolve_topic(subject_name, task_number, et)
        grade_range = list(program.get("grades") or [])
        skills_list = list(official.get("skills") or [])
        skill_code = ""
        skill_name = skills_list[0] if skills_list else ""
        content_codes = fipi.get("content_codes") or []
        fipi_code = content_codes[0] if content_codes else ""
        exam_part = int(kim.get("part") or 0)
        if exam_part not in (1, 2):
            part_boundary = part2_start_task(et, sk)
            exam_part = 2 if task_number >= part_boundary else 1
        section = block or _extract_section(topic)
        subsection = display_name if block and display_name != block else _extract_subsection(topic)
        return TaskMetadata(
            task_number=task_number,
            topic=topic,
            section=section,
            subsection=subsection,
            fipi_code=fipi_code,
            skill=skill_code,
            skill_name=skill_name,
            grade_range=grade_range,
            exam_part=exam_part,
            max_score=None,
            difficulty_level="",
            subject_key=sk,
            domain=domain,
        )

    # Priority 2+: enriched JSON / legacy fallback
    topic = _resolve_topic(subject_name, task_number, et)
    manual = manual_task_meta(subject_name, task_number, et) or {}
    grade_range = list(manual.get("grade_range") or [])

    topics_index = load_subject_task_catalog(et)
    skill_code = ""
    skill_name = ""
    max_score = None
    difficulty_level = ""
    for candidate in subject_key_candidates(subject_name, et):
        task_meta = topics_index.get(candidate, {}).get(task_number, {})
        if not grade_range:
            if et == "oge":
                grade_range = list(task_meta.get("grade_range_oge") or task_meta.get("grade_range") or [])
            else:
                grade_range = list(task_meta.get("grade_range") or [])
        skill_code = str(task_meta.get("skill") or "").strip()
        if skill_code:
            break

    part_boundary = part2_start_task(et, sk)
    exam_part = 2 if task_number >= part_boundary else 1

    return TaskMetadata(
        task_number=task_number,
        topic=topic,
        section=_extract_section(topic),
        subsection=_extract_subsection(topic),
        fipi_code=skill_code,
        skill=skill_code,
        skill_name=skill_name,
        grade_range=grade_range,
        exam_part=exam_part,
        max_score=max_score,
        difficulty_level=difficulty_level,
        subject_key=sk,
        domain=domain,
    )


def validate_topic_belongs_to_subject(subject_name: str, exam_type: str, topic: str) -> list[str]:
    errors: list[str] = []
    sk = subject_key(subject_name, exam_type)
    domain = domain_from_subject_key(sk)
    lower = (topic or "").lower()
    if not lower.strip():
        return errors

    forbidden = FORBIDDEN_CROSS_SUBJECT.get(domain, ())
    if forbidden and any(marker in lower for marker in forbidden):
        errors.append(f"Тема «{topic[:80]}» не соответствует предмету «{subject_name}».")
    return errors
