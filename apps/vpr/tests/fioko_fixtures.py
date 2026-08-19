"""Общие фабрики для FIOKO 2026 unit-тестов (без hardcode Biology/English)."""

from __future__ import annotations

from apps.vpr.analytics.result import (
    VprAnalyticsResult,
    VprMarksDistribution,
    VprScoresDistribution,
    VprStudentAnalytics,
    VprSummaryMetrics,
    VprTaskAnalytics,
)


def make_task(
    code: str,
    *,
    completion: float,
    difficulty: str = "Базовый",
    max_score: int = 1,
    skill: str = "Умение A",
    topic: str = "Тема A",
    n: int = 20,
    full: int | None = None,
    partial: int = 0,
    zero: int | None = None,
) -> VprTaskAnalytics:
    if full is None:
        full = int(round(n * completion / 100.0))
    if zero is None:
        zero = max(0, n - full - partial)
    earned = completion / 100.0 * max_score * n
    return VprTaskAnalytics(
        task_code=code,
        task_number=code,
        position=int(code) if str(code).isdigit() else 1,
        max_score=max_score,
        avg_score=round(earned / n, 2) if n else None,
        completion_percent=completion,
        full_count=full,
        partial_count=partial,
        zero_count=zero,
        answers_count=n,
        correct_count=full,
        incorrect_count=zero,
        total_students=n,
        full_score_count=full,
        partial_score_count=partial,
        zero_score_count=zero,
        earned_points_sum=earned,
        max_points_sum=float(max_score * n),
        mean_score=round(earned / n, 2) if n else None,
        full_score_rate=round(100.0 * full / n, 2) if n else None,
        partial_score_rate=round(100.0 * partial / n, 2) if n else None,
        zero_score_rate=round(100.0 * zero / n, 2) if n else None,
        topic=topic,
        program_section="",
        checked_skill=skill,
        difficulty=difficulty,
        catalog_matched=bool(difficulty and skill),
    )


def make_student(
    code: str,
    *,
    primary: float,
    mark_vpr: int | None,
    mark_journal: int | None = None,
    completion: float = 50.0,
) -> VprStudentAnalytics:
    return VprStudentAnalytics(
        participant_code=code,
        full_name=f"Ученик {code}",
        class_group="5А",
        gender="",
        primary_score=primary,
        mark_vpr=mark_vpr,
        mark_journal=mark_journal,
        completion_percent=completion,
        avg_task_score=None,
        place_overall=None,
        place_in_class=None,
    )


def make_analytics(
    *,
    subject: str = "Математика",
    parallel: int = 5,
    year: int = 2026,
    n: int = 20,
    tasks: list[VprTaskAnalytics] | None = None,
    students: list[VprStudentAnalytics] | None = None,
) -> VprAnalyticsResult:
    if students is None:
        students = [
            make_student(
                str(i + 1),
                primary=10 + (i % 15),
                mark_vpr=2 + (i % 4),
                mark_journal=3 + (i % 3),
                completion=40 + i,
            )
            for i in range(n)
        ]
    if tasks is None:
        tasks = [
            make_task("1", completion=70, difficulty="Базовый", skill="Счёт", n=n),
            make_task("2", completion=50, difficulty="Базовый", skill="Счёт", n=n),
            make_task("3", completion=25, difficulty="Повышенный", skill="Задача", n=n),
            make_task("4", completion=35, difficulty="Повышенный", skill="Задача", n=n),
        ]
    primaries = [float(s.primary_score) for s in students if s.primary_score is not None]
    marks = {}
    for s in students:
        if s.mark_vpr is not None:
            k = str(int(s.mark_vpr))
            marks[k] = marks.get(k, 0) + 1
    total_m = sum(marks.values()) or 1
    from collections import Counter

    hist = Counter(int(p) if float(p).is_integer() else p for p in primaries)
    return VprAnalyticsResult(
        protocol_id=1001,
        subject=subject,
        parallel=parallel,
        academic_year=year,
        organization_name="ОО Тест",
        summary=VprSummaryMetrics(
            participants_count=len(students),
            max_primary_score=max(primaries) if primaries else 0,
            avg_primary_score=round(sum(primaries) / len(primaries), 2) if primaries else None,
            min_primary_score=min(primaries) if primaries else None,
            max_primary_result=max(primaries) if primaries else None,
            avg_mark_vpr=None,
            avg_mark_journal=None,
            knowledge_quality_percent=None,
            absolute_achievement_percent=None,
            median_primary_score=None,
            mode_primary_score=None,
            stdev_primary_score=None,
            cv_primary_score_percent=None,
        ),
        marks=VprMarksDistribution(
            vpr=marks,
            journal={},
            vpr_percents={k: round(100.0 * v / total_m, 2) for k, v in marks.items()},
            journal_percents={},
        ),
        scores=VprScoresDistribution(
            counts={str(k): int(v) for k, v in hist.items()},
            percents={
                str(k): round(100.0 * v / len(primaries), 2) for k, v in hist.items()
            }
            if primaries
            else {},
        ),
        tasks=tasks,
        topics=[],
        skills=[],
        students=students,
    )
