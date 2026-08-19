"""Синхронизация справочника заданий ВПР при импорте протоколов."""

from __future__ import annotations

import logging

from apps.vpr.models import VprProtocol
from apps.vpr.services.catalog_bootstrap import ensure_protocol_catalog_entries
from apps.vpr.services.catalog_import import import_catalog_data_tree

logger = logging.getLogger(__name__)


def ensure_catalog_data_synced(*, user=None) -> bool:
    """
    Идемпотентный импорт JSON-дерева apps/vpr/catalog/data в БД.
    Вызывается после загрузки протокола, чтобы темы/умения подтянулись автоматически.
    """
    try:
        record, stats = import_catalog_data_tree(user=user)
        logger.info(
            "VPR catalog sync: status=%s created=%s updated=%s files",
            record.status,
            stats.created,
            stats.updated,
        )
        return True
    except Exception:  # noqa: BLE001
        logger.exception("VPR catalog sync failed")
        return False


def sync_catalog_for_protocol(protocol: VprProtocol, *, user=None) -> None:
    """
    После импорта протокола:
    1) синхронизировать JSON-справочник;
    2) дополнить записи по кодам заданий протокола (если есть seed-данные);
    3) сбросить кэш комплексного анализа.
    """
    ensure_catalog_data_synced(user=user)
    ensure_protocol_catalog_entries(protocol)
    from apps.vpr.comprehensive_analysis import clear_protocol_analysis_cache

    clear_protocol_analysis_cache(protocol.pk)
