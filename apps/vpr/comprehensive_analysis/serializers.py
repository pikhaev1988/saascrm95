"""Сериализация комплексного профиля ВПР в JSON-совместимые структуры."""

from __future__ import annotations

from typing import Any

from apps.vpr.comprehensive_analysis.schemas import VprComprehensiveAnalysisResult


def serialize_comprehensive_result(result: VprComprehensiveAnalysisResult) -> dict[str, Any]:
    """Полный JSON-профиль без вложенного сырого analytics (компактный API-ответ)."""
    return result.to_dict()


def serialize_comprehensive_result_full(result: VprComprehensiveAnalysisResult) -> dict[str, Any]:
    """Полный ответ включая сырой analytics.to_dict() для отладки."""
    payload = result.to_dict()
    payload["analytics"] = dict(result.analytics or {})
    return payload
