"""
Единая точка получения комплексного анализа ВПР для View / API.

View не вызывает Analytics/Deficit/Cause/Conclusion напрямую.
"""

from __future__ import annotations

import logging

from apps.vpr.comprehensive_analysis.cache import (
    get_cached_analysis,
    invalidate_protocol_analysis,
    set_cached_analysis,
)
from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
from apps.vpr.comprehensive_analysis.schemas import VprComprehensiveAnalysisResult
from apps.vpr.models import VprProtocol

logger = logging.getLogger(__name__)


def get_protocol_analysis(
    protocol: VprProtocol | int,
    *,
    engine: VprComprehensiveAnalysisEngine | None = None,
    use_cache: bool | None = None,
) -> VprComprehensiveAnalysisResult:
    """
    Получить единый объект анализа протокола.

    use_cache=None — следовать settings.VPR_ANALYSIS_CACHE_ENABLED.
    use_cache=False — всегда пересчитать (удобно для тестов).
    """
    protocol_obj = protocol if isinstance(protocol, VprProtocol) else VprProtocol.objects.get(pk=int(protocol))
    protocol_id = int(protocol_obj.pk)

    allow_cache = True if use_cache is None else bool(use_cache)
    if allow_cache:
        cached = get_cached_analysis(protocol_id)
        if cached is not None:
            logger.debug("VPR analysis cache hit protocol_id=%s", protocol_id)
            return cached

    result = (engine or VprComprehensiveAnalysisEngine()).analyze(protocol_obj)
    if allow_cache:
        set_cached_analysis(protocol_id, result)
    return result


def clear_protocol_analysis_cache(protocol: VprProtocol | int) -> None:
    protocol_obj = protocol if isinstance(protocol, VprProtocol) else None
    protocol_id = int(protocol.pk if protocol_obj is not None else protocol)
    invalidate_protocol_analysis(protocol_id)
    if protocol_obj is None:
        try:
            protocol_obj = VprProtocol.objects.only("school_id", "academic_year").get(pk=protocol_id)
        except VprProtocol.DoesNotExist:
            return
    if protocol_obj.school_id:
        from apps.vpr.school_analysis_cache import invalidate_school_analysis

        invalidate_school_analysis(protocol_obj.school_id, protocol_obj.academic_year)
        invalidate_school_analysis(protocol_obj.school_id, None)
