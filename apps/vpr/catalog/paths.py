"""Пути к нормативным JSON справочника ВПР."""

from __future__ import annotations

from pathlib import Path

CATALOG_DATA_ROOT = Path(__file__).resolve().parent / "data"


def catalog_data_root(override: Path | str | None = None) -> Path:
    if override:
        return Path(override)
    return CATALOG_DATA_ROOT
