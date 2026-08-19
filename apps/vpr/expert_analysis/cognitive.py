"""Анализ когнитивного уровня заданий (базовый / повышенный) по каталогу."""

from __future__ import annotations


def _difficulty_band(raw: str | None) -> str | None:
    text = (raw or "").strip().lower().replace("ё", "е")
    if not text:
        return None
    if text in {"б", "базовый", "basic", "b"} or text.startswith("баз"):
        return "basic"
    if text in {"п", "повышенный", "повыш", "advanced", "p"} or "повыш" in text or "высок" in text:
        return "advanced"
    return None


def analyze_cognitive(analysis) -> tuple[str, str, list[str], dict]:
    """
    Возвращает (code, label, legacy_paragraphs, meta).
    meta: basic_avg, advanced_avg, n_basic, n_advanced.
    Развёрнутый текст пишет composer по предметной модели.
    """
    basic: list[float] = []
    advanced: list[float] = []
    for row in analysis.task_rows or []:
        pct = row.get("completion_percent")
        if pct is None:
            continue
        band = _difficulty_band(row.get("difficulty"))
        if band == "basic":
            basic.append(float(pct))
        elif band == "advanced":
            advanced.append(float(pct))

    meta = {
        "basic_avg": (sum(basic) / len(basic)) if basic else None,
        "advanced_avg": (sum(advanced) / len(advanced)) if advanced else None,
        "n_basic": len(basic),
        "n_advanced": len(advanced),
    }

    if not basic and not advanced:
        return (
            "unknown",
            "когнитивная сложность по каталогу не размечена",
            [],
            meta,
        )

    basic_avg = meta["basic_avg"]
    advanced_avg = meta["advanced_avg"]
    basic_weak = basic_avg is not None and basic_avg < 60
    advanced_weak = advanced_avg is not None and advanced_avg < 60
    basic_strong = basic_avg is not None and basic_avg >= 75
    advanced_strong = advanced_avg is not None and advanced_avg >= 75

    if basic_weak and advanced_weak:
        code = "both_levels"
        label = "дефицит репродуктивной и продуктивной деятельности"
    elif basic_weak and not advanced_weak:
        code = "basic_deficit"
        label = "неполное освоение обязательного содержания"
    elif advanced_weak and basic_strong:
        code = "advanced_deficit"
        label = "преобладание репродуктивного уровня подготовки"
    elif advanced_weak:
        code = "advanced_gap"
        label = "разрыв между репродукцией и применением знаний"
    elif basic_strong and advanced_strong:
        code = "balanced_high"
        label = "устойчивость репродуктивной и продуктивной деятельности"
    else:
        code = "balanced"
        label = "сбалансированный когнитивный профиль"

    return code, label, [], meta
