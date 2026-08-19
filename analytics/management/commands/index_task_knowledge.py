from django.core.management.base import BaseCommand

from analytics.knowledge.service import TaskKnowledgeIndexer


class Command(BaseCommand):
    help = "Индексация FIPI Knowledge Base из официальных каталогов (ege/oge enriched JSON)"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=2026, help="Год документов ФИПИ")

    def handle(self, *args, **options):
        year = options["year"]
        stats = TaskKnowledgeIndexer().index_all(document_year=year)
        self.stdout.write(
            self.style.SUCCESS(
                f"Индексация завершена: ЕГЭ={stats['ege']}, ОГЭ={stats['oge']}, обновлено={stats['updated']}"
            )
        )
