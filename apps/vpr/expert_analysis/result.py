"""DTO экспертной интерпретации — только тексты и классификаторы, без новых метрик."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class CompetenceInsight:
    name: str
    status: str  # formed | partial | weak | insufficient_data
    status_label: str
    evidence: list[str] = field(default_factory=list)
    conclusion: str = ""


@dataclass(slots=True)
class PatternInsight:
    kind: str  # thematic | competence | systemic | cognitive
    title: str
    explanation: str
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CauseChain:
    steps: list[str]
    summary: str


@dataclass(slots=True)
class ExpertAnalysisResult:
    """Полная экспертная интерпретация предмета."""

    profile_code: str = ""
    profile_label: str = ""
    profile_explanation: list[str] = field(default_factory=list)

    cognitive_code: str = ""
    cognitive_label: str = ""
    cognitive_analysis: list[str] = field(default_factory=list)

    competences: list[CompetenceInsight] = field(default_factory=list)
    competences_analysis: list[str] = field(default_factory=list)

    patterns: list[PatternInsight] = field(default_factory=list)
    patterns_analysis: list[str] = field(default_factory=list)

    structure_analysis: list[str] = field(default_factory=list)

    strengths: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    cause_chains: list[CauseChain] = field(default_factory=list)
    causes_analysis: list[str] = field(default_factory=list)

    overview: list[str] = field(default_factory=list)
    quality_analysis: list[str] = field(default_factory=list)
    statistics_analysis: list[str] = field(default_factory=list)
    tasks_analysis: list[str] = field(default_factory=list)
    topics_analysis: list[str] = field(default_factory=list)
    skills_analysis: list[str] = field(default_factory=list)
    deficits_analysis: list[str] = field(default_factory=list)
    final_conclusion: list[str] = field(default_factory=list)

    subject: str = ""
    parallel: int | None = None
    academic_year: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
