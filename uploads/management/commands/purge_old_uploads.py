from __future__ import annotations

import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from uploads.models import UploadSession, UploadStatus


class Command(BaseCommand):
    help = "Deletes old upload sessions and their files to reduce personal-data retention risk."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=int(os.getenv("UPLOAD_RETENTION_DAYS", "180")),
            help="Retention period in days (default: 180 or UPLOAD_RETENTION_DAYS env).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many records/files would be deleted without applying changes.",
        )

    def handle(self, *args, **options):
        retention_days = max(int(options["days"]), 1)
        dry_run = bool(options["dry_run"])
        cutoff = timezone.now() - timedelta(days=retention_days)

        qs = UploadSession.objects.filter(
            created_at__lt=cutoff,
            status__in=(UploadStatus.DONE, UploadStatus.FAILED),
        ).only("id", "file")

        candidates = list(qs)
        files_count = sum(1 for item in candidates if bool(item.file))
        self.stdout.write(
            f"Found {len(candidates)} upload sessions older than {retention_days} days. "
            f"Files attached: {files_count}."
        )
        if dry_run or not candidates:
            self.stdout.write(self.style.WARNING("Dry run mode: no changes applied.") if dry_run else "Nothing to purge.")
            return

        deleted_files = 0
        for item in candidates:
            if item.file:
                item.file.delete(save=False)
                deleted_files += 1

        deleted_rows, _ = qs.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted rows: {deleted_rows}. Deleted files: {deleted_files}. Cutoff date: {cutoff:%Y-%m-%d}."
            )
        )
