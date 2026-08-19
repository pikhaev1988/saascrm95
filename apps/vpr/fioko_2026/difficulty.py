"""Нормализация уровней сложности заданий (Б / П / В)."""

from __future__ import annotations

from typing import Literal

DifficultyCode = Literal["basic", "advanced", "high", "unknown"]

DIFFICULTY_LABELS_RU = {
    "basic": "Б",
    "advanced": "П",
    "high": "В",
    "unknown": "н/д",
}


def normalize_difficulty(raw: str | None) -> DifficultyCode:
    """
    Приводит строку каталога/протокола к basic|advanced|high|unknown.

    Не угадывает: неизвестные значения → unknown (NOT_AVAILABLE).
    """
    if raw is None:
        return "unknown"
    text = str(raw).strip().lower()
    if not text:
        return "unknown"

    # Короткие коды
    if text in {"б", "b", "basic", "base"}:
        return "basic"
    if text in {"п", "p", "advanced", "повыш"}:
        return "advanced"
    if text in {"в", "v", "h", "high"}:
        return "high"

    # Полные слова (каталог: «Базовый», «Повышенный», «Высокий»)
    if "базов" in text or "basic" in text:
        return "basic"
    if "повыш" in text or "advanced" in text:
        return "advanced"
    if "высок" in text or "high" in text:
        return "high"

    return "unknown"


def difficulty_label(code: DifficultyCode) -> str:
    return DIFFICULTY_LABELS_RU.get(code, "н/д")


def is_advanced_or_high(code: DifficultyCode) -> bool:
    return code in {"advanced", "high"}
