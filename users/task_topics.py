"""
Темы заданий, маппинг предметов и границы частей КИМ для отчётов ЕГЭ/ОГЭ.
"""
from __future__ import annotations

import re
from functools import lru_cache
from json import JSONDecodeError
from pathlib import Path

# Русские названия предметов (как в протоколах) → ключи каталога ФИПИ.
SUBJECT_NAME_TO_CATALOG_KEYS: dict[str, list[str]] = {
    "русский язык": ["russian"],
    "математика": ["math_basic"],
    "математика базовая": ["math_basic"],
    "математика профильная": ["math_profile"],
    "физика": ["physics"],
    "химия": ["chemistry"],
    "биология": ["biology"],
    "география": ["geography"],
    "история": ["history"],
    "обществознание": ["social_studies"],
    "литература": ["literature"],
    "информатика": ["informatics"],
    "информатика (кегэ)": ["informatics"],
    "английский язык": ["english"],
    "немецкий язык": ["german"],
    "французский язык": ["french"],
    "испанский язык": ["spanish"],
    "китайский язык": ["chinese"],
    "родной язык": ["russian"],
}

# ОГЭ: математика — темы заданий по спецификации ФИПИ (КИМ 2026).
OGE_MATH_TASK_TOPICS: dict[int, str] = {
    1: "Числа и вычисления",
    2: "Алгебраические выражения",
    3: "Уравнения и неравенства",
    4: "Числовые последовательности",
    5: "Практико-ориентированная задача",
    6: "Геометрия: планиметрия",
    7: "Геометрия: планиметрия",
    8: "Геометрия: планиметрия",
    9: "Статистика и вероятность",
    10: "Функции и графики",
    11: "Геометрия: планиметрия",
    12: "Геометрия: планиметрия",
    13: "Геометрия: планиметрия",
    14: "Геометрия: планиметрия",
    15: "Алгебра: функции",
    16: "Алгебра: уравнения и системы",
    17: "Геометрия: планиметрия",
    18: "Геометрия: планиметрия",
    19: "Алгебра: неравенства и системы",
    20: "Развёрнутый ответ: алгебра",
    21: "Развёрнутый ответ: алгебра",
    22: "Развёрнутый ответ: геометрия",
    23: "Развёрнутый ответ: геометрия",
    24: "Развёрнутый ответ: геометрия",
    25: "Развёрнутый ответ: геометрия",
}

OGE_SKILL_PROFILES: dict[str, list[str]] = {
    "math": [
        "вычислительные навыки и точность преобразований",
        "решение уравнений и построение математических моделей",
        "геометрическое рассуждение и анализ графиков",
    ],
    "russian": [
        "понимание текста и условия задания",
        "орфография, пунктуация и языковые нормы",
        "грамотность письменной речи и построение ответа",
    ],
    "physics": [
        "интерпретация физических величин и законов",
        "решение расчётных задач",
        "качественный анализ физических явлений",
    ],
    "chemistry": [
        "понимание химических закономерностей",
        "расчёты по формулам и уравнениям реакций",
        "анализ свойств веществ",
    ],
    "biology": [
        "системный анализ биологических процессов",
        "интерпретация биологических схем и данных",
        "применение биологических знаний в новых ситуациях",
    ],
    "geography": [
        "пространственный анализ и работа с картами",
        "анализ географических данных",
        "практико-ориентированная географическая интерпретация",
    ],
    "history": [
        "хронологическое мышление",
        "анализ исторических источников",
        "историческая аргументация",
    ],
    "social": [
        "понятийный аппарат обществознания",
        "анализ социальных ситуаций",
        "аргументированное объяснение",
    ],
    "informatics": [
        "алгоритмическое мышление",
        "логический анализ и кодирование информации",
        "программирование и анализ данных",
    ],
    "literature": [
        "аналитическое чтение",
        "интерпретация художественного текста",
        "аргументация в письменной форме",
    ],
    "foreign": [
        "понимание иноязычного текста",
        "лексико-грамматическая точность",
        "письменная и устная коммуникация",
    ],
}

PLACEHOLDER_TOPIC_MARKERS = (
    "тема задания №",
    "тема задания по спецификации",
    "тема по спецификации огэ",
    "требуется методическая верификация",
    "элемент содержания по спецификации",
    "тема из спецификации (уточнить по фипи)",
)


def subject_key_candidates(subject_name: str, exam_type: str = "ege") -> list[str]:
    title = (subject_name or "").strip().lower()
    if not title:
        return []
    # Длинные ключи первыми, чтобы «математика базовая» не схлопывалась в «математика».
    for ru_name in sorted(SUBJECT_NAME_TO_CATALOG_KEYS, key=len, reverse=True):
        if ru_name in title:
            keys = list(SUBJECT_NAME_TO_CATALOG_KEYS[ru_name])
            if exam_type == "oge" and "математ" in title and "math_basic" not in keys:
                keys = ["math_basic"] + keys
            return keys
    if "математ" in title:
        return ["math_basic"] if exam_type == "oge" else ["math_profile", "math_basic"]
    if "рус" in title:
        return ["russian"]
    if "обществ" in title:
        return ["social_studies"]
    if "информат" in title:
        return ["informatics"]
    if any(x in title for x in ("англий", "немец", "француз", "испан", "китай", "иностран")):
        return ["english"]
    return []


def subject_key(subject_name: str, exam_type: str = "ege") -> str:
    """Ключ предмета в каталоге ФИПИ (совпадает с subject_key_candidates[0])."""
    candidates = subject_key_candidates(subject_name, exam_type)
    if candidates:
        return candidates[0]
    return "generic"


def domain_from_subject_key(subject_key: str) -> str:
    if subject_key.startswith("math"):
        return "math"
    mapping = {
        "russian": "russian",
        "biology": "biology",
        "chemistry": "chemistry",
        "physics": "physics",
        "history": "history",
        "social": "social",
        "social_studies": "social",
        "informatics": "informatics",
        "literature": "literature",
        "geography": "geography",
        "foreign": "foreign",
        "english": "foreign",
        "german": "foreign",
        "french": "foreign",
        "spanish": "foreign",
        "chinese": "foreign",
    }
    return mapping.get(subject_key, "generic")


def is_usable_catalog_topic(topic: str) -> bool:
    text = (topic or "").strip()
    if not text:
        return False
    lower = text.lower()
    if any(marker in lower for marker in PLACEHOLDER_TOPIC_MARKERS):
        return False
    # Только «5 класс: ; 6 класс» без содержания.
    stripped = re.sub(r"[\d\sкласс:;.,\-–]+", "", lower)
    if len(stripped) < 4:
        return False
    return True


def _catalog_source(exam_type: str) -> Path:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    if (exam_type or "ege").lower() == "oge":
        source = data_dir / "oge_json" / "oge_2026_enriched.json"
        if source.exists():
            return source
    source = data_dir / "ege_2026_enriched.json"
    if not source.exists():
        source = data_dir / "ege_2026_full.json"
    return source


@lru_cache(maxsize=16)
def _load_catalog_cached(source_path: str, version_token: int) -> dict:
    source = Path(source_path)
    if not source.exists():
        return {}
    raw = source.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        payload = __import__("json").loads(raw)
    except JSONDecodeError:
        return {}
    result: dict = {}
    for subject in payload.get("subjects", []):
        key = (subject.get("subject") or "").strip().lower()
        if not key:
            continue
        result[key] = {
            item.get("task"): {
                "topic": item.get("topic"),
                "topic_oge": item.get("topic_oge"),
                "grade_range": item.get("grade_range") or [],
                "grade_range_oge": item.get("grade_range_oge") or [],
            }
            for item in subject.get("tasks", [])
            if item.get("task") is not None
        }
    return result


def load_subject_task_catalog(exam_type: str = "ege") -> dict:
    source = _catalog_source(exam_type)
    version_token = source.stat().st_mtime_ns if source.exists() else 0
    return _load_catalog_cached(str(source), version_token)


def static_task_topic(subject_name: str, task_number: int, exam_type: str) -> str | None:
    et = (exam_type or "ege").lower()
    title = (subject_name or "").strip().lower()
    sk = subject_key(subject_name, et)
    if et == "oge" and sk == "math_basic" and task_number in OGE_MATH_TASK_TOPICS:
        return OGE_MATH_TASK_TOPICS[task_number]
    if et == "ege" and "рус" in title and task_number >= 28:
        return "Критерии задания №27 (сочинение), не отдельная линия КИМ ФИПИ"
    if "математ" in title:
        if task_number <= 5:
            return "Числа, выражения и практико-ориентированные задачи"
        if task_number <= 14:
            return "Алгебра и геометрия (первая часть)"
        if task_number <= 19:
            return "Алгебра и геометрия повышенной сложности"
        return "Задания с развёрнутым ответом"
    if "рус" in title:
        if task_number <= 9:
            return "Работа с текстом и лексика"
        if task_number <= 15:
            return "Орфография и пунктуация"
        return "Грамматика и письменная речь"
    if "физик" in title:
        return "Раздел физики по номеру задания КИМ"
    if "хими" in title:
        return "Раздел химии по номеру задания КИМ"
    if "биолог" in title:
        if task_number <= 16:
            return "Общая биология и анатомия"
        return "Генетика и экология"
    if "информат" in title:
        if task_number <= 12:
            return "Кодирование, логика и алгоритмы"
        return "Программирование и анализ данных"
    return None


def manual_task_meta(subject_name: str, task_number: int, exam_type: str = "ege") -> dict | None:
    from exams.models import ExamTaskTopic

    et = (exam_type or "ege").lower()
    candidates = subject_key_candidates(subject_name, et)
    row = (
        ExamTaskTopic.objects.filter(exam_type=et, subject_key__in=candidates, task_number=task_number)
        .only("topic", "grade_range")
        .first()
    )
    if not row and et != "ege":
        row = (
            ExamTaskTopic.objects.filter(exam_type="ege", subject_key__in=candidates, task_number=task_number)
            .only("topic", "grade_range")
            .first()
        )
    if not row:
        return None
    return {"topic": (row.topic or "").strip(), "grade_range": row.grade_range or []}


def topic_for_task(subject_name: str, task_number: int, exam_type: str = "ege") -> str:
    """Единая точка: тема задания для отчётов и дашбордов."""
    et = (exam_type or "ege").lower()
    manual_meta = manual_task_meta(subject_name, task_number, et)
    if manual_meta and manual_meta.get("topic"):
        topic = str(manual_meta["topic"]).strip()
        if is_usable_catalog_topic(topic):
            return topic

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


def part2_start_task(exam_type: str, subject_key_value: str, short_part_length: int | None = None) -> int:
    """Номер первого задания второй части."""
    et = (exam_type or "ege").lower()
    if short_part_length and short_part_length > 0:
        return short_part_length + 1
    if et == "oge":
        if subject_key_value == "math_basic":
            return 20
        if subject_key_value == "russian":
            return 14
        return 20
    if subject_key_value == "math_profile":
        return 13
    if subject_key_value == "math_basic":
        return 13
    if subject_key_value == "russian":
        return 14
    return 13


def is_expanded_answer_task(exam_type: str, subject_key_value: str, task_number: int, short_part_length: int | None = None) -> bool:
    return task_number >= part2_start_task(exam_type, subject_key_value, short_part_length)


def default_grade_label(exam_type: str) -> str:
    return "9" if (exam_type or "").lower() == "oge" else "10–11"


def default_skill_profile(subject_name: str, exam_type: str) -> list[str]:
    sk = subject_key(subject_name, exam_type)
    domain = domain_from_subject_key(sk)
    if (exam_type or "").lower() == "oge":
        profile = OGE_SKILL_PROFILES.get(domain)
        if profile:
            return list(profile)
    generic = {
        "math": ["многошаговое рассуждение", "моделирование", "стратегия вычислений"],
        "russian": ["текстовая интерпретация", "языковой анализ", "письменная аргументация"],
        "biology": ["системный анализ", "процессная интерпретация", "экспериментальное мышление"],
    }
    return list(generic.get(domain, ["аналитическое применение знаний", "аргументация решения", "перенос способов решения"]))


def parse_long_answer_mask(text: str, start_task: int) -> list[tuple[int, str]]:
    """Разбор маски второй части: «0(2)1(2)...» или посимвольная."""
    raw = (text or "").strip()
    if not raw:
        return []
    groups = re.findall(r"(\d+)\((\d+)\)", raw)
    if groups:
        return [(start_task + idx, score) for idx, (score, _max_score) in enumerate(groups)]
    tokens: list[tuple[int, str]] = []
    for idx, char in enumerate(raw):
        if char.isspace():
            continue
        tokens.append((start_task + len(tokens), char))
    return tokens
