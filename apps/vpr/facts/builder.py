"""Сборка VPRReportFacts из уже рассчитанного comprehensive analysis (без повторной математики)."""

from __future__ import annotations

from typing import Any

from apps.vpr.facts.report_facts import (
    ComparisonFact,
    DeficitSummaryFact,
    GroupFact,
    MarksFact,
    PlannedSummaryFact,
    ProfileFact,
    ScoresFact,
    TaskSummaryFact,
    VPRReportFacts,
)
from apps.vpr.facts.task_classification import classify_tasks
from apps.vpr.fioko_2026.sample import GROUP_SAMPLE_MIN, group_sample_flags


def build_vpr_report_facts(analysis: Any) -> VPRReportFacts:
    summary = getattr(analysis, "summary", None)
    analytics = getattr(analysis, "analytics", None)
    n = int(getattr(summary, "participants_count", None) or 0)
    if not n and analytics is not None:
        n = int(getattr(getattr(analytics, "summary", None), "participants_count", 0) or 0)

    groups = _groups(analysis, n)
    marks = _marks(analysis, analytics)
    comparison = _comparison(analysis, analytics)
    scores = _scores(summary)
    task_results, task_summary = _tasks(analysis)
    planned = _planned(analysis)
    deficits = _deficits(analysis)
    profile = _profile(analysis)

    return VPRReportFacts(
        participants=n,
        groups=groups,
        marks=marks,
        comparison=comparison,
        scores=scores,
        tasks=task_summary,
        task_results=task_results,
        planned_results=planned,
        deficits=deficits,
        profile=profile,
        methodology={
            "exclusive_groups": ["risk", "medium", "high"],
            "overlapping_groups": ["positive_potential"],
            "stable_alias": "medium",
            "sample_min": GROUP_SAMPLE_MIN,
        },
        evidence={
            "limited_sample_groups": [
                k for k, g in groups.items() if g.evidence_status == "LIMITED_SAMPLE"
            ]
        },
        recommendations={},
    )


def _groups(analysis, n: int) -> dict[str, GroupFact]:
    profile = getattr(analysis, "participant_groups", None)
    raw = getattr(profile, "groups", None) or {}
    out: dict[str, GroupFact] = {}
    for key in ("high", "medium", "risk"):
        bucket = raw.get(key)
        count = int(getattr(bucket, "count", 0) or 0) if bucket is not None else 0
        flags = group_sample_flags(count)
        informative = bool(getattr(bucket, "informative", flags["informative"])) if bucket else flags["informative"]
        pct = float(getattr(bucket, "percent", 0) or 0) if bucket is not None else 0.0
        if bucket is None and n:
            pct = round(100.0 * count / n, 1)
        out[key] = GroupFact(
            count=count,
            percent=pct,
            group_type="EXCLUSIVE",
            classification_origin=str(
                getattr(bucket, "classification_origin", "SYSTEM_ANALYTICS") if bucket else "SYSTEM_ANALYTICS"
            ),
            evidence_status=str(
                getattr(bucket, "evidence_status", flags["sample_status"]) if bucket else flags["sample_status"]
            ),
            allow_management_conclusion=bool(
                getattr(bucket, "allow_management_conclusion", informative) if bucket else informative
            ),
            sample_size=count,
        )
    # alias required by TZ
    out["stable"] = out["medium"]

    pot_codes = list(getattr(profile, "positive_potential_codes", None) or []) if profile else []
    pot_n = len(pot_codes)
    pot_flags = group_sample_flags(pot_n)
    out["positive_potential"] = GroupFact(
        count=pot_n,
        percent=round(100.0 * pot_n / n, 1) if n else 0.0,
        group_type="OVERLAPPING",
        classification_origin="SYSTEM_ANALYTICS",
        evidence_status=str(pot_flags["sample_status"]),
        allow_management_conclusion=bool(pot_flags["informative"]),
        sample_size=pot_n,
    )
    incomplete = list(getattr(profile, "incomplete_participant_codes", None) or []) if profile else []
    if incomplete:
        out["other"] = GroupFact(
            count=len(incomplete),
            percent=round(100.0 * len(incomplete) / n, 1) if n else 0.0,
            group_type="OVERLAPPING",
            classification_origin="SYSTEM_ANALYTICS",
            evidence_status="INFORMATIVE",
            allow_management_conclusion=False,
            sample_size=len(incomplete),
        )
    return out


def _marks(analysis, analytics) -> MarksFact:
    marks_obj = getattr(analysis, "marks", None)
    if marks_obj is None and analytics is not None:
        marks_obj = getattr(analytics, "marks", None)
    return MarksFact(
        vpr=dict(getattr(marks_obj, "vpr", None) or {}),
        journal=dict(getattr(marks_obj, "journal", None) or {}),
        vpr_percents=dict(getattr(marks_obj, "vpr_percents", None) or {}),
        journal_percents=dict(getattr(marks_obj, "journal_percents", None) or {}),
    )


def _comparison(analysis, analytics) -> ComparisonFact:
    obj = getattr(analysis, "objectivity", None)
    compared = int(getattr(obj, "compared_count", 0) or 0) if obj is not None else 0
    jc = dict(getattr(obj, "journal_comparison", None) or {}) if obj is not None else {}
    jp = dict(getattr(obj, "journal_comparison_percents", None) or {}) if obj is not None else {}
    equal = int(jc.get("equal", 0) or 0)
    lower = int(jc.get("lower", 0) or 0)
    higher = int(jc.get("higher", 0) or 0)
    gap = 0
    students = []
    if analytics is not None:
        students = list(getattr(analytics, "students", None) or [])
    if not students:
        students = list(getattr(analysis, "students", None) or [])
    for st in students:
        vpr = getattr(st, "mark_vpr", None)
        journal = getattr(st, "mark_journal", None)
        if vpr is None or journal is None:
            continue
        if abs(int(journal) - int(vpr)) >= 2:
            gap += 1
    status = "INFORMATIVE" if compared else "NOT_AVAILABLE"
    return ComparisonFact(
        equal=equal,
        vpr_lower_than_journal=lower,
        vpr_higher_than_journal=higher,
        gap_ge_2=gap,
        compared=compared,
        equal_percent=jp.get("equal") if compared else None,
        lower_percent=jp.get("lower") if compared else None,
        higher_percent=jp.get("higher") if compared else None,
        status=status,
    )


def _scores(summary) -> ScoresFact:
    if summary is None:
        return ScoresFact()
    return ScoresFact(
        min=getattr(summary, "min_primary_score", None),
        max=getattr(summary, "max_primary_result", None),
        mean=getattr(summary, "avg_primary_score", None),
        median=getattr(summary, "median_primary_score", None),
        stdev=getattr(summary, "stdev_primary_score", None),
        cv=getattr(summary, "cv_primary_score_percent", None),
    )


def _tasks(analysis) -> tuple[list, TaskSummaryFact]:
    analytics = getattr(analysis, "analytics", None)
    tasks = list(getattr(analytics, "tasks", None) or []) if analytics is not None else []
    if not tasks:
        tasks = list(getattr(analysis, "tasks", None) or [])
        # VprTaskAnalysisProfile.items
        if hasattr(tasks, "items"):
            tasks = list(getattr(tasks, "items", None) or [])
    deficits = getattr(analysis, "deficits", None)
    by_code = {item.task_code: item for item in (getattr(deficits, "tasks", None) or [])}
    results = classify_tasks(tasks, deficits_by_code=by_code)
    summary = TaskSummaryFact(
        total=len(results),
        below_50=sum(1 for r in results if r.below_50),
        below_40=sum(1 for r in results if r.below_40),
        critical=sum(1 for r in results if r.is_critical),
        problem=sum(1 for r in results if r.is_problem),
        informative=sum(1 for r in results if r.is_informative),
        not_available=sum(1 for r in results if r.classification == "NOT_AVAILABLE"),
    )
    return results, summary


def _planned(analysis) -> PlannedSummaryFact:
    layer = getattr(analysis, "fioko_2026", None)
    rows = list(getattr(layer, "planned_results", None) or []) if layer is not None else []
    if not rows:
        return PlannedSummaryFact()
    not_achieved = partial = achieved = 0
    for r in rows:
        st = str(getattr(r, "status", None) or getattr(r, "fioko_status", None) or "")
        if st in {"not_achieved", "insufficient", "NOT_ACHIEVED"}:
            not_achieved += 1
        elif st in {"partial", "PARTIAL", "uncertainty"}:
            partial += 1
        elif st in {"achieved", "sufficient", "ACHIEVED"}:
            achieved += 1
    return PlannedSummaryFact(
        total=len(rows),
        not_achieved=not_achieved,
        partial=partial,
        achieved=achieved,
    )


def _deficits(analysis) -> DeficitSummaryFact:
    deficits = getattr(analysis, "deficits", None)
    summary = getattr(deficits, "summary", None) if deficits is not None else None
    return DeficitSummaryFact(
        topics_at_risk=int(getattr(summary, "topics_at_risk", 0) or 0) if summary else 0,
        skills_at_risk=int(getattr(summary, "skills_at_risk", 0) or 0) if summary else 0,
    )


def _profile(analysis) -> ProfileFact:
    school = getattr(analysis, "school_profile", None)
    code = str(getattr(school, "classification", None) or "")
    return ProfileFact(
        code=code,
        label=code,
        classification_origin="SYSTEM_ANALYTICS",
        evidence_status="INFORMATIVE",
        methodology_note=(
            "Автоматически рассчитанный внутренний аналитический профиль, "
            "не официальная классификация ФИОКО."
        ),
    )
