"""Пороги сдачи ЕГЭ / ГВЭ / ОГЭ."""

from __future__ import annotations

from types import SimpleNamespace

# В протоколах ЕГЭ код 51 — русский язык ГВЭ (оценка 2–5, порог ≥ 3).
GVE_EXAM_CODES = frozenset({"51"})
GVE_GRADE_THRESHOLD = SimpleNamespace(minimum_score=None, minimum_grade=3)


def normalize_exam_code(code) -> str:
    return str(code or "").strip()


def is_gve_exam(*, exam_code=None, subject_name: str | None = None) -> bool:
    """ГВЭ в выгрузках ЕГЭ: код предмета 51 (русский) или явное «ГВЭ» в названии."""
    code = normalize_exam_code(exam_code)
    if code in GVE_EXAM_CODES:
        return True
    if code.isdigit() and str(int(code)) in GVE_EXAM_CODES:
        return True
    title = (subject_name or "").strip().lower()
    return "гвэ" in title


def gve_subject_label(subject_name: str | None, exam_code=None) -> str:
    name = (subject_name or "").strip() or "Предмет не указан"
    if is_gve_exam(exam_code=exam_code, subject_name=name) and "гвэ" not in name.lower():
        return f"{name} (ГВЭ)"
    return name


def ege_threshold_subject_key(subject_name: str | None) -> str | None:
    """Ключ порога ЕГЭ по названию предмета протокола."""
    title = (subject_name or "").strip().lower()
    if "рус" in title:
        return "russian"
    if "математика" in title and "проф" in title:
        return "math_profile"
    if "математика" in title and "баз" in title:
        return "math_basic"
    if "обществ" in title:
        return "social"
    if "информат" in title:
        return "informatics"
    if "физик" in title:
        return "physics"
    if "хими" in title:
        return "chemistry"
    if "биолог" in title:
        return "biology"
    if "истори" in title:
        return "history"
    if "литератур" in title:
        return "literature"
    if "географ" in title:
        return "geography"
    if any(lang in title for lang in ("англий", "немец", "француз", "испан", "китай", "иностран")):
        return "foreign_language"
    return None


def resolve_ege_passing_threshold(year: int | None, subject_key: str | None, *, cache: dict | None = None):
    """
    Порог ЕГЭ по предмету и году.
    Если для года нет записи — берём ближайший предыдущий год с порогом
    (например, 2026 → 2025), чтобы не падать на флаг passed из импорта.
    """
    from exams.models import EgePassingThreshold

    if not subject_key:
        return None
    try:
        year_int = int(year or 0)
    except (TypeError, ValueError):
        year_int = 0
    if year_int <= 0:
        return None

    cache_key = (year_int, subject_key)
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    threshold = (
        EgePassingThreshold.objects.filter(year=year_int, subject_key=subject_key)
        .only("year", "subject_key", "minimum_score", "minimum_grade")
        .first()
    )
    if threshold is None:
        threshold = (
            EgePassingThreshold.objects.filter(year__lte=year_int, subject_key=subject_key)
            .only("year", "subject_key", "minimum_score", "minimum_grade")
            .order_by("-year")
            .first()
        )
    if cache is not None:
        cache[cache_key] = threshold
    return threshold


def score_meets_ege_threshold(score, threshold) -> bool | None:
    """True/False по порогу; None если порог не задан."""
    if threshold is None:
        return None
    try:
        score_value = float(score or 0)
    except (TypeError, ValueError):
        score_value = 0.0
    if threshold.minimum_score is not None:
        return score_value >= float(threshold.minimum_score)
    if threshold.minimum_grade is not None:
        return score_value >= float(threshold.minimum_grade)
    return None


def oge_score_passed(score, passed_flag=None) -> bool:
    """ОГЭ / ГВЭ: на пятибалльной шкале порог — оценка ≥ 3."""
    try:
        score_value = float(score or 0)
    except (TypeError, ValueError):
        score_value = 0.0
    if 0 < score_value <= 5:
        return score_value >= 3
    return bool(passed_flag)


def ege_result_passed(
    *,
    subject_name: str | None,
    year: int | None,
    score,
    passed_flag=None,
    exam_code=None,
    cache: dict | None = None,
) -> bool:
    """Сдал ли результат ЕГЭ по официальному порогу (не по флагу импорта)."""
    if is_gve_exam(exam_code=exam_code, subject_name=subject_name):
        return oge_score_passed(score, passed_flag)
    subject_key = ege_threshold_subject_key(subject_name)
    if not subject_key:
        return bool(passed_flag)
    threshold = resolve_ege_passing_threshold(year, subject_key, cache=cache)
    met = score_meets_ege_threshold(score, threshold)
    if met is None:
        return bool(passed_flag)
    return bool(met)

