"""Пользовательские формулировки вместо технических enum."""

from __future__ import annotations

USER_LABELS = {
    "EDUCATIONAL_DIFFICULTY": "образовательное затруднение",
    "EDUCATIONAL_DEFICIT": "образовательный дефицит",
    "LIMITED_SAMPLE": "Выборка недостаточна для информативного группового анализа",
    "HYPOTHESIS": "Возможная причина требует дополнительной проверки",
    "INFORMATIVE": "диагностическая информация",
    "INSUFFICIENT_DATA": "недостаточно данных",
    "NOT_AVAILABLE": "данные отсутствуют",
    "ESTABLISHED": "подтверждено данными ВПР",
    "SYSTEM_ANALYTICS": "внутренняя аналитика системы",
    "FIOKO_2026": "методология ФИОКО 2026",
    "LOCAL_ANALYTICS": "локальная аналитика",
    "OVERLAPPING_GROUP": "дополнительная (перекрывающаяся) характеристика",
    "EXCLUSIVE": "взаимоисключающая группа",
    "FACT": "факт",
    "GENERAL_PEAK": "общий пик распределения",
}


def user_label(code: str | None, *, default: str | None = None) -> str:
    if not code:
        return default or ""
    key = str(code).strip()
    return USER_LABELS.get(key, default if default is not None else key)
