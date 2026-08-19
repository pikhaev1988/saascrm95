"""
Единая точка входа для ИИ в проекте.

Все сценарии анализа текстов используют только GigaChat (Сбер).
Настройка — переменные GIGACHAT_* в .env (см. .env.example).
"""

from users.district_gigachat_analysis import enrich_district_report_with_ai
from users.gigachat_analysis import (
    enhance_analysis_with_gigachat,
    enhance_exam_analysis,
    enrich_school_summary_with_ai,
)
from users.gigachat_client import (
    chat_completion_json,
    chat_completion_text,
    gigachat_configured,
)

__all__ = [
    "chat_completion_json",
    "chat_completion_text",
    "enhance_analysis_with_gigachat",
    "enhance_exam_analysis",
    "enrich_district_report_with_ai",
    "enrich_school_summary_with_ai",
    "gigachat_configured",
]
