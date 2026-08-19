"""Структуры анализа причин образовательных дефицитов ВПР."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class VprCauseSummary:
    significant_deficits_count: int
    causes_count: int
    local_count: int
    mass_count: int
    systemic_count: int
    dominant_cause_type: str
    dominant_scale: str
    catalog_coverage: str  # full / partial / none

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprCauseFinding:
    """Единица причинного анализа (задание / тема / умение / паттерн)."""

    problem: str
    skill: str
    topic: str
    section: str
    difficulty: str
    task_type: str
    cause: str
    cause_type: str
    scale: str
    character: str
    task_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprCausePattern:
    pattern_type: str
    title: str
    cause: str
    scale: str
    task_codes: list[str] = field(default_factory=list)
    related_topics: list[str] = field(default_factory=list)
    related_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprCauseAnalysisResult:
    protocol_id: int
    subject: str
    parallel: int
    academic_year: int
    summary: VprCauseSummary
    tasks: list[VprCauseFinding]
    topics: list[VprCauseFinding]
    skills: list[VprCauseFinding]
    patterns: list[VprCausePattern]

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "subject": self.subject,
            "parallel": self.parallel,
            "academic_year": self.academic_year,
            "summary": self.summary.to_dict(),
            "tasks": [item.to_dict() for item in self.tasks],
            "topics": [item.to_dict() for item in self.topics],
            "skills": [item.to_dict() for item in self.skills],
            "patterns": [item.to_dict() for item in self.patterns],
        }
