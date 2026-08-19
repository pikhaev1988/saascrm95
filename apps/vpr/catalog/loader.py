"""Загрузка JSON-файлов нормативного справочника ВПР из catalog/data."""

from __future__ import annotations

from pathlib import Path

from apps.vpr.catalog.paths import catalog_data_root
from apps.vpr.services.catalog_import import load_rows_from_json


def discover_catalog_json_files(root: Path | str | None = None) -> list[Path]:
    base = catalog_data_root(root)
    if not base.exists():
        return []
    files = sorted(base.rglob("*.json"))
    return [path for path in files if path.name.upper() != "MANIFEST.JSON"]


def load_all_catalog_rows(root: Path | str | None = None) -> list[dict]:
    rows: list[dict] = []
    for path in discover_catalog_json_files(root):
        rows.extend(load_rows_from_json(path))
    return rows
