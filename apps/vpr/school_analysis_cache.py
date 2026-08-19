"""Кэш школьной аналитики ВПР на уровне view (без изменения движков)."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.cache import caches

from apps.vpr.school_analysis import VprSchoolAnalysisEngine
from organizations.models import School

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "vpr:school_analysis"


def _cache_enabled() -> bool:
    return bool(getattr(settings, "VPR_ANALYSIS_CACHE_ENABLED", False))


def _cache_timeout() -> int:
    return int(getattr(settings, "VPR_ANALYSIS_CACHE_TIMEOUT", 3600))


def _cache_alias() -> str:
    return str(getattr(settings, "VPR_ANALYSIS_CACHE_ALIAS", "default"))


def make_school_analysis_cache_key(school_id: int, academic_year: int | None) -> str:
    year_part = str(academic_year) if academic_year is not None else "all"
    return f"{CACHE_KEY_PREFIX}:{int(school_id)}:{year_part}"


def get_school_analysis(school: School, academic_year: int | None):
    """Получить SchoolAnalysisResult с кэшированием результата оркестратора."""
    if not _cache_enabled():
        return VprSchoolAnalysisEngine().analyze(school, academic_year)

    key = make_school_analysis_cache_key(school.pk, academic_year)
    try:
        cache = caches[_cache_alias()]
        cached = cache.get(key)
        if cached is not None:
            return cached
    except Exception:  # noqa: BLE001
        logger.warning("VPR school analysis cache get failed school_id=%s", school.pk, exc_info=True)
        return VprSchoolAnalysisEngine().analyze(school, academic_year)

    analysis = VprSchoolAnalysisEngine().analyze(school, academic_year)
    try:
        cache.set(key, analysis, _cache_timeout())
    except Exception:  # noqa: BLE001
        logger.warning("VPR school analysis cache set failed school_id=%s", school.pk, exc_info=True)
    return analysis


def invalidate_school_analysis(school_id: int, academic_year: int | None = None) -> None:
    if not _cache_enabled():
        return
    try:
        cache = caches[_cache_alias()]
        if academic_year is None:
            # точечный сброс всех лет недоступен в LocMem без ключей — сбрасываем «all»
            cache.delete(make_school_analysis_cache_key(school_id, None))
            return
        cache.delete(make_school_analysis_cache_key(school_id, academic_year))
    except Exception:  # noqa: BLE001
        logger.warning(
            "VPR school analysis cache invalidate failed school_id=%s",
            school_id,
            exc_info=True,
        )
