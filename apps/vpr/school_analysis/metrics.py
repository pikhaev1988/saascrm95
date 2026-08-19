"""Вспомогательные извлечения метрик из VprComprehensiveAnalysisResult."""

from __future__ import annotations

from typing import Any


PLACEHOLDER_TOPICS = frozenset({"", "Без темы в справочнике"})
PLACEHOLDER_SKILLS = frozenset({"", "Без умения в справочнике"})


def safe_mean(values: list[float | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


def weighted_mean(pairs: list[tuple[float | None, int]]) -> float | None:
    """Среднее с весом (например, по числу участников протокола)."""
    nums = [(float(value), int(weight)) for value, weight in pairs if value is not None and weight > 0]
    if not nums:
        return None
    total_weight = sum(weight for _, weight in nums)
    if total_weight <= 0:
        return None
    return round(sum(value * weight for value, weight in nums) / total_weight, 2)


def unique_participants_count(protocols) -> int:
    """Уникальные коды участников по всем протоколам школы за год."""
    codes: set[str] = set()
    for protocol in protocols:
        student_results = getattr(protocol, "student_results", None)
        if student_results is None:
            continue
        if hasattr(student_results, "values_list"):
            rows = student_results.values_list("participant_code", flat=True)
        else:
            rows = [
                getattr(row, "participant_code", None)
                for row in student_results
            ]
        for code in rows:
            text = str(code or "").strip()
            if text:
                codes.add(text)
    return len(codes)


def completion_percent(analysis) -> float | None:
    summary = getattr(analysis, "summary", None)
    if summary is None:
        return None
    avg = summary.avg_primary_score
    max_score = summary.max_primary_score
    if avg is None or not max_score:
        return None
    return round(float(avg) / float(max_score) * 100.0, 2)


def quality_percent(analysis) -> float | None:
    summary = getattr(analysis, "summary", None)
    if summary is None:
        return None
    return summary.knowledge_quality_percent


def absolute_percent(analysis) -> float | None:
    summary = getattr(analysis, "summary", None)
    if summary is None:
        return None
    return summary.absolute_achievement_percent


def participants_count(analysis) -> int:
    summary = getattr(analysis, "summary", None)
    if summary is None:
        return int(getattr(getattr(analysis, "achievement", None), "participants", 0) or 0)
    return int(summary.participants_count or 0)


def deficits_count(analysis) -> int:
    ds = getattr(analysis, "deficit_summary", None)
    if ds is not None:
        return int(ds.tasks_critical or 0) + int(ds.tasks_problem or 0)
    ta = getattr(analysis, "task_analysis", None)
    if ta is None:
        return 0
    return int(ta.critical_count or 0) + int(ta.risk_count or 0)


def risk_group_percent(analysis) -> float | None:
    groups = getattr(analysis, "participant_groups", None)
    if groups is None:
        return None
    bucket = (groups.groups or {}).get("risk")
    if bucket is None:
        return None
    return float(bucket.percent)


def subject_name(analysis) -> str:
    return (getattr(analysis, "subject", None) or analysis.protocol.subject or "").strip()


def parallel_value(analysis) -> int:
    return int(getattr(analysis, "parallel", None) or analysis.protocol.parallel)


def academic_year_value(analysis) -> int:
    return int(getattr(analysis, "academic_year", None) or analysis.protocol.academic_year)


def classify_item_risk(
    *,
    completion: float | None,
    quality: float | None,
    deficits: int,
) -> str:
    score = 0
    if completion is not None:
        if completion < 50:
            score += 2
        elif completion < 65:
            score += 1
    if quality is not None:
        if quality < 40:
            score += 2
        elif quality < 55:
            score += 1
    if deficits >= 5:
        score += 2
    elif deficits >= 2:
        score += 1
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def topic_averages(analyses: list[Any]) -> dict[str, list[float]]:
    acc: dict[str, list[float]] = {}
    for analysis in analyses:
        for item in analysis.topic_analysis.items:
            topic = (item.topic or "").strip()
            if not topic or topic in PLACEHOLDER_TOPICS:
                continue
            if item.average is None:
                continue
            acc.setdefault(topic, []).append(float(item.average))
    return acc


def skill_averages(analyses: list[Any]) -> dict[str, list[float]]:
    acc: dict[str, list[float]] = {}
    for analysis in analyses:
        for item in analysis.skill_analysis.items:
            skill = (item.skill or "").strip()
            if not skill or skill in PLACEHOLDER_SKILLS:
                continue
            if item.average is None:
                continue
            acc.setdefault(skill, []).append(float(item.average))
    return acc
