from __future__ import annotations

import json
import logging
from typing import Any

from users.gigachat_client import _analysis_enabled, chat_completion_json, gigachat_configured

logger = logging.getLogger(__name__)


EGE_SYSTEM_PROMPT = """
Ты — аналитический модуль для отчётов по результатам ЕГЭ (Россия).

Задача: улучшить текстовую часть отчёта — методический и управленческий анализ.
Стиль: официальные региональные и школьные аналитические материалы, без «воды» и без признаков машинной генерации.

Фокус анализа ЕГЭ:
- сформированность аналитических компетенций и развёрнутого ответа;
- вторая часть работы и задания повышенной сложности;
- системные предметные дефициты.

Шкала тестовых баллов 0–100 (интерпретация):
- 0–35: низкий уровень;
- 36–60: базовый;
- 61–80: повышенный;
- 81–100: высокий.

Не используй логику и формулировки ОГЭ (пятибалльную шкалу оценок 2–5).

Если вторая часть слабая — подчёркивай дефициты анализа, аргументации, структуры развёрнутого ответа.
Если много заданий с 0% успешности — укажи на системный провал подготовки.

Нормализуй сырые темы в короткие учебные домены (например, вместо длинного заголовка спецификации — «Генетика», «Общая биология»).

Рекомендации: ориентируй на отработку второй части, критериальную оценку, пробные экзамены, качество рассуждения.

Язык ответа: только русский. Не используй английские заголовки и англицизмы, если можно заменить русским термином.

Обязательное правило вывода: верни только валидный JSON в точности по запрошенной схеме (имена полей на латинице, как в запросе пользователя).
""".strip()


OGE_SYSTEM_PROMPT = """
Ты — аналитический модуль для отчётов по результатам ОГЭ (Россия).

Задача: улучшить текстовую часть отчёта — педагогический и управленческий анализ уровня ОО/муниципалитета.
Стиль: официальная школьная аналитика и методический мониторинг, без «воды».

Фокус анализа ОГЭ:
- устойчивость базовых умений и стандартных форматов заданий;
- предметные компетенции строго в логике указанного предмета (математика, русский язык, физика и т.д.);
- готовность к экзаменационному формату.

Если по данным видно шкалу до 5 баллов (макс. и средний балл не выше 5) — интерпретируй как пятибалльную: 2 — неуд., 3 — удовл., 4 — хорошо, 5 — отлично.
Не подменяй выводы логикой ЕГЭ (0–100).

КРИТИЧЕСКИ ВАЖНО:
- для математики используй математические компетенции (вычисления, алгебра, геометрия, моделирование), НЕ используй синтаксис и письменную речь;
- для русского языка — орфография, пунктуация, текст, письменная речь;
- для каждого предмета — только его терминологию и содержание КИМ;
- если has_part2_data=false, не делай выводов о провале части 2;
- не завышай негатив при высокой доле сдавших (pass_rate) и хорошем среднем балле.

Переводи сырые обозначения заданий в понятные предметные домены (алгебра, геометрия, орфография и т.п.), не выводи формулировки вида «Тема задания №2».

Рекомендации: стабилизация ключевых навыков, повторяемые тренировки, работа в стандартных форматах КИМ.
Для ОГЭ указывай параллели 5–9 классов, не 10–11.

Язык ответа: только русский.

Обязательное правило вывода: верни только валидный JSON в точности по запрошенной схеме (имена полей на латинице, как в запросе пользователя).
""".strip()


def _build_user_prompt(exam_context: dict[str, Any], exam_type: str) -> str:
    exam_label = "ОГЭ" if exam_type == "oge" else "ЕГЭ"
    class_rule = (
        "- использовать только темы и интерпретации для основной школы (5-9), без упоминания 10-11;\n"
        if exam_type == "oge"
        else "- использовать логику старшей школы и экзаменационного профиля ЕГЭ;\n"
    )
    return (
        f"Сформируй улучшенную аналитическую часть отчёта по {exam_label}.\n"
        f"Предмет экзамена: {exam_context.get('subject', 'не указан')}.\n"
        "Компетенции, темы и рекомендации должны строго соответствовать этому предмету.\n"
        "Требования к стилю: компактно, профессионально, без повторов и без общих фраз.\n"
        "Обязательно:\n"
        "- нормализуй образовательные домены в короткие понятные формулировки;\n"
        "- объединяй семантически близкие домены;\n"
        "- связывай дефицит по заданию с дефицитом сформированного умения (межзадательные связи);\n"
        "- учитывай степень серьёзности дефицита (критический / значимый / умеренный) в формулировках и рекомендациях;\n"
        "- выводы о готовности к экзамену должны строго соответствовать статистике.\n"
        + class_rule
        + "Нужно вернуть JSON строго со следующей структурой (имена полей — латиницей, как ниже; все текстовые значения — на русском языке):\n"
        "{\n"
        '  "executive_summary": ["строка1", "строка2", "строка3", "строка4"],\n'
        '  "systemic_problems": ["..."],\n'
        '  "local_problems": ["..."],\n'
        '  "severity_summary": {\n'
        '    "critical": "...",\n'
        '    "significant": "...",\n'
        '    "moderate": "..."\n'
        "  },\n"
        '  "cross_skill_analysis": ["..."],\n'
        '  "conclusion": "одна итоговая управленческая формулировка",\n'
        '  "recommendations_override": {\n'
        '    "Задания": ["..."],\n'
        '    "Темы": ["..."],\n'
        '    "Навыки": ["..."],\n'
        '    "Экзаменационная стратегия": ["..."]\n'
        "  }\n"
        "}\n\n"
        "Контекст данных:\n"
        f"{json.dumps(exam_context, ensure_ascii=False, indent=2)}"
    )


def _exam_type_label(exam_type: str) -> str:
    return "ОГЭ" if exam_type == "oge" else "ЕГЭ"


def _resolve_exam_type(exam_context: dict[str, Any]) -> str:
    exam_type = str(exam_context.get("exam_type") or "ege").lower()
    return exam_type if exam_type in {"ege", "oge"} else "ege"


def enhance_exam_analysis(exam_context: dict[str, Any]) -> dict[str, Any] | None:
    """Улучшение аналитической справки по одному экзамену (ЕГЭ/ОГЭ) через GigaChat."""
    if not _analysis_enabled():
        return None
    if not gigachat_configured():
        logger.warning("GIGACHAT_ANALYSIS_ENABLED, но учётные данные GigaChat не заданы.")
        return None

    exam_type = _resolve_exam_type(exam_context)
    system_prompt = OGE_SYSTEM_PROMPT if exam_type == "oge" else EGE_SYSTEM_PROMPT

    return chat_completion_json(
        system_prompt=system_prompt,
        user_prompt=_build_user_prompt(exam_context, exam_type),
        temperature=0.2,
    )


def enhance_analysis_with_gigachat(exam_context: dict[str, Any]) -> dict[str, Any] | None:
    """Обратная совместимость: алиас для enhance_exam_analysis."""
    return enhance_exam_analysis(exam_context)


def _build_school_summary_user_prompt(
    exam_type: str,
    stats: dict[str, Any],
    report_kind: str,
    draft: dict[str, list[str]],
) -> str:
    exam_label = _exam_type_label(exam_type)
    kind_labels = {
        "summary": "сводной информационной статистики школы",
        "analytic_note": "аналитической справки школы",
        "deputy": "отчёта заместителя директора",
        "dashboard": "экрана сводки в личном кабинете школы",
    }
    kind_label = kind_labels.get(report_kind, "школьного отчёта")
    return (
        f"Сформируй текстовые блоки для {kind_label} по {exam_label}.\n"
        "Опирайся только на переданную статистику; не выдумывай цифры.\n"
        "Стиль: официальный, управленческий, без общих фраз и без английских заголовков.\n"
        "Черновые формулировки ниже можно улучшить и заменить, сохранив факты.\n\n"
        "Верни JSON строго такой структуры (все значения — на русском):\n"
        "{\n"
        '  "insights": ["ключевой вывод 1", "..."],\n'
        '  "recommendations": ["рекомендация 1", "..."],\n'
        '  "conclusions": ["вывод 1", "..."],\n'
        '  "executive_summary": ["резюме 1", "..."]\n'
        "}\n\n"
        f"Черновики:\n{json.dumps(draft, ensure_ascii=False, indent=2)}\n\n"
        f"Статистика:\n{json.dumps(stats, ensure_ascii=False, indent=2)}"
    )


def _generate_school_summary_ai(
    exam_type: str,
    stats: dict[str, Any],
    report_kind: str,
    draft: dict[str, list[str]],
) -> dict[str, Any] | None:
    if not _analysis_enabled() or not gigachat_configured():
        return None
    system_prompt = OGE_SYSTEM_PROMPT if exam_type == "oge" else EGE_SYSTEM_PROMPT
    return chat_completion_json(
        system_prompt=system_prompt,
        user_prompt=_build_school_summary_user_prompt(exam_type, stats, report_kind, draft),
        temperature=0.2,
    )


def _merge_text_list(primary: list[str] | None, fallback: list[str] | None, limit: int = 8) -> list[str]:
    source = primary if primary else fallback
    if not source:
        return []
    return [str(item).strip() for item in source if str(item).strip()][:limit]


def enrich_school_summary_with_ai(
    *,
    exam_type: str,
    stats: dict[str, Any],
    report_kind: str = "summary",
    draft_insights: list[str] | None = None,
    draft_recommendations: list[str] | None = None,
    draft_conclusions: list[str] | None = None,
    draft_executive_summary: list[str] | None = None,
) -> dict[str, list[str]]:
    """
    Обогащает школьные сводки через GigaChat.
    При недоступности API возвращает черновые (шаблонные) формулировки.
    """
    exam_type = _resolve_exam_type({"exam_type": exam_type})
    draft = {
        "insights": list(draft_insights or []),
        "recommendations": list(draft_recommendations or []),
        "conclusions": list(draft_conclusions or []),
        "executive_summary": list(draft_executive_summary or []),
    }
    fallback = {key: list(value) for key, value in draft.items()}
    ai_result = _generate_school_summary_ai(exam_type, stats, report_kind, draft)
    if not isinstance(ai_result, dict):
        return fallback

    return {
        "insights": _merge_text_list(
            ai_result.get("insights") if isinstance(ai_result.get("insights"), list) else None,
            fallback["insights"],
        ),
        "recommendations": _merge_text_list(
            ai_result.get("recommendations") if isinstance(ai_result.get("recommendations"), list) else None,
            fallback["recommendations"],
        ),
        "conclusions": _merge_text_list(
            ai_result.get("conclusions") if isinstance(ai_result.get("conclusions"), list) else None,
            fallback["conclusions"],
        ),
        "executive_summary": _merge_text_list(
            ai_result.get("executive_summary") if isinstance(ai_result.get("executive_summary"), list) else None,
            fallback["executive_summary"],
        ),
    }
