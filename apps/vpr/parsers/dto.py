from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


@dataclass(slots=True)
class VprTaskMeta:
    position: int
    code: str
    title: str
    max_score: int
    difficulty: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprTaskScoreData:
    task_code: str
    raw_value: str
    score: float | None
    max_score: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprStudentRow:
    participant_code: str
    organization_code: str = ""
    organization_name: str = ""
    municipality: str = ""
    class_group: str = ""
    variant: str = ""
    gender: str = ""
    full_name: str = ""
    primary_score: float | None = None
    mark_vpr: int | None = None
    mark_journal: int | None = None
    source_row: int | None = None
    task_scores: list[VprTaskScoreData] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


@dataclass(slots=True)
class VprParseResult:
    """Нормализованный результат разбора файла ВПР."""

    template_key: str
    sheet_name: str
    source_title: str
    subject: str
    parallel: int
    academic_year: int
    exam_date: date | None
    max_primary_score: int
    organization_code: str
    organization_name: str
    municipality: str
    participants_declared: int | None
    tasks: list[VprTaskMeta]
    students: list[VprStudentRow]
    warnings: list[str] = field(default_factory=list)

    @property
    def participants_count(self) -> int:
        return len(self.students)

    @property
    def tasks_count(self) -> int:
        return len(self.tasks)

    def preview_dict(self) -> dict[str, Any]:
        return {
            "template_key": self.template_key,
            "sheet_name": self.sheet_name,
            "source_title": self.source_title,
            "subject": self.subject,
            "parallel": self.parallel,
            "academic_year": self.academic_year,
            "exam_date": self.exam_date.isoformat() if self.exam_date else None,
            "max_primary_score": self.max_primary_score,
            "organization_code": self.organization_code,
            "organization_name": self.organization_name,
            "municipality": self.municipality,
            "participants_declared": self.participants_declared,
            "participants_count": self.participants_count,
            "tasks_count": self.tasks_count,
            "tasks": [t.to_dict() for t in self.tasks],
            "warnings": list(self.warnings),
            "sample_students": [
                {
                    "participant_code": s.participant_code,
                    "class_group": s.class_group,
                    "variant": s.variant,
                    "primary_score": s.primary_score,
                    "mark_vpr": s.mark_vpr,
                    "mark_journal": s.mark_journal,
                }
                for s in self.students[:5]
            ],
        }
