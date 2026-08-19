from __future__ import annotations

import re
from dataclasses import dataclass, field

from users.task_topics import is_usable_catalog_topic


GRADE_RE = re.compile(r"(\d{1,2})\s*(?:класс|кл\.?)", re.IGNORECASE)
GRADE_RANGE_RE = re.compile(r"(\d{1,2})\s*[–\-]\s*(\d{1,2})\s*(?:класс|кл\.?)", re.IGNORECASE)
FIPI_POINT_RE = re.compile(r"п\.\s*([\d.]+)", re.IGNORECASE)
FIPI_CODE_RE = re.compile(r"\b(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\b")
GRADE_CHUNK_RE = re.compile(
    r"(\d{1,2})\s*(?:класс|кл\.?)[,\s:]*([^0-9]+?)(?=\d{1,2}\s*(?:класс|кл\.?)|$)",
    re.IGNORECASE | re.DOTALL,
)

SUBJECT_SECTION_KEYWORDS: dict[str, list[tuple[str, str]]] = {
    "russian": [
        ("орфограф", "Орфография"),
        ("правописан", "Орфография"),
        ("пунктуац", "Пунктуация"),
        ("синтакс", "Синтаксис"),
        ("лексик", "Лексика"),
        ("морфолог", "Морфология"),
        ("фонет", "Фонетика"),
        ("ударен", "Фонетика"),
        ("граммат", "Грамматика"),
        ("текст", "Работа с текстом"),
        ("сочинен", "Письменная речь"),
        ("речь", "Речь"),
    ],
    "math_basic": [
        ("геометр", "Геометрия"),
        ("алгебр", "Алгебра"),
        ("уравнен", "Уравнения"),
        ("неравенств", "Неравенства"),
        ("функц", "Функции"),
        ("вероятност", "Вероятность и статистика"),
        ("вычисл", "Числа и вычисления"),
        ("график", "Графики и функции"),
    ],
    "math_profile": [
        ("логарифм", "Логарифмы"),
        ("производн", "Математический анализ"),
        ("интеграл", "Математический анализ"),
        ("геометр", "Геометрия"),
        ("стереометр", "Стереометрия"),
        ("планиметр", "Планиметрия"),
        ("тригоном", "Тригонометрия"),
        ("уравнен", "Уравнения"),
        ("алгебр", "Алгебра"),
        ("вероятност", "Вероятность и статистика"),
    ],
    "physics": [
        ("кинемат", "Кинематика"),
        ("динамик", "Динамика"),
        ("механик", "Механика"),
        ("электродинам", "Электродинамика"),
        ("оптик", "Оптика"),
        ("термодинам", "Термодинамика"),
        ("магнит", "Магнетизм"),
        ("квант", "Квантовая физика"),
    ],
    "chemistry": [
        ("органическ", "Органическая химия"),
        ("неорганическ", "Неорганическая химия"),
        ("реакц", "Химические реакции"),
        ("стехиометр", "Стехиометрия"),
        ("электрол", "Электролитическая диссоциация"),
        ("раствор", "Растворы"),
    ],
    "biology": [
        ("человек", "Анатомия и физиология"),
        ("биосоциаль", "Анатомия и физиология"),
        ("генет", "Генетика"),
        ("эволюц", "Эволюция"),
        ("эколог", "Экология"),
        ("клетк", "Клетка"),
        ("ботан", "Ботаника"),
        ("зоолог", "Зоология"),
        ("анатом", "Анатомия"),
        ("физиолог", "Физиология"),
        ("живые систем", "Общая биология"),
    ],
    "history": [
        ("древн", "Древняя история"),
        ("средневек", "Средневековье"),
        ("новое время", "Новое время"),
        ("xx век", "XX век"),
        ("источник", "Работа с источниками"),
        ("культур", "Культура"),
    ],
    "social_studies": [
        ("эконом", "Экономика"),
        ("прав", "Право"),
        ("полит", "Политика"),
        ("социолог", "Социология"),
        ("конституц", "Конституция"),
        ("обществ", "Общество"),
    ],
    "informatics": [
        ("алгоритм", "Алгоритмы"),
        ("программ", "Программирование"),
        ("код", "Кодирование информации"),
        ("логик", "Логика"),
        ("баз данных", "Базы данных"),
    ],
    "literature": [
        ("поэт", "Поэзия"),
        ("проз", "Проза"),
        ("драм", "Драматургия"),
        ("художествен", "Художественный анализ"),
        ("литератур", "Литература"),
    ],
    "geography": [
        ("карт", "Картография"),
        ("климат", "Климат"),
        ("рельеф", "Рельеф"),
        ("населен", "Население"),
        ("хозяйств", "Хозяйство"),
    ],
    "english": [("лексик", "Лексика"), ("граммат", "Грамматика"), ("чтени", "Чтение"), ("письм", "Письмо")],
    "german": [("лексик", "Лексика"), ("граммат", "Грамматика"), ("чтени", "Чтение"), ("письм", "Письмо")],
    "french": [("лексик", "Лексика"), ("граммат", "Грамматика"), ("чтени", "Чтение"), ("письм", "Письмо")],
    "spanish": [("лексик", "Лексика"), ("граммат", "Грамматика"), ("чтени", "Чтение"), ("письм", "Письмо")],
    "chinese": [("лексик", "Лексика"), ("граммат", "Грамматика"), ("чтени", "Чтение"), ("письм", "Письмо")],
}


@dataclass
class ParsedTopic:
    topic: str = ""
    subtopic: str = ""
    section: str = ""
    subsection: str = ""
    fipi_content_code: str = ""
    requirement_code: str = ""
    fgos_classes: list[int] = field(default_factory=list)
    fgos_class_start: int | None = None
    fgos_class_repeat: list[int] = field(default_factory=list)
    skill_text: str = ""


def _clean_topic_name(text: str) -> str:
    value = (text or "").strip()
    value = re.sub(r"^\d{1,2}\s*(?:класс|кл\.?)[,\s:]*", "", value, flags=re.I)
    value = re.sub(r"^п\.\s*[\d.]+\s*", "", value, flags=re.I)
    value = re.sub(r"^\d{1,2}\.\d{1,2}(?:\.\d{1,2})?\s*", "", value)
    value = re.sub(r"\s{2,}", " ", value).strip(" ;,.")
    return value[:512]


def _extract_grade_chunks(text: str) -> list[tuple[int, str]]:
    chunks: list[tuple[int, str]] = []
    for match in GRADE_CHUNK_RE.finditer(text or ""):
        grade = int(match.group(1))
        content = _clean_topic_name(match.group(2))
        if is_usable_catalog_topic(content):
            chunks.append((grade, content))
    return chunks


def _pick_best_chunk(chunks: list[tuple[int, str]], grade_range: list[int] | None) -> str:
    if not chunks:
        return ""
    if grade_range:
        for target_grade in sorted(grade_range, reverse=True):
            for grade, content in chunks:
                if grade == target_grade:
                    return content
    return chunks[-1][1]


def infer_section_from_topic(topic: str, subject_key: str = "") -> tuple[str, str]:
    lower = (topic or "").lower()
    if not lower:
        return "", ""

    keys = [subject_key] if subject_key else []
    if subject_key.startswith("math"):
        keys.extend(["math_profile", "math_basic"])
    for key in keys:
        for marker, label in SUBJECT_SECTION_KEYWORDS.get(key, []):
            if marker in lower:
                return label, ""
    return "", ""


def parse_grades_from_text(text: str) -> list[int]:
    grades: list[int] = []
    for match in GRADE_RANGE_RE.finditer(text or ""):
        start, end = int(match.group(1)), int(match.group(2))
        grades.extend(range(start, end + 1))
    for match in GRADE_RE.finditer(text or ""):
        grades.append(int(match.group(1)))
    return sorted(set(grades))


def parse_topic_text(
    topic_raw: str,
    grade_range: list[int] | None = None,
    *,
    subject_key: str = "",
    exam_type: str = "ege",
) -> ParsedTopic:
    text = (topic_raw or "").strip()
    grades = list(grade_range or []) or parse_grades_from_text(text)
    fipi_codes = FIPI_POINT_RE.findall(text)
    content_codes = FIPI_CODE_RE.findall(text)

    grade_chunks = _extract_grade_chunks(text)
    topic_name = _pick_best_chunk(grade_chunks, grades)

    if not topic_name and is_usable_catalog_topic(text):
        chunks = [c.strip() for c in re.split(r"[;•]", text) if c.strip()]
        for chunk in chunks:
            cleaned = _clean_topic_name(chunk)
            if is_usable_catalog_topic(cleaned):
                topic_name = cleaned
                break
        if not topic_name:
            topic_name = _clean_topic_name(chunks[0] if chunks else text)

    if not is_usable_catalog_topic(topic_name):
        topic_name = _clean_topic_name(text) if is_usable_catalog_topic(_clean_topic_name(text)) else ""

    subtopic = ""
    if len(grade_chunks) > 1:
        subtopic = grade_chunks[-2][1] if grade_chunks[-1][1] == topic_name else grade_chunks[-1][1]
        if subtopic == topic_name:
            subtopic = ""

    section, subsection = infer_section_from_topic(topic_name, subject_key)
    if not section and subtopic:
        section, subsection = infer_section_from_topic(subtopic, subject_key)

    fgos_start = grades[0] if grades else None
    fgos_repeat = grades[1:] if len(grades) > 1 else []

    return ParsedTopic(
        topic=topic_name or text[:512],
        subtopic=subtopic,
        section=section,
        subsection=subsection,
        fipi_content_code=f"п. {fipi_codes[0]}" if fipi_codes else (content_codes[0] if content_codes else ""),
        requirement_code=content_codes[-1] if content_codes else "",
        fgos_classes=grades,
        fgos_class_start=fgos_start,
        fgos_class_repeat=fgos_repeat,
        skill_text=topic_name or text[:256],
    )


def infer_difficulty(task_number: int, exam_part: int, part_boundary: int) -> str:
    if exam_part == 2:
        return "высокий"
    if task_number >= part_boundary - 2:
        return "повышенный"
    if task_number <= 5:
        return "базовый"
    return "средний"


def format_grade_label(start: int | None, repeat: list[int], exam_type: str) -> dict[str, str]:
    exam_label = "ЕГЭ" if exam_type == "ege" else "ОГЭ"
    studied = f"{start} класс" if start else "по спецификации"
    if repeat:
        if len(repeat) == 1:
            reinforced = f"{repeat[0]} класс"
        else:
            reinforced = f"{repeat[0]}–{repeat[-1]} класс"
    elif start:
        reinforced = f"{start + 1} класс" if start < 11 else f"{start} класс"
    else:
        reinforced = "по спецификации"
    return {
        "studied": studied,
        "reinforced": reinforced,
        "exam": exam_label,
    }
