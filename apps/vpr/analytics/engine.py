"""
Аналитическое ядро ВПР.

Только расчёты показателей. Без рекомендаций, отчётов и UI.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Iterable

from apps.vpr.analytics.result import (
    VprAnalyticsResult,
    VprMarksDistribution,
    VprScoresDistribution,
    VprSkillAnalytics,
    VprStudentAnalytics,
    VprSummaryMetrics,
    VprTaskAnalytics,
    VprTopicAnalytics,
)
from apps.vpr.analytics.stats import (
    coefficient_of_variation,
    degree_of_learning,
    distribution_counts,
    percent,
    population_stdev,
    safe_mean,
    safe_median,
    safe_mode,
    to_float,
)
from apps.vpr.models import VprProtocol, VprStudentResult, VprTask
from apps.vpr.services.catalog_lookup import VprTaskCatalogLookup

logger = logging.getLogger(__name__)


class VprAnalyticsEngine:
    """
    Принимает протокол ВПР и возвращает полностью рассчитанную аналитику.

    Использование::

        result = VprAnalyticsEngine().analyze(protocol)
        payload = result.to_dict()
    """

    def __init__(self, *, catalog_lookup: VprTaskCatalogLookup | None = None) -> None:
        self.catalog = catalog_lookup or VprTaskCatalogLookup()

    def analyze(self, protocol: VprProtocol | int) -> VprAnalyticsResult:
        protocol_obj = self._load_protocol(protocol)
        students = list(
            protocol_obj.student_results.prefetch_related("task_scores__task").order_by(
                "participant_code"
            )
        )
        tasks = list(protocol_obj.tasks.order_by("position", "id"))

        primary_scores = [to_float(s.primary_score) for s in students if s.primary_score is not None]
        marks_vpr = [int(s.mark_vpr) for s in students if s.mark_vpr is not None]
        marks_journal = [int(s.mark_journal) for s in students if s.mark_journal is not None]

        max_primary = int(protocol_obj.max_primary_score or 0)
        if max_primary <= 0 and primary_scores:
            max_primary = int(max(primary_scores))

        summary = self._build_summary(
            participants_count=len(students),
            max_primary_score=max_primary,
            primary_scores=primary_scores,
            marks_vpr=marks_vpr,
            marks_journal=marks_journal,
        )
        marks = self._build_marks(marks_vpr, marks_journal)
        scores = self._build_scores(primary_scores)
        task_rows = self._build_tasks(protocol_obj, tasks, students)
        topics = self._build_topics(task_rows)
        skills = self._build_skills(task_rows)
        student_rows = self._build_students(students, max_primary)

        result = VprAnalyticsResult(
            protocol_id=protocol_obj.pk,
            subject=protocol_obj.subject,
            parallel=protocol_obj.parallel,
            academic_year=protocol_obj.academic_year,
            organization_name=protocol_obj.organization_name or protocol_obj.organization_code or "",
            summary=summary,
            marks=marks,
            scores=scores,
            tasks=task_rows,
            topics=topics,
            skills=skills,
            students=student_rows,
        )
        logger.info(
            "VPR analytics computed protocol_id=%s participants=%s tasks=%s",
            protocol_obj.pk,
            summary.participants_count,
            len(task_rows),
        )
        return result

    def analyze_to_dict(self, protocol: VprProtocol | int) -> dict:
        return self.analyze(protocol).to_dict()

    def _load_protocol(self, protocol: VprProtocol | int) -> VprProtocol:
        if isinstance(protocol, VprProtocol):
            protocol_id = protocol.pk
        else:
            protocol_id = int(protocol)
        return VprProtocol.objects.get(pk=protocol_id)

    def _build_summary(
        self,
        *,
        participants_count: int,
        max_primary_score: int,
        primary_scores: list[float],
        marks_vpr: list[int],
        marks_journal: list[int],
    ) -> VprSummaryMetrics:
        quality = None
        absolute = None
        if marks_vpr:
            quality = percent(sum(1 for m in marks_vpr if m >= 4), len(marks_vpr))
            absolute = percent(sum(1 for m in marks_vpr if m >= 3), len(marks_vpr))

        return VprSummaryMetrics(
            participants_count=participants_count,
            max_primary_score=max_primary_score,
            avg_primary_score=safe_mean(primary_scores),
            min_primary_score=round(min(primary_scores), 4) if primary_scores else None,
            max_primary_result=round(max(primary_scores), 4) if primary_scores else None,
            avg_mark_vpr=safe_mean(marks_vpr),
            avg_mark_journal=safe_mean(marks_journal),
            knowledge_quality_percent=quality,
            absolute_achievement_percent=absolute,
            median_primary_score=safe_median(primary_scores),
            mode_primary_score=safe_mode(primary_scores),
            stdev_primary_score=population_stdev(primary_scores),
            cv_primary_score_percent=coefficient_of_variation(primary_scores),
            sou_percent=degree_of_learning(marks_vpr),
        )

    def _build_marks(self, marks_vpr: list[int], marks_journal: list[int]) -> VprMarksDistribution:
        vpr_counts = distribution_counts(marks_vpr)
        journal_counts = distribution_counts(marks_journal)
        total_vpr = sum(vpr_counts.values()) or 0
        total_journal = sum(journal_counts.values()) or 0
        return VprMarksDistribution(
            vpr=vpr_counts,
            journal=journal_counts,
            vpr_percents={
                key: round((value / total_vpr) * 100, 2) for key, value in vpr_counts.items()
            }
            if total_vpr
            else {},
            journal_percents={
                key: round((value / total_journal) * 100, 2) for key, value in journal_counts.items()
            }
            if total_journal
            else {},
        )

    def _build_scores(self, primary_scores: list[float]) -> VprScoresDistribution:
        counts = distribution_counts(primary_scores)
        total = sum(counts.values()) or 0
        return VprScoresDistribution(
            counts=counts,
            percents={
                key: round((value / total) * 100, 2) for key, value in counts.items()
            }
            if total
            else {},
        )

    def _build_tasks(
        self,
        protocol: VprProtocol,
        tasks: list[VprTask],
        students: list[VprStudentResult],
    ) -> list[VprTaskAnalytics]:
        rows: list[VprTaskAnalytics] = []
        score_maps = [
            {item.task_id: item for item in student.task_scores.all()}
            for student in students
        ]
        for task in tasks:
            scores: list[float] = []
            full = partial = zero = 0
            max_score = int(task.max_score or 0)
            for score_map in score_maps:
                score_obj = score_map.get(task.id)
                raw = to_float(score_obj.score) if score_obj else None
                if raw is None:
                    zero += 1
                    scores.append(0.0)
                    continue
                scores.append(raw)
                if max_score > 0:
                    if raw >= max_score:
                        full += 1
                    elif raw > 0:
                        partial += 1
                    else:
                        zero += 1
                else:
                    if raw > 0:
                        full += 1
                    else:
                        zero += 1

            avg_score = safe_mean(scores)
            completion = None
            if max_score > 0 and scores:
                completion = percent(sum(scores), max_score * len(scores))

            catalog = self.catalog.resolve(
                subject=protocol.subject,
                parallel=protocol.parallel,
                academic_year=protocol.academic_year,
                task_code=task.code,
            )
            rows.append(
                VprTaskAnalytics(
                    task_code=task.code,
                    task_number=task.code,
                    position=int(task.position or 0),
                    max_score=max_score,
                    avg_score=avg_score,
                    completion_percent=completion,
                    full_count=full,
                    partial_count=partial,
                    zero_count=zero,
                    answers_count=len(students),
                    correct_count=full,
                    incorrect_count=zero,
                    topic=(catalog.topic if catalog else "") or "",
                    program_section=(catalog.program_section if catalog else "") or "",
                    checked_skill=(catalog.checked_skill if catalog else "") or "",
                    difficulty=(catalog.difficulty if catalog else task.difficulty) or "",
                    catalog_matched=catalog is not None,
                )
            )
        return rows

    def _build_topics(self, tasks: list[VprTaskAnalytics]) -> list[VprTopicAnalytics]:
        buckets: dict[str, list[VprTaskAnalytics]] = defaultdict(list)
        for task in tasks:
            key = (task.topic or "").strip() or "Без темы в справочнике"
            buckets[key].append(task)

        result: list[VprTopicAnalytics] = []
        for topic, items in sorted(buckets.items(), key=lambda pair: pair[0].lower()):
            completions = [t.completion_percent for t in items if t.completion_percent is not None]
            avg_scores = [t.avg_score for t in items if t.avg_score is not None]
            errors = sum(t.partial_count + t.zero_count for t in items)
            result.append(
                VprTopicAnalytics(
                    topic=topic,
                    tasks_count=len(items),
                    avg_completion_percent=safe_mean(completions),
                    avg_score=safe_mean(avg_scores),
                    errors_count=errors,
                    task_codes=[t.task_code for t in items],
                )
            )
        return result

    def _build_skills(self, tasks: list[VprTaskAnalytics]) -> list[VprSkillAnalytics]:
        buckets: dict[str, list[VprTaskAnalytics]] = defaultdict(list)
        for task in tasks:
            key = (task.checked_skill or "").strip() or "Без умения в справочнике"
            buckets[key].append(task)

        result: list[VprSkillAnalytics] = []
        for skill, items in sorted(buckets.items(), key=lambda pair: pair[0].lower()):
            completions = [t.completion_percent for t in items if t.completion_percent is not None]
            avg_scores = [t.avg_score for t in items if t.avg_score is not None]
            result.append(
                VprSkillAnalytics(
                    checked_skill=skill,
                    tasks_count=len(items),
                    avg_completion_percent=safe_mean(completions),
                    avg_score=safe_mean(avg_scores),
                    task_codes=[t.task_code for t in items],
                )
            )
        return result

    def _build_students(
        self,
        students: list[VprStudentResult],
        max_primary_score: int,
    ) -> list[VprStudentAnalytics]:
        scored = []
        for student in students:
            score = to_float(student.primary_score)
            scored.append((student, score if score is not None else float("-inf")))

        # место среди всех участников (1 = лучший), одинаковые баллы — одинаковое место
        overall_places = self._competition_ranks(
            [score for _, score in scored],
            higher_is_better=True,
        )

        by_class: dict[str, list[tuple[int, float]]] = defaultdict(list)
        for idx, (student, score) in enumerate(scored):
            class_key = (student.class_group or "").strip() or "—"
            by_class[class_key].append((idx, score))

        class_places: dict[int, int | None] = {}
        for pairs in by_class.values():
            ranks = self._competition_ranks([score for _, score in pairs], higher_is_better=True)
            for (idx, _), rank in zip(pairs, ranks):
                class_places[idx] = rank

        rows: list[VprStudentAnalytics] = []
        for idx, (student, score) in enumerate(scored):
            finite_score = score if score != float("-inf") else None
            task_values = [
                to_float(item.score)
                for item in student.task_scores.all()
                if item.score is not None
            ]
            completion = None
            if finite_score is not None and max_primary_score > 0:
                completion = percent(finite_score, max_primary_score)
            rows.append(
                VprStudentAnalytics(
                    participant_code=student.participant_code,
                    full_name=student.full_name or "",
                    class_group=student.class_group or "",
                    gender=student.gender or "",
                    primary_score=finite_score,
                    mark_vpr=student.mark_vpr,
                    mark_journal=student.mark_journal,
                    completion_percent=completion,
                    avg_task_score=safe_mean(task_values),
                    place_overall=overall_places[idx],
                    place_in_class=class_places.get(idx),
                )
            )
        # сортировка по месту, затем по коду
        rows.sort(
            key=lambda row: (
                row.place_overall if row.place_overall is not None else 10**9,
                row.participant_code,
            )
        )
        return rows

    @staticmethod
    def _competition_ranks(scores: Iterable[float], *, higher_is_better: bool) -> list[int | None]:
        """
        Competition ranking: 1, 2, 2, 4...
        Участники без балла (-inf) получают места в конце.
        """
        items = list(scores)
        n = len(items)
        present = [(idx, value) for idx, value in enumerate(items) if value != float("-inf")]
        missing = [idx for idx, value in enumerate(items) if value == float("-inf")]
        present.sort(key=lambda pair: (-pair[1] if higher_is_better else pair[1], pair[0]))

        ranks: list[int | None] = [None] * n
        i = 0
        while i < len(present):
            j = i
            current = present[i][1]
            while j + 1 < len(present) and present[j + 1][1] == current:
                j += 1
            place = i + 1
            for k in range(i, j + 1):
                ranks[present[k][0]] = place
            i = j + 1

        next_place = len(present) + 1
        for offset, idx in enumerate(missing):
            ranks[idx] = next_place + offset
        return ranks
