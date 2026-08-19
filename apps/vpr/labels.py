"""Русские подписи для кодов ВПР (риск, приоритет, тренд и т.п.)."""

from __future__ import annotations

RISK_LEVEL_LABELS = {
    "high": "Высокий",
    "medium": "Средний",
    "low": "Низкий",
    "critical": "Критический",
}

SCHOOL_RISK_CLASSIFICATION_LABELS = {
    "HIGH_RISK": "Высокий риск",
    "MEDIUM_RISK": "Средний риск",
    "LOW_RISK": "Низкий риск",
    "STABLE": "Стабильный профиль",
}

PRIORITY_LABELS = {
    "Critical": "Критический",
    "High": "Высокий",
    "Medium": "Средний",
    "Low": "Низкий",
    "critical": "Критический",
    "high": "Высокий",
    "medium": "Средний",
    "low": "Низкий",
}

TREND_LABELS = {
    "up": "Рост",
    "down": "Снижение",
    "stable": "Стабильно",
    "baseline": "Базовый год",
}

MASTERY_LEVEL_LABELS = {
    "high": "Высокий уровень",
    "sufficient": "Достаточный уровень",
    "acceptable": "Допустимый уровень",
    "problem": "Проблемная зона",
    "critical": "Критический дефицит",
}

TASK_STATUS_LABELS = {
    "HIGH": "Высокий результат",
    "NORMAL": "Норма",
    "RISK": "Зона риска",
    "CRITICAL": "Критический дефицит",
    "critical_deficit": "Критический дефицит",
    "problem_zone": "Проблемная зона",
    "ok": "Норма",
}


def _lookup(mapping: dict[str, str], value: str) -> str | None:
    if value in mapping:
        return mapping[value]
    lower = value.lower()
    if lower in mapping:
        return mapping[lower]
    upper = value.upper()
    if upper in mapping:
        return mapping[upper]
    title = value[:1].upper() + value[1:].lower() if value else value
    if title in mapping:
        return mapping[title]
    return None


def label_risk(value) -> str:
    if value in (None, ""):
        return "—"
    text = str(value).strip()
    return _lookup(RISK_LEVEL_LABELS, text) or _lookup(PRIORITY_LABELS, text) or text


def label_school_risk(value) -> str:
    if value in (None, ""):
        return "—"
    text = str(value).strip()
    return SCHOOL_RISK_CLASSIFICATION_LABELS.get(text, text)


def label_priority(value) -> str:
    if value in (None, ""):
        return "—"
    text = str(value).strip()
    return _lookup(PRIORITY_LABELS, text) or text


def label_trend(value) -> str:
    if value in (None, ""):
        return "—"
    text = str(value).strip()
    return TREND_LABELS.get(text.lower(), text)


def label_mastery(value) -> str:
    if value in (None, ""):
        return "—"
    text = str(value).strip()
    return MASTERY_LEVEL_LABELS.get(text.lower(), text)


def label_status(value) -> str:
    if value in (None, ""):
        return "—"
    text = str(value).strip()
    return _lookup(TASK_STATUS_LABELS, text) or text
