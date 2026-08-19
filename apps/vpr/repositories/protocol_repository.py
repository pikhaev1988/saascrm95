"""Репозиторий сохранения сущностей ВПР."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.vpr.models import (
    VprImportLog,
    VprImportLogLevel,
    VprProtocol,
    VprStudentResult,
    VprTask,
    VprTaskScore,
    VprUpload,
    VprUploadStatus,
)
from apps.vpr.parsers.dto import VprParseResult
from organizations.models import School


class VprProtocolRepository:
    @staticmethod
    def add_log(
        upload: VprUpload,
        message: str,
        *,
        level: str = VprImportLogLevel.INFO,
        details: dict | None = None,
    ) -> VprImportLog:
        return VprImportLog.objects.create(
            upload=upload,
            level=level,
            message=message,
            details=details or {},
        )

    @classmethod
    @transaction.atomic
    def persist_import(
        cls,
        upload: VprUpload,
        parsed: VprParseResult,
        *,
        school: School | None,
    ) -> VprProtocol:
        # Повторный импорт той же загрузки — очищаем предыдущий протокол.
        VprProtocol.objects.filter(upload=upload).delete()

        protocol = VprProtocol.objects.create(
            upload=upload,
            school=school,
            organization_code=parsed.organization_code,
            organization_name=parsed.organization_name,
            municipality=parsed.municipality,
            subject=parsed.subject,
            parallel=parsed.parallel,
            academic_year=parsed.academic_year,
            exam_date=parsed.exam_date,
            max_primary_score=parsed.max_primary_score,
            participants_count=parsed.participants_count,
            tasks_count=parsed.tasks_count,
            source_title=parsed.source_title,
            sheet_name=parsed.sheet_name,
        )

        task_map: dict[str, VprTask] = {}
        tasks = [
            VprTask(
                protocol=protocol,
                position=task.position,
                code=task.code,
                title=task.title,
                max_score=task.max_score,
                difficulty=task.difficulty,
            )
            for task in parsed.tasks
        ]
        VprTask.objects.bulk_create(tasks)
        for task in VprTask.objects.filter(protocol=protocol):
            task_map[task.code] = task

        results: list[VprStudentResult] = []
        for row in parsed.students:
            results.append(
                VprStudentResult(
                    protocol=protocol,
                    participant_code=row.participant_code,
                    full_name=row.full_name,
                    gender=row.gender,
                    class_group=row.class_group,
                    variant=row.variant,
                    primary_score=row.primary_score,
                    mark_vpr=row.mark_vpr,
                    mark_journal=row.mark_journal,
                    source_row=row.source_row,
                )
            )
        VprStudentResult.objects.bulk_create(results)

        result_map = {
            item.participant_code: item
            for item in VprStudentResult.objects.filter(protocol=protocol)
        }

        scores: list[VprTaskScore] = []
        for row in parsed.students:
            result = result_map[row.participant_code]
            for score_data in row.task_scores:
                task = task_map.get(score_data.task_code)
                if not task:
                    continue
                scores.append(
                    VprTaskScore(
                        result=result,
                        task=task,
                        raw_value=score_data.raw_value,
                        score=score_data.score,
                        max_score=score_data.max_score,
                    )
                )
        if scores:
            VprTaskScore.objects.bulk_create(scores, batch_size=500)

        upload.status = VprUploadStatus.IMPORTED
        upload.template_key = parsed.template_key
        upload.students_imported = parsed.participants_count
        upload.results_imported = parsed.participants_count
        upload.tasks_imported = parsed.tasks_count
        upload.errors_count = 0
        upload.processed_at = timezone.now()
        upload.error_message = ""
        upload.school = school or upload.school
        upload.save(
            update_fields=[
                "status",
                "template_key",
                "students_imported",
                "results_imported",
                "tasks_imported",
                "errors_count",
                "processed_at",
                "error_message",
                "school",
            ]
        )

        cls.add_log(
            upload,
            (
                f"Импорт завершён: учащихся {parsed.participants_count}, "
                f"результатов {parsed.participants_count}, заданий {parsed.tasks_count}."
            ),
            details={
                "subject": parsed.subject,
                "parallel": parsed.parallel,
                "academic_year": parsed.academic_year,
            },
        )
        return protocol
