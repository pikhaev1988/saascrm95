from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALIDATION_ERROR_MESSAGE = "Аналитика не построена. Обнаружено несоответствие расчетных данных."


@dataclass
class TaskAnalysis:
    task_number: int
    total: int
    correct: int
    wrong: int
    blank: int
    success_rate: float
    error_rate: float
    blank_rate: float
    avg_score: float | None
    difficulty: float
    discrimination: float
    score_correlation: float
    result_contribution: float
    classification: str
    topic: str
    section: str
    subsection: str
    fipi_code: str
    skill: str
    skill_name: str
    grade_range: list[int]
    exam_part: int
    max_score: float | None
    metadata: dict = field(default_factory=dict)


@dataclass
class TopicAnalysis:
    topic: str
    section: str
    task_numbers: list[int]
    success_rate: float
    error_count: int
    student_attempts: int


@dataclass
class SkillAnalysis:
    skill: str
    skill_name: str
    success_rate: float
    task_numbers: list[int]
    classification: str


@dataclass
class PrepLevelGroup:
    key: str
    label: str
    count: int
    share: float
    avg_score: float
    pass_rate: float
    weak_tasks: list[int]


@dataclass
class ExamAnalysisResult:
    valid: bool
    error_message: str | None = None
    subject: str = ""
    exam_type: str = "ege"
    exam_id: int | None = None
    exam_year: int | None = None
    exam_date: str = ""
    measure_mode: str = "percent"
    students_count: int = 0
    avg_score: float = 0.0
    median_score: float = 0.0
    min_score: float = 0.0
    max_score: float = 0.0
    pass_rate: float = 0.0
    fail_rate: float = 0.0
    score_distribution: dict[str, int] = field(default_factory=dict)
    tasks: list[TaskAnalysis] = field(default_factory=list)
    topics: list[TopicAnalysis] = field(default_factory=list)
    skills: list[SkillAnalysis] = field(default_factory=list)
    prep_levels: list[PrepLevelGroup] = field(default_factory=list)
    part1_success_rate: float | None = None
    part2_success_rate: float | None = None
    part_gap: float | None = None
    strong_tasks: list[int] = field(default_factory=list)
    weak_tasks: list[int] = field(default_factory=list)
    critical_tasks: list[int] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    methodical_recommendations: list[dict[str, Any]] = field(default_factory=list)
    correlations: dict[str, Any] = field(default_factory=dict)
    dynamics: list[dict[str, Any]] = field(default_factory=list)
    validation_details: list[str] = field(default_factory=list)
    sections: dict[str, list[str]] = field(default_factory=dict)
    control_plan: list[dict[str, Any]] = field(default_factory=list)
    chart: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
