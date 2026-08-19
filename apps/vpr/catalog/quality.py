"""Контроль качества записей справочника заданий ВПР."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db.models import Count

from apps.vpr.models import VprTaskCatalogEntry

VALID_PARALLELS = set(range(1, 11))


@dataclass
class CatalogQualityReport:
    missing_topic: list[str] = field(default_factory=list)
    missing_skill: list[str] = field(default_factory=list)
    missing_section: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    invalid_parallel: list[str] = field(default_factory=list)
    invalid_subject: list[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return any(
            [
                self.missing_topic,
                self.missing_skill,
                self.missing_section,
                self.duplicates,
                self.invalid_parallel,
                self.invalid_subject,
            ]
        )

    @property
    def total_issues(self) -> int:
        return (
            len(self.missing_topic)
            + len(self.missing_skill)
            + len(self.missing_section)
            + len(self.duplicates)
            + len(self.invalid_parallel)
            + len(self.invalid_subject)
        )


def _label(entry: VprTaskCatalogEntry) -> str:
    return (
        f"#{entry.pk} {entry.subject} {entry.parallel}кл "
        f"{entry.academic_year} код={entry.task_code or entry.task_number}"
    )


def catalog_quality_check(*, active_only: bool = True) -> CatalogQualityReport:
    """Публичная точка входа контроля качества справочника."""
    return run_catalog_quality_check(active_only=active_only)


def run_catalog_quality_check(*, active_only: bool = True) -> CatalogQualityReport:
    qs = VprTaskCatalogEntry.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)

    report = CatalogQualityReport()
    for entry in qs.iterator():
        label = _label(entry)
        if not (entry.topic or "").strip():
            report.missing_topic.append(label)
        if not (entry.checked_skill or "").strip():
            report.missing_skill.append(label)
        if not (entry.program_section or "").strip():
            report.missing_section.append(label)
        if entry.parallel not in VALID_PARALLELS:
            report.invalid_parallel.append(label)
        if not (entry.subject or "").strip():
            report.invalid_subject.append(label)

    dup_qs = (
        qs.values("academic_year", "subject", "parallel", "task_code")
        .exclude(task_code="")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
    )
    for row in dup_qs:
        report.duplicates.append(
            f"{row['subject']} {row['parallel']}кл {row['academic_year']} "
            f"код={row['task_code']} ×{row['cnt']}"
        )
    return report
