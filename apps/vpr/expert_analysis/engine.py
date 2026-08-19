"""
Rule Engine экспертной предметной аналитики ВПР (ФИОКО 2.0).

Только интерпретация готовых данных get_protocol_analysis.
Тексты формируются предметными моделями + компоновщиком (без шаблонной подстановки названия).
"""

from __future__ import annotations

from apps.vpr.conclusion.rules import (
    QUALITY_INTERPRETATION,
    SKEW_INTERPRETATION,
    SPREAD_INTERPRETATION,
    classify_mastery,
    classify_skew,
    classify_spread,
)
from apps.vpr.expert_analysis import composer
from apps.vpr.expert_analysis.cognitive import analyze_cognitive
from apps.vpr.expert_analysis.competences import (
    PLACEHOLDER_SKILLS,
    PLACEHOLDER_TOPICS,
    analyze_competences,
)
from apps.vpr.expert_analysis.patterns import analyze_patterns
from apps.vpr.expert_analysis.profiles import classify_preparation_profile
from apps.vpr.expert_analysis.result import ExpertAnalysisResult
from apps.vpr.expert_analysis.subject_models import get_subject_model


def _avg_share(summary) -> float | None:
    if summary is None or summary.avg_primary_score is None or not summary.max_primary_score:
        return None
    return float(summary.avg_primary_score) / float(summary.max_primary_score) * 100.0


def _topic_shares(analysis) -> tuple[float, float, list[str], list[str]]:
    strong: list[str] = []
    weak: list[str] = []
    total = 0
    for row in analysis.topic_rows or []:
        topic = (getattr(row, "topic", None) or "").strip()
        if topic in PLACEHOLDER_TOPICS:
            continue
        pct = getattr(row, "avg_completion_percent", None)
        if pct is None:
            continue
        total += 1
        band = classify_mastery(float(pct))
        if band in {"high", "sufficient"}:
            strong.append(topic)
        elif band in {"problem", "critical"}:
            weak.append(topic)
    if not total:
        return 0.0, 0.0, strong, weak
    return len(strong) / total, len(weak) / total, strong, weak


def _skill_lists(analysis) -> tuple[list[str], list[str]]:
    strong: list[str] = []
    weak: list[str] = []
    for row in analysis.skill_rows or []:
        skill = (getattr(row, "checked_skill", None) or "").strip()
        if skill in PLACEHOLDER_SKILLS:
            continue
        pct = getattr(row, "avg_completion_percent", None)
        if pct is None:
            continue
        band = classify_mastery(float(pct))
        if band in {"high", "sufficient"}:
            strong.append(skill)
        elif band in {"problem", "critical"}:
            weak.append(skill)
    return strong, weak


def _section_lists(analysis) -> tuple[list[str], list[str]]:
    from collections import defaultdict

    stats: dict[str, list[float]] = defaultdict(list)
    for row in analysis.task_rows or []:
        section = (row.get("program_section") or "").strip()
        pct = row.get("completion_percent")
        if section and pct is not None:
            stats[section].append(float(pct))
    strong, weak = [], []
    for section, values in stats.items():
        avg = sum(values) / len(values)
        band = classify_mastery(avg)
        if band in {"high", "sufficient"}:
            strong.append(section)
        elif band in {"problem", "critical"}:
            weak.append(section)
    return strong, weak


def _group_percents(groups) -> tuple[float, float]:
    risk_pct = high_pct = 0.0
    if not groups:
        return risk_pct, high_pct
    gmap = getattr(groups, "groups", None) or {}
    risk = gmap.get("risk")
    high = gmap.get("high")
    if risk is not None:
        risk_pct = float(getattr(risk, "percent", 0) or 0)
    if high is not None:
        high_pct = float(getattr(high, "percent", 0) or 0)
    return risk_pct, high_pct


def build_expert_analysis(analysis, protocol=None) -> ExpertAnalysisResult:
    summary = getattr(analysis, "summary", None)
    groups = getattr(analysis, "participant_groups", None)
    subject = str(
        getattr(analysis, "subject", None)
        or (getattr(protocol, "subject", None) if protocol else None)
        or "—"
    )
    parallel = getattr(analysis, "parallel", None) or (
        getattr(protocol, "parallel", None) if protocol else None
    )
    year = getattr(analysis, "academic_year", None) or (
        getattr(protocol, "academic_year", None) if protocol else None
    )

    model = get_subject_model(subject)
    competences = analyze_competences(analysis, subject)
    cognitive_code, cognitive_label, _legacy_cog, cog_meta = analyze_cognitive(analysis)
    patterns, _legacy_patterns = analyze_patterns(analysis, competences)

    strong_share, weak_share, strong_topics, weak_topics = _topic_shares(analysis)
    strong_skills, weak_skills = _skill_lists(analysis)
    strong_sections, _weak_sections = _section_lists(analysis)
    risk_pct, high_pct = _group_percents(groups)

    profile_code, profile_label, _legacy_profile = classify_preparation_profile(
        summary=summary,
        cognitive_code=cognitive_code,
        groups=groups,
        weak_topic_share=weak_share,
        strong_topic_share=strong_share,
    )

    formed = [c for c in competences if c.status == "formed"]
    weak_comp = [c for c in competences if c.status == "weak"]

    overview = composer.compose_overview(
        model=model,
        parallel=parallel,
        profile_label=profile_label,
        cognitive_label=cognitive_label,
        formed=formed,
        weak=weak_comp,
        patterns=patterns,
    )
    cognitive_analysis = composer.compose_cognitive(
        model,
        cognitive_code,
        cog_meta.get("basic_avg"),
        cog_meta.get("advanced_avg"),
        cog_meta.get("n_basic"),
        cog_meta.get("n_advanced"),
    )
    profile_explanation = composer.compose_profile(
        model=model,
        code=profile_code,
        label=profile_label,
        risk_pct=risk_pct,
        high_pct=high_pct,
        weak_share=weak_share,
        strong_share=strong_share,
    )
    structure_analysis = composer.compose_structure(model, analysis)
    competences_analysis = composer.compose_competences_analysis(model, competences)
    patterns_analysis = composer.compose_patterns_analysis(model, patterns)

    quality_band = classify_mastery(
        getattr(summary, "knowledge_quality_percent", None) if summary else None
    )
    quality_text = QUALITY_INTERPRETATION.get(quality_band or "", None)
    quality_analysis = composer.compose_quality(
        model, profile_label, cognitive_label, summary, quality_text
    )

    spread = classify_spread(
        getattr(summary, "cv_primary_score_percent", None) if summary else None
    )
    skew = classify_skew(
        getattr(summary, "avg_primary_score", None) if summary else None,
        getattr(summary, "median_primary_score", None) if summary else None,
    )
    statistics_analysis = composer.compose_statistics(
        model,
        SPREAD_INTERPRETATION.get(spread or "", ""),
        SKEW_INTERPRETATION.get(skew or "", ""),
        profile_label,
        getattr(summary, "cv_primary_score_percent", None) if summary else None,
    )

    tasks_analysis = composer.compose_tasks_analysis(
        model=model,
        analysis=analysis,
        cognitive_label=cognitive_label,
        patterns=patterns,
        weak_competences=weak_comp,
    )
    topics_analysis = composer.compose_topics_analysis(
        model, strong_topics, weak_topics, patterns
    )
    skills_analysis = composer.compose_skills_analysis(
        model, strong_skills, weak_skills, competences
    )
    deficits_analysis = composer.compose_deficits(
        model, patterns, weak_comp, profile_label
    )
    cause_chains, causes_analysis = composer.compose_causes(
        model, patterns, weak_comp, getattr(analysis, "causes", None)
    )

    strengths = composer.compose_strengths(
        model,
        strong_topics,
        strong_skills,
        [c.name for c in formed],
        strong_sections,
        profile_label,
        cognitive_label,
    )
    problems = composer.compose_problems(
        model,
        weak_topics,
        weak_skills,
        [c.name for c in weak_comp],
        patterns,
        profile_label,
    )
    final_conclusion = composer.compose_final(
        model,
        parallel,
        profile_label,
        cognitive_label,
        strengths,
        problems,
        overview,
        causes_analysis,
    )

    return ExpertAnalysisResult(
        profile_code=profile_code,
        profile_label=profile_label,
        profile_explanation=profile_explanation,
        cognitive_code=cognitive_code,
        cognitive_label=cognitive_label,
        cognitive_analysis=cognitive_analysis,
        competences=competences,
        competences_analysis=competences_analysis,
        patterns=patterns,
        patterns_analysis=patterns_analysis,
        structure_analysis=structure_analysis,
        strengths=strengths,
        problems=problems,
        cause_chains=cause_chains,
        causes_analysis=causes_analysis,
        overview=overview,
        quality_analysis=quality_analysis,
        statistics_analysis=statistics_analysis,
        tasks_analysis=tasks_analysis,
        topics_analysis=topics_analysis,
        skills_analysis=skills_analysis,
        deficits_analysis=deficits_analysis,
        final_conclusion=final_conclusion,
        subject=subject,
        parallel=parallel,
        academic_year=year,
    )
