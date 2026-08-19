"""
Сборка FIOKO 2026 layer для любого протокола ВПР.

Data-driven: subject / class / year / tasks / catalog.
Не хардкодит предметы и protocol_id.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from apps.vpr.analytics.metrics import rate_percent
from apps.vpr.analytics.result import VprAnalyticsResult, VprTaskAnalytics
from apps.vpr.analytics.stats import (
    coefficient_of_variation,
    population_stdev,
    safe_mean,
    safe_median,
    to_float,
)
from apps.vpr.analytics.thresholds import VPR_THRESHOLDS
from apps.vpr.conclusion.rules import classify_mastery
from apps.vpr.fioko_2026.classification import (
    classify_fioko_level,
    classify_sample_quality,
)
from apps.vpr.fioko_2026.difficulty import (
    difficulty_label,
    normalize_difficulty,
)
from apps.vpr.fioko_2026.management import build_management_recommendations
from apps.vpr.fioko_2026.mapping import get_fioko_mapping_matrix
from apps.vpr.fioko_2026.schemas import (
    FiokoBoundaryPeakFlag,
    FiokoCrossSubjectAnalysis,
    FiokoCrossSubjectItem,
    FiokoCrossYearAnalysis,
    FiokoCrossYearItem,
    FiokoGeneralPeak,
    FiokoGroupsAnalysis,
    FiokoIndividualRow,
    FiokoJournalAnalysis,
    FiokoJournalGapRow,
    FiokoMarkGroupBucket,
    FiokoMarksStats,
    FiokoPlannedResultRow,
    FiokoPrimaryDistribution,
    FiokoSkillDeficit,
    FiokoTaskRow,
    VprFioko2026Layer,
)
from apps.vpr.fioko_2026.sample import group_sample_flags, resolve_official_mark_boundaries
from apps.vpr.fioko_2026.source import (
    FIOKO_DOCUMENT,
    methodology_basis_text,
)


def build_fioko_2026_layer(
    analytics: VprAnalyticsResult,
    *,
    protocol=None,
    previous_analytics: VprAnalyticsResult | None = None,
    peer_protocols: Iterable[Any] | None = None,
    enrich_catalog: bool = True,
) -> VprFioko2026Layer:
    """
    Построить FIOKO-слой поверх уже рассчитанной VPR analytics.

    protocol — ORM VprProtocol (опционально): нужен для индивидуальных % Б/П/В
    и поиска прошлых лет / peer-протоколов.
    """
    tasks = _build_tasks(analytics.tasks)
    if enrich_catalog:
        _enrich_planned_from_catalog(analytics, tasks)

    warnings: list[str] = []
    system_notes = [
        "Группы high/medium/risk (80/50) — SYSTEM_ANALYTICS, не требование ФИОКО 2026.",
        "CV / PreparationProfile / positive_potential — SYSTEM_ANALYTICS.",
        "classify_mastery 90/75/60/40 — SYSTEM_ANALYTICS; fioko_achievement_status — отдельно.",
    ]

    catalog_status = _catalog_mapping_status(tasks)
    difficulty_cov = _difficulty_coverage(tasks)
    if catalog_status != "COMPLETE":
        warnings.append(
            f"Каталог КИМ: catalog_mapping_status={catalog_status}. "
            "Выводы по difficulty/planned_result ограничены отсутствием mapping."
        )

    individuals = _build_individuals(analytics, protocol, tasks)
    marks = _build_marks(analytics, protocol)
    journal = _build_journal(analytics)
    distribution = _build_distribution(analytics, protocol=protocol)
    skill_deficits = _build_skill_deficits(tasks)
    planned = _build_planned_results(tasks)
    groups = _build_groups(analytics, protocol, tasks)
    cross_year = _build_cross_year(analytics, protocol, previous_analytics, tasks)
    # peer-сравнение дорого на 138 протоколах — по умолчанию лёгкий режим без рекурсивного analyze
    cross_subject = _build_cross_subject_light(analytics, protocol, peer_protocols)
    management = build_management_recommendations(
        tasks=tasks,
        skill_deficits=skill_deficits,
        journal=journal,
        distribution=distribution,
        marks=marks,
        groups=groups,
        subject=analytics.subject,
        parallel=analytics.parallel,
    )

    if distribution.sample_warning:
        warnings.append(
            f"Распределение первичных баллов: N={distribution.sample_size}, "
            f"качество выборки={distribution.sample_quality}."
        )
    if groups.sample_warning:
        warnings.append(
            f"Групповой анализ: N={groups.sample_size} < 10 — informational_only."
        )

    return VprFioko2026Layer(
        source="FIOKO_2026",
        document=dict(FIOKO_DOCUMENT),
        mapping=get_fioko_mapping_matrix(),
        catalog_mapping_status=catalog_status,
        difficulty_coverage=difficulty_cov,
        tasks=tasks,
        individuals=individuals,
        marks=marks,
        journal=journal,
        distribution=distribution,
        skill_deficits=skill_deficits,
        planned_results=planned,
        groups=groups,
        management_recommendations=management,
        cross_year=cross_year,
        cross_subject=cross_subject,
        methodology_basis=methodology_basis_text(),
        warnings=warnings,
        system_analytics_notes=system_notes,
    )


def _task_catalog_status(task: VprTaskAnalytics) -> str:
    has_diff = bool(str(task.difficulty or "").strip()) and normalize_difficulty(task.difficulty) != "unknown"
    has_skill = bool(str(task.checked_skill or "").strip())
    has_topic = bool(str(task.topic or "").strip())
    matched = bool(task.catalog_matched)
    if matched and has_diff and has_skill:
        return "COMPLETE"
    if matched or has_diff or has_skill or has_topic:
        return "PARTIAL"
    return "NOT_AVAILABLE"


def _build_tasks(raw_tasks: list[VprTaskAnalytics]) -> list[FiokoTaskRow]:
    rows: list[FiokoTaskRow] = []
    for t in raw_tasks:
        diff = normalize_difficulty(t.difficulty)
        diff_status = "ok" if diff != "unknown" else "NOT_AVAILABLE"
        cls = classify_fioko_level(t.completion_percent, diff)
        map_status = _task_catalog_status(t)
        if map_status == "NOT_AVAILABLE" and not t.catalog_matched:
            map_status = "NOT_MAPPED" if not (t.topic or t.checked_skill) else "PARTIAL"
        rows.append(
            FiokoTaskRow(
                task_code=str(t.task_code),
                task_number=str(t.task_number or t.task_code),
                difficulty=diff,
                difficulty_label=difficulty_label(diff),
                difficulty_status=diff_status,
                completion_percent=t.completion_percent,
                fioko_level_status=str(cls["fioko_level_status"]),
                visual_marker=str(cls["visual_marker"]),
                checked_skill=t.checked_skill or "",
                topic=t.topic or "",
                planned_result="",
                catalog_mapping_status=map_status,
                full_score_rate=t.full_score_rate,
                partial_score_rate=t.partial_score_rate,
                zero_score_rate=t.zero_score_rate,
                max_score=int(t.max_score or 0),
            )
        )
    return rows


def _catalog_mapping_status(tasks: list[FiokoTaskRow]) -> str:
    if not tasks:
        return "NOT_AVAILABLE"
    statuses = {t.catalog_mapping_status for t in tasks}
    if statuses == {"COMPLETE"}:
        return "COMPLETE"
    if "COMPLETE" in statuses or "PARTIAL" in statuses:
        return "PARTIAL"
    return "NOT_AVAILABLE"


def _difficulty_coverage(tasks: list[FiokoTaskRow]) -> dict[str, Any]:
    counts = {"basic": 0, "advanced": 0, "high": 0, "unknown": 0}
    for t in tasks:
        counts[t.difficulty] = counts.get(t.difficulty, 0) + 1
    mapped = sum(counts[k] for k in ("basic", "advanced", "high"))
    total = len(tasks)
    return {
        "counts": counts,
        "mapped_tasks": mapped,
        "total_tasks": total,
        "mapped_share": round(100.0 * mapped / total, 2) if total else None,
        "has_basic": counts["basic"] > 0,
        "has_advanced": counts["advanced"] > 0,
        "has_high": counts["high"] > 0,
    }


def _completion_by_difficulty(
    earned: dict[str, float],
    maximum: dict[str, float],
    code: str,
) -> tuple[float | None, str]:
    mx = maximum.get(code, 0.0)
    if mx <= 0:
        return None, "not_available"
    calc = rate_percent(
        earned.get(code, 0.0),
        mx,
        formula_type=f"earned_{code}/max_{code}*100",
        source_metric=f"{code}_completion_percent",
    )
    cls = classify_fioko_level(calc.value, code)  # type: ignore[arg-type]
    return calc.value, str(cls["fioko_level_status"])


def _build_individuals(
    analytics: VprAnalyticsResult,
    protocol,
    tasks: list[FiokoTaskRow],
) -> list[FiokoIndividualRow]:
    diff_by_code = {t.task_code: t.difficulty for t in tasks}
    max_by_code = {t.task_code: t.max_score for t in tasks}
    score_maps: dict[str, dict[str, float | None]] = {}

    if protocol is not None:
        try:
            students = list(
                protocol.student_results.prefetch_related("task_scores__task").all()
            )
        except Exception:
            students = []
        for st in students:
            m: dict[str, float | None] = {}
            for ts in st.task_scores.all():
                code = str(getattr(ts.task, "code", "") or "")
                if not code:
                    continue
                m[code] = to_float(ts.score)
            score_maps[str(st.participant_code)] = m

    rows: list[FiokoIndividualRow] = []
    for st in analytics.students:
        code = str(st.participant_code)
        task_scores = score_maps.get(code, {})
        earned = {"basic": 0.0, "advanced": 0.0, "high": 0.0}
        maximum = {"basic": 0.0, "advanced": 0.0, "high": 0.0}
        for tcode, score in task_scores.items():
            diff = diff_by_code.get(tcode, "unknown")
            if diff == "unknown":
                continue
            mx = float(max_by_code.get(tcode) or 0)
            if mx <= 0:
                continue
            maximum[diff] += mx
            earned[diff] += float(score or 0.0)

        b_pct, b_st = _completion_by_difficulty(earned, maximum, "basic")
        a_pct, a_st = _completion_by_difficulty(earned, maximum, "advanced")
        h_pct, h_st = _completion_by_difficulty(earned, maximum, "high")

        coverage = {
            "basic": maximum["basic"] > 0,
            "advanced": maximum["advanced"] > 0,
            "high": maximum["high"] > 0,
        }
        if not task_scores:
            b_pct = a_pct = h_pct = None
            b_st = a_st = h_st = "not_available"
            coverage = {"basic": False, "advanced": False, "high": False}

        rows.append(
            FiokoIndividualRow(
                participant_code=code,
                full_name=st.full_name or "",
                primary_score=st.primary_score,
                mark_vpr=st.mark_vpr,
                mark_journal=st.mark_journal,
                task_scores=task_scores,
                basic_completion_percent=b_pct,
                advanced_completion_percent=a_pct,
                high_completion_percent=h_pct,
                basic_status=b_st,
                advanced_status=a_st,
                high_status=h_st,
                difficulty_coverage=coverage,
            )
        )
    return rows


def _mark_percent(counts: dict[str, int], mark: str, total: int) -> float | None:
    if total <= 0:
        return None
    return round(100.0 * int(counts.get(mark, 0)) / total, 2)


def _build_marks(analytics: VprAnalyticsResult, protocol) -> FiokoMarksStats:
    vpr = analytics.marks.vpr or {}
    total = sum(int(v) for v in vpr.values())
    cur2 = _mark_percent(vpr, "2", total)

    prev2 = None
    dynamics = None
    dyn_status = "NOT_AVAILABLE"
    trend: list[dict[str, Any]] = []

    if protocol is not None:
        try:
            from apps.vpr.models import VprProtocol

            peers = list(
                VprProtocol.objects.filter(
                    subject=protocol.subject,
                    parallel=protocol.parallel,
                    organization_code=protocol.organization_code or "",
                )
                .exclude(pk=protocol.pk)
                .order_by("academic_year")
            )
            for p in peers:
                marks = [
                    int(s.mark_vpr)
                    for s in p.student_results.all()
                    if s.mark_vpr is not None
                ]
                if not marks:
                    continue
                share2 = round(100.0 * sum(1 for m in marks if m == 2) / len(marks), 2)
                trend.append(
                    {"year": int(p.academic_year), "mark_2_percent": share2, "protocol_id": p.pk}
                )
            prev_year = int(protocol.academic_year) - 1
            prev_entry = next((t for t in reversed(trend) if t["year"] == prev_year), None)
            if prev_entry is None and trend:
                older = [t for t in trend if t["year"] < int(protocol.academic_year)]
                prev_entry = older[-1] if older else None
            if prev_entry is not None and cur2 is not None:
                prev2 = float(prev_entry["mark_2_percent"])
                dynamics = round(cur2 - prev2, 2)
                neg_pp = float(
                    (VPR_THRESHOLDS.get("fioko_2026") or {}).get("mark2_negative_dynamics_pp") or 10
                )
                if dynamics <= 0:
                    dyn_status = "positive"
                elif dynamics >= neg_pp:
                    dyn_status = "negative"
                else:
                    dyn_status = "neutral"
        except Exception:
            pass

    if cur2 is not None and protocol is not None:
        trend.append(
            {
                "year": int(getattr(protocol, "academic_year", analytics.academic_year)),
                "mark_2_percent": cur2,
                "protocol_id": int(getattr(protocol, "pk", analytics.protocol_id) or 0),
            }
        )
        trend.sort(key=lambda x: x["year"])

    return FiokoMarksStats(
        mark_2_percent=cur2,
        mark_3_percent=_mark_percent(vpr, "3", total),
        mark_4_percent=_mark_percent(vpr, "4", total),
        mark_5_percent=_mark_percent(vpr, "5", total),
        previous_year_mark_2_percent=prev2,
        mark_2_dynamics_pp=dynamics,
        mark_2_dynamics_status=dyn_status,
        mark_2_trend=trend,
        sample_size=total,
    )


def _build_journal(analytics: VprAnalyticsResult) -> FiokoJournalAnalysis:
    gap_min = int((VPR_THRESHOLDS.get("fioko_2026") or {}).get("journal_gap_abs_min") or 2)
    rows: list[FiokoJournalGapRow] = []
    for st in analytics.students:
        if st.mark_vpr is None or st.mark_journal is None:
            continue
        vpr = int(st.mark_vpr)
        journal = int(st.mark_journal)
        gap = abs(vpr - journal)
        if vpr < journal:
            direction = "vpr_lower"
        elif vpr > journal:
            direction = "vpr_higher"
        else:
            direction = "equal"
        rows.append(
            FiokoJournalGapRow(
                participant_code=str(st.participant_code),
                mark_vpr=vpr,
                mark_journal=journal,
                journal_gap_abs=gap,
                journal_gap_direction=direction,
                journal_gap_ge_2=gap >= gap_min,
            )
        )

    if not rows:
        return FiokoJournalAnalysis(
            status="NOT_AVAILABLE",
            wording="Данные отметок по журналу отсутствуют (NOT_AVAILABLE).",
            sample_size=0,
        )

    ge2 = [r for r in rows if r.journal_gap_ge_2]
    pct = round(100.0 * len(ge2) / len(rows), 2) if rows else None
    wording = (
        "Выявлено существенное расхождение (2 и более балла), "
        "требующее дополнительного анализа."
        if ge2
        else "Существенных расхождений (≥2 балла) не выявлено."
    )
    return FiokoJournalAnalysis(
        status="OK",
        compared_count=len(rows),
        gap_ge_2_count=len(ge2),
        gap_ge_2_percent=pct,
        rows=ge2,
        wording=wording,
        sample_size=len(rows),
    )


def _infer_mark_boundaries(analytics: VprAnalyticsResult) -> dict[str, float | None]:
    """
    Диагностический вывод min(primary|mark) — НЕ официальные границы.
    Stage 7.1: не использовать для BOUNDARY_PEAK / objectivity marker.
    """
    by_mark: dict[int, list[float]] = defaultdict(list)
    for st in analytics.students:
        if st.mark_vpr is None or st.primary_score is None:
            continue
        by_mark[int(st.mark_vpr)].append(float(st.primary_score))

    def _min_for(mark: int) -> float | None:
        vals = by_mark.get(mark) or []
        return min(vals) if vals else None

    return {
        "2->3": _min_for(3),
        "3->4": _min_for(4),
        "4->5": _min_for(5),
    }


def _detect_general_peak(hist: dict[str, int], total: int) -> FiokoGeneralPeak:
    if not hist or total <= 0:
        return FiokoGeneralPeak(is_peak=False, note="Недостаточно данных для general peak.")
    best_key = max(hist.keys(), key=lambda k: int(hist[k]))
    count = int(hist[best_key])
    pct = round(100.0 * count / total, 2)
    avg = sum(int(v) for v in hist.values()) / max(len(hist), 1)
    is_peak = count >= max(2, avg * 1.5) and count >= avg + 1
    try:
        score = float(best_key)
    except (TypeError, ValueError):
        score = None
    return FiokoGeneralPeak(
        primary_score=score,
        observed_count=count,
        percent=pct,
        is_peak=is_peak,
        note=(
            "Статистическая особенность распределения (GENERAL_PEAK); "
            "сама по себе не является маркером нарушения объективности."
            if is_peak
            else "Выраженный general peak не выделен."
        ),
    )


def _build_distribution(
    analytics: VprAnalyticsResult,
    *,
    protocol=None,
) -> FiokoPrimaryDistribution:
    scores = [
        float(st.primary_score)
        for st in analytics.students
        if st.primary_score is not None
    ]
    sample = classify_sample_quality(len(scores), context="distribution")
    hist = dict(analytics.scores.counts or {})
    if not hist and scores:
        from collections import Counter

        hist = {
            str(int(k) if float(k).is_integer() else k): v for k, v in Counter(scores).items()
        }

    mean = safe_mean(scores)
    median = safe_median(scores)
    stdev = population_stdev(scores)
    cv = coefficient_of_variation(scores)
    general_peak = _detect_general_peak(hist, len(scores))

    # Stage 7.1: только официальные границы; inferred — не для objectivity
    official = resolve_official_mark_boundaries(
        subject=analytics.subject,
        parallel=analytics.parallel,
        academic_year=analytics.academic_year,
        protocol=protocol,
    )
    flags: list[FiokoBoundaryPeakFlag] = []
    possible_marker = False
    boundary_peak_status = "NOT_AVAILABLE"
    boundary_source = "NOT_AVAILABLE"

    if not official:
        for b in ("2->3", "3->4", "4->5"):
            flags.append(
                FiokoBoundaryPeakFlag(
                    boundary=b,
                    primary_score=None,
                    observed_count=0,
                    expected_context=(
                        "Официальные границы перевода первичных баллов в отметки "
                        "для subject/class/year недоступны. Оценка BOUNDARY_PEAK не выполняется "
                        "(не угадываем границы)."
                    ),
                    status="NOT_AVAILABLE",
                )
            )
        wording = (
            "Оценка пиков на границах перехода отметок не выполнена: "
            "отсутствуют необходимые данные о границах перевода первичных баллов."
        )
        if general_peak.is_peak:
            wording += (
                f" Выявлен GENERAL_PEAK на балле {general_peak.primary_score} "
                f"({general_peak.percent}%); это статистическая особенность, "
                "не автоматический маркер нарушения объективности."
            )
    else:
        boundary_source = "official"
        counts_list = [int(v) for v in hist.values()] or [0]
        avg_count = sum(counts_list) / max(len(counts_list), 1)
        for boundary, score in official.items():
            key_candidates = [
                str(score),
                str(int(score)) if float(score).is_integer() else str(score),
            ]
            observed = 0
            for k in key_candidates:
                if k in hist:
                    observed = int(hist[k])
                    break
            is_peak = observed >= max(2, avg_count * 1.5) and observed >= avg_count + 1
            status = "POSSIBLE_MARKER" if is_peak else "ok"
            if is_peak:
                possible_marker = True
            flags.append(
                FiokoBoundaryPeakFlag(
                    boundary=boundary,
                    primary_score=float(score),
                    observed_count=observed,
                    expected_context=(
                        f"Официальная граница {boundary}={score} "
                        f"(subject/class/year); avg_bin={avg_count:.1f}."
                    ),
                    status=status,
                )
            )
        boundary_peak_status = "HAS_MARKER" if possible_marker else "OK"
        if possible_marker:
            wording = (
                "Наличие выраженных пиков на границах перехода отметок может рассматриваться "
                "как один из возможных маркеров нарушения объективности и требует "
                "дополнительного анализа."
            )
        else:
            wording = "Выраженных пиков на границах перехода отметок не выявлено."

    sample_note = sample.get("wording") or ""
    if sample_note:
        wording = f"{sample_note} {wording}".strip()

    return FiokoPrimaryDistribution(
        min=min(scores) if scores else None,
        max=max(scores) if scores else None,
        mean=mean,
        median=median,
        stdev=stdev,
        cv=cv,
        histogram={str(k): int(v) for k, v in hist.items()},
        general_peak=general_peak,
        boundary_peak_flags=flags,
        boundary_peak_status=boundary_peak_status,
        possible_objectivity_marker=possible_marker,
        boundary_source=boundary_source,
        sample_size=int(sample["sample_size"]),
        sample_quality=str(sample["sample_quality"]),
        sample_warning=bool(sample["sample_warning"]),
        wording=wording,
    )


def _build_skill_deficits(tasks: list[FiokoTaskRow]) -> list[FiokoSkillDeficit]:
    by_skill: dict[str, list[FiokoTaskRow]] = defaultdict(list)
    for t in tasks:
        skill = (t.checked_skill or "").strip()
        if not skill:
            continue
        by_skill[skill].append(t)

    out: list[FiokoSkillDeficit] = []
    for skill, linked in by_skill.items():
        red = [t.task_code for t in linked if t.fioko_level_status == "insufficient"]
        yellow = [t.task_code for t in linked if t.fioko_level_status == "uncertainty"]
        green = [t.task_code for t in linked if t.fioko_level_status == "sufficient"]
        n = len(linked)
        if n < 2:
            out.append(
                FiokoSkillDeficit(
                    skill=skill,
                    linked_tasks=[t.task_code for t in linked],
                    red_tasks=red,
                    yellow_tasks=yellow,
                    green_tasks=green,
                    red_share=round(100.0 * len(red) / n, 2) if n else None,
                    system_deficit=False,
                    status="INSUFFICIENT_DATA",
                )
            )
            continue
        red_share = round(100.0 * len(red) / n, 2)
        system = len(red) > (n / 2.0)
        out.append(
            FiokoSkillDeficit(
                skill=skill,
                linked_tasks=[t.task_code for t in linked],
                red_tasks=red,
                yellow_tasks=yellow,
                green_tasks=green,
                red_share=red_share,
                system_deficit=system,
                status="OK",
            )
        )
    return out


def _enrich_planned_from_catalog(analytics: VprAnalyticsResult, tasks: list[FiokoTaskRow]) -> None:
    try:
        from apps.vpr.services.catalog_lookup import lookup_task_catalog
    except Exception:
        return
    for t in tasks:
        if t.planned_result:
            continue
        info = lookup_task_catalog(
            subject=analytics.subject,
            parallel=analytics.parallel,
            academic_year=analytics.academic_year,
            task_code=t.task_code,
        )
        if info is None:
            continue
        pr = getattr(info, "fgos_result", "") or ""
        if pr:
            t.planned_result = str(pr)


def _build_planned_results(tasks: list[FiokoTaskRow]) -> list[FiokoPlannedResultRow]:
    by_key: dict[str, list[FiokoTaskRow]] = defaultdict(list)
    for t in tasks:
        key = (t.planned_result or t.checked_skill or t.topic or "").strip()
        if not key:
            continue
        by_key[key].append(t)

    rows: list[FiokoPlannedResultRow] = []
    for key, linked in by_key.items():
        comps = [float(t.completion_percent) for t in linked if t.completion_percent is not None]
        avg = round(sum(comps) / len(comps), 2) if comps else None
        diffs = {t.difficulty for t in linked if t.difficulty != "unknown"}
        if diffs == {"basic"}:
            diff = "basic"
        elif diffs and diffs.issubset({"advanced", "high"}):
            diff = "advanced"
        elif "basic" in diffs:
            diff = "basic"
        elif diffs:
            diff = next(iter(diffs))
        else:
            diff = "unknown"
        cls = classify_fioko_level(avg, diff)  # type: ignore[arg-type]
        system_status = ""
        if avg is not None:
            try:
                system_status = classify_mastery(avg)
            except Exception:
                system_status = ""
        rows.append(
            FiokoPlannedResultRow(
                planned_result=key,
                linked_tasks=[t.task_code for t in linked],
                difficulties=sorted(diffs) if diffs else ["unknown"],
                completion_percent=avg,
                fioko_achievement_status=str(cls["fioko_level_status"]),
                visual_marker=str(cls["visual_marker"]),
                evidence=f"avg(completion) по заданиям {', '.join(t.task_code for t in linked)}",
                system_mastery_status=system_status,
            )
        )
    return rows


def _build_groups(
    analytics: VprAnalyticsResult,
    protocol,
    tasks: list[FiokoTaskRow],
) -> FiokoGroupsAnalysis:
    n = int(analytics.summary.participants_count or len(analytics.students) or 0)
    sample = classify_sample_quality(n, context="groups")

    by_mark: dict[str, list] = defaultdict(list)
    for st in analytics.students:
        if st.mark_vpr is None:
            continue
        by_mark[str(int(st.mark_vpr))].append(st)

    score_by_participant: dict[str, dict[str, float | None]] = {}
    if protocol is not None:
        try:
            for st in protocol.student_results.prefetch_related("task_scores__task").all():
                m = {}
                for ts in st.task_scores.all():
                    code = str(getattr(ts.task, "code", "") or "")
                    if code:
                        m[code] = to_float(ts.score)
                score_by_participant[str(st.participant_code)] = m
        except Exception:
            pass

    max_by_code = {t.task_code: max(t.max_score, 1) for t in tasks}
    buckets: list[FiokoMarkGroupBucket] = []
    group_task_pct: dict[str, dict[str, float | None]] = {}

    for mark in sorted(by_mark.keys()):
        members = by_mark[mark]
        size = len(members)
        gflags = group_sample_flags(size)
        # protocol-level sample also applies
        limited = (not gflags["informative"]) or bool(sample["informational_only"])
        task_completion: dict[str, float | None] = {}
        for t in tasks:
            earned = 0.0
            mx_sum = 0.0
            for st in members:
                sc = score_by_participant.get(str(st.participant_code), {}).get(t.task_code)
                if sc is None and not score_by_participant:
                    continue
                mx_sum += float(max_by_code.get(t.task_code) or 1)
                earned += float(sc or 0.0)
            if mx_sum <= 0:
                task_completion[t.task_code] = None
            else:
                task_completion[t.task_code] = round(100.0 * earned / mx_sum, 2)
        group_task_pct[mark] = task_completion
        vals = [(code, pct) for code, pct in task_completion.items() if pct is not None]
        weak = [c for c, p in sorted(vals, key=lambda x: x[1])[:3]]
        strong = [c for c, p in sorted(vals, key=lambda x: x[1], reverse=True)[:3]]
        buckets.append(
            FiokoMarkGroupBucket(
                mark=mark,
                group_size=size,
                informational_only=limited,
                sample_warning=limited,
                sample_status=str(gflags["sample_status"]),
                informative=bool(gflags["informative"]) and not bool(sample["informational_only"]),
                task_completion=task_completion,
                weak_tasks=weak,
                strong_tasks=strong,
            )
        )

    hard_for_all: list[str] = []
    easiest: list[str] = []
    if group_task_pct and tasks:
        for t in tasks:
            pcts = [
                group_task_pct[m].get(t.task_code)
                for m in group_task_pct
                if group_task_pct[m].get(t.task_code) is not None
            ]
            if pcts and all(p is not None and p < 40 for p in pcts):
                hard_for_all.append(t.task_code)
            if pcts and all(p is not None and p >= 80 for p in pcts):
                easiest.append(t.task_code)

    anomalies: list[dict[str, Any]] = []
    marks_sorted = sorted(group_task_pct.keys(), key=lambda x: int(x))
    size_by_mark = {b.mark: b.group_size for b in buckets}
    informative_by_mark = {b.mark: b.informative for b in buckets}
    for i, m_low in enumerate(marks_sorted):
        for m_high in marks_sorted[i + 1 :]:
            # Stage 7.1: не используем LIMITED_SAMPLE как основание FIOKO-вывода
            if not informative_by_mark.get(m_low) or not informative_by_mark.get(m_high):
                continue
            for t in tasks:
                p_low = group_task_pct[m_low].get(t.task_code)
                p_high = group_task_pct[m_high].get(t.task_code)
                if p_low is None or p_high is None:
                    continue
                if p_low > p_high + 5:
                    anomalies.append(
                        {
                            "task_code": t.task_code,
                            "lower_mark": m_low,
                            "higher_mark": m_high,
                            "lower_pct": p_low,
                            "higher_pct": p_high,
                            "lower_n": size_by_mark.get(m_low),
                            "higher_n": size_by_mark.get(m_high),
                        }
                    )

    wording = ""
    if anomalies:
        wording = (
            "Ситуация требует детального изучения для выявления истинных причин результатов."
        )

    return FiokoGroupsAnalysis(
        sample_size=n,
        sample_warning=bool(sample["sample_warning"]),
        informational_only=bool(sample["informational_only"]),
        buckets=buckets,
        hard_for_all=hard_for_all,
        easiest=easiest,
        anomaly_crossings=anomalies,
        anomaly_wording=wording,
    )


def _build_cross_year(
    analytics: VprAnalyticsResult,
    protocol,
    previous_analytics: VprAnalyticsResult | None,
    tasks: list[FiokoTaskRow],
) -> FiokoCrossYearAnalysis:
    prev = previous_analytics
    prev_id = None
    prev_year = None

    if prev is None and protocol is not None:
        try:
            from apps.vpr.analytics import VprAnalyticsEngine
            from apps.vpr.models import VprProtocol

            candidate = (
                VprProtocol.objects.filter(
                    subject=protocol.subject,
                    parallel=protocol.parallel,
                    organization_code=protocol.organization_code or "",
                    academic_year__lt=int(protocol.academic_year),
                )
                .order_by("-academic_year")
                .first()
            )
            if candidate is not None:
                prev = VprAnalyticsEngine().analyze(candidate)
                prev_id = candidate.pk
                prev_year = int(candidate.academic_year)
        except Exception:
            prev = None

    if prev is None:
        return FiokoCrossYearAnalysis(
            status="NOT_AVAILABLE",
            note="Протокол предыдущего года не найден.",
        )

    cur_skills = {t.checked_skill for t in tasks if t.checked_skill}
    prev_tasks = list(prev.tasks or [])
    prev_skills = {t.checked_skill for t in prev_tasks if t.checked_skill}
    overlap = cur_skills & prev_skills
    if not overlap:
        return FiokoCrossYearAnalysis(
            status="NOT_COMPARABLE",
            previous_protocol_id=prev_id or getattr(prev, "protocol_id", None),
            previous_year=prev_year or getattr(prev, "academic_year", None),
            note="Нет пересечения проверяемых умений по кодификатору — сравнение недопустимо.",
        )

    prev_by_skill: dict[str, list[float]] = defaultdict(list)
    for t in prev_tasks:
        if t.checked_skill and t.completion_percent is not None:
            prev_by_skill[t.checked_skill].append(float(t.completion_percent))
    cur_by_skill: dict[str, list[float]] = defaultdict(list)
    for t in tasks:
        if t.checked_skill and t.completion_percent is not None:
            cur_by_skill[t.checked_skill].append(float(t.completion_percent))

    items: list[FiokoCrossYearItem] = []
    for skill in sorted(overlap):
        c_vals = cur_by_skill.get(skill) or []
        p_vals = prev_by_skill.get(skill) or []
        c_avg = round(sum(c_vals) / len(c_vals), 2) if c_vals else None
        p_avg = round(sum(p_vals) / len(p_vals), 2) if p_vals else None
        delta = round(c_avg - p_avg, 2) if c_avg is not None and p_avg is not None else None
        items.append(
            FiokoCrossYearItem(
                skill_or_topic=skill,
                kind="skill",
                current_completion=c_avg,
                previous_completion=p_avg,
                delta_completion_pp=delta,
                comparison_status="OK",
            )
        )

    return FiokoCrossYearAnalysis(
        status="OK",
        previous_protocol_id=prev_id or getattr(prev, "protocol_id", None),
        previous_year=prev_year or getattr(prev, "academic_year", None),
        items=items,
        note="Сравнение только по пересекающимся умениям (сопоставимость по кодификатору).",
    )


def _build_cross_subject_light(
    analytics: VprAnalyticsResult,
    protocol,
    peer_protocols: Iterable[Any] | None,
) -> FiokoCrossSubjectAnalysis:
    """
    Лёгкий слой: метаданные peer-протоколов без полного re-analyze всех предметов.
    Полный task-level cross-subject — при явной передаче peer_protocols + deep mode.
    """
    peers = list(peer_protocols or [])
    if not peers and protocol is not None:
        try:
            from apps.vpr.models import VprProtocol

            peers = list(
                VprProtocol.objects.filter(
                    parallel=protocol.parallel,
                    academic_year=protocol.academic_year,
                    organization_code=protocol.organization_code or "",
                ).exclude(pk=protocol.pk)[:50]
            )
        except Exception:
            peers = []

    if not peers:
        return FiokoCrossSubjectAnalysis(
            status="NOT_AVAILABLE",
            note="Нет peer-протоколов той же параллели/года для структурного сравнения.",
        )

    items: list[FiokoCrossSubjectItem] = []
    # текущий протокол
    for t in analytics.tasks or []:
        items.append(
            FiokoCrossSubjectItem(
                subject=analytics.subject,
                parallel=int(analytics.parallel),
                year=int(analytics.academic_year),
                skill=t.checked_skill or "",
                topic=t.topic or "",
                completion=t.completion_percent,
                comparison_status="OK" if (t.checked_skill or t.topic) else "NOT_COMPARABLE",
            )
        )
    # peers — только паспорт (без усреднения предметов)
    for p in peers:
        items.append(
            FiokoCrossSubjectItem(
                subject=getattr(p, "subject", "") or "",
                parallel=int(getattr(p, "parallel", 0) or 0),
                year=int(getattr(p, "academic_year", 0) or 0),
                skill="",
                topic="",
                completion=None,
                comparison_status="NOT_COMPARABLE",
            )
        )

    return FiokoCrossSubjectAnalysis(
        status="OK",
        items=items[:200],
        note=(
            "Структурное сравнение предметов/параллелей без усреднения "
            "«среднего результата школы». Task-level peers — NOT_COMPARABLE "
            "без полного mapping умений."
        ),
    )
