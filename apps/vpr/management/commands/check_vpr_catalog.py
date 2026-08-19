"""
Проверка качества справочника заданий ВПР.

  python manage.py check_vpr_catalog
  python manage.py check_vpr_catalog --warn-only
"""

from django.core.management.base import BaseCommand

from apps.vpr.catalog.quality import run_catalog_quality_check


class Command(BaseCommand):
    help = "Контроль качества справочника заданий ВПР"

    def add_arguments(self, parser):
        parser.add_argument(
            "--warn-only",
            action="store_true",
            help="Не завершать процесс с кодом ошибки",
        )
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Проверять также неактивные записи",
        )

    def handle(self, *args, **options):
        report = run_catalog_quality_check(active_only=not options["include_inactive"])
        sections = [
            ("Без темы", report.missing_topic),
            ("Без умения", report.missing_skill),
            ("Без раздела", report.missing_section),
            ("Дубликаты", report.duplicates),
            ("Некорректный класс", report.invalid_parallel),
            ("Пустой предмет", report.invalid_subject),
        ]
        if not report.has_issues:
            self.stdout.write(self.style.SUCCESS("Справочник ВПР: замечаний не найдено."))
            return

        self.stdout.write(self.style.WARNING(f"Найдено замечаний: {report.total_issues}"))
        for title, items in sections:
            if not items:
                continue
            self.stdout.write(f"\n{title} ({len(items)}):")
            for item in items[:50]:
                self.stdout.write(f"  - {item}")
            if len(items) > 50:
                self.stdout.write(f"  … ещё {len(items) - 50}")

        if not options["warn_only"]:
            raise SystemExit(1)
