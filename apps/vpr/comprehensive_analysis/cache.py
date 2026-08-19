"""Кэш комплексного анализа ВПР (Django Cache / Redis-ready)."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.cache import caches

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "vpr:comprehensive_analysis"


def analysis_cache_enabled() -> bool:
    return bool(getattr(settings, "VPR_ANALYSIS_CACHE_ENABLED", False))


def analysis_cache_timeout() -> int:
    return int(getattr(settings, "VPR_ANALYSIS_CACHE_TIMEOUT", 3600))


def analysis_cache_alias() -> str:
    return str(getattr(settings, "VPR_ANALYSIS_CACHE_ALIAS", "default"))


def make_analysis_cache_key(protocol_id: int, *, revision: str = "") -> str:
    base = f"{CACHE_KEY_PREFIX}:{int(protocol_id)}"
    if revision:
        return f"{base}:r:{revision}"
    return base


def get_cached_analysis(protocol_id: int) -> Any | None:
    if not analysis_cache_enabled():
        return None
    try:
        cache = caches[analysis_cache_alias()]
        return cache.get(make_analysis_cache_key(protocol_id))
    except Exception:  # noqa: BLE001
        logger.warning("VPR analysis cache get failed protocol_id=%s", protocol_id, exc_info=True)
        return None


def set_cached_analysis(protocol_id: int, analysis: Any) -> None:
    if not analysis_cache_enabled():
        return
    try:
        cache = caches[analysis_cache_alias()]
        cache.set(make_analysis_cache_key(protocol_id), analysis, analysis_cache_timeout())
    except Exception:  # noqa: BLE001
        logger.warning("VPR analysis cache set failed protocol_id=%s", protocol_id, exc_info=True)


def invalidate_protocol_analysis(protocol_id: int) -> None:
    """Сброс кэша анализа протокола (после реимпорта / правок)."""
    if not analysis_cache_enabled():
        return
    try:
        cache = caches[analysis_cache_alias()]
        cache.delete(make_analysis_cache_key(protocol_id))
    except Exception:  # noqa: BLE001
        logger.warning(
            "VPR analysis cache invalidate failed protocol_id=%s",
            protocol_id,
            exc_info=True,
        )
