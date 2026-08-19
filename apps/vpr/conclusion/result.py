"""Структуры аналитического заключения ВПР (ФИОКО)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class VprConclusionItem:
    """Элемент списка (задание / тема / умение) с готовым текстом."""

    code: str
    title: str
    detail: str
    percent: float | None = None
    level: str = ""
    risk: str = ""
    priority: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprConclusionSection:
    """Раздел заключения: заголовок, абзацы, опциональные элементы."""

    key: str
    title: str
    paragraphs: list[str] = field(default_factory=list)
    items: list[VprConclusionItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "paragraphs": list(self.paragraphs),
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(slots=True)
class VprConclusionResult:
    protocol_id: int
    subject: str
    parallel: int
    academic_year: int
    overview: VprConclusionSection
    statistics: VprConclusionSection
    strengths: VprConclusionSection
    weaknesses: VprConclusionSection
    topics: VprConclusionSection
    skills: VprConclusionSection
    deficits: VprConclusionSection
    final_conclusion: VprConclusionSection

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "subject": self.subject,
            "parallel": self.parallel,
            "academic_year": self.academic_year,
            "overview": self.overview.to_dict(),
            "statistics": self.statistics.to_dict(),
            "strengths": self.strengths.to_dict(),
            "weaknesses": self.weaknesses.to_dict(),
            "topics": self.topics.to_dict(),
            "skills": self.skills.to_dict(),
            "deficits": self.deficits.to_dict(),
            "final_conclusion": self.final_conclusion.to_dict(),
        }

    @property
    def sections(self) -> list[VprConclusionSection]:
        return [
            self.overview,
            self.statistics,
            self.strengths,
            self.weaknesses,
            self.topics,
            self.skills,
            self.deficits,
            self.final_conclusion,
        ]
