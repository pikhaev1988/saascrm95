"""
Импорт справочника заданий ВПР из файла или каталога JSON.

Примеры:
  python manage.py import_vpr_task_catalog
  python manage.py import_vpr_task_catalog apps/vpr/catalog/data
  python manage.py import_vpr_task_catalog path/to/catalog.json
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.vpr.exceptions import VprCatalogImportError
from apps.vpr.services.catalog_import import import_catalog_path


class Command(BaseCommand):
    help = "Импорт справочника заданий ВПР (JSON / Excel / CSV или каталог data/)"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default=None,
            help="Файл или каталог. По умолчанию: apps/vpr/catalog/data",
        )

    def handle(self, *args, **options):
        raw = options.get("path")
        path = Path(raw) if raw else None
        if path is not None and not path.exists():
            raise CommandError(f"Путь не найден: {path}")
        try:
            record, stats = import_catalog_path(path)
        except VprCatalogImportError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(record.message))
        details = (record.details or {}).get("files") or []
        for line in details[:30]:
            self.stdout.write(f"  • {line}")
        if stats.messages:
            for msg in stats.messages[:20]:
                self.stdout.write(f"  - {msg}")
