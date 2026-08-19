"""Нормативный справочник заданий ВПР (JSON-данные)."""

from pathlib import Path

CATALOG_DATA_ROOT = Path(__file__).resolve().parent / "data"

__all__ = ["CATALOG_DATA_ROOT"]
