"""
Stage 10 — integrity / arithmetic validation layer.

SOURCE → FACTS → CALCULATIONS → AGGREGATES → REPORT
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class IntegrityIssue:
    code: str
    severity: str  # error | warning
    message: str
    actual: Any = None
    expected: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IntegrityResult:
    ok: bool
    protocol_id: int | None = None
    errors: list[IntegrityIssue] = field(default_factory=list)
    warnings: list[IntegrityIssue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "protocol_id": self.protocol_id,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "metrics": dict(self.metrics),
        }


class VprIntegrityValidator:
    """Арифметика и методологические ограничения без protocol_id forks."""

    def validate(self, analysis, protocol=None) -> IntegrityResult:
        errors: list[IntegrityIssue] = []
        warnings: list[IntegrityIssue] = []
        pid = getattr(getattr(analysis, "protocol", None), "protocol_id", None)
        if pid is None and protocol is not None:
            pid = getattr(protocol, "id", None)

        analytics = getattr(analysis, "analytics", None)
        facts = getattr(analysis, "facts", None)
        summary = getattr(analytics, "summary", None) if analytics else None
        n = int(
            getattr(summary, "participants_count", None)
            or getattr(facts, "participants", None)
            or 0
        )
        metrics: dict[str, Any] = {"participants": n}

        # Marks sum == N
        marks = getattr(analytics, "marks", None) if analytics else None
        if marks is not None and n:
            raw = getattr(marks, "vpr", None) or getattr(marks, "counts", None) or {}
            if raw:
                counts = [int(raw.get(k, raw.get(str(k), 0)) or 0) for k in (2, 3, 4, 5)]
                total_marks = sum(counts)
                metrics["mark_counts_sum"] = total_marks
                if total_marks and total_marks != n:
                    errors.append(
                        IntegrityIssue(
                            code="DATA_INTEGRITY_ERROR.marks_sum",
                            severity="error",
                            message="sum(mark_counts) != N",
                            actual=total_marks,
                            expected=n,
                        )
                    )

        # Task FULL+PARTIAL+ZERO == answers_count
        tasks = list(getattr(analytics, "tasks", None) or []) if analytics else []
        metrics["tasks_total"] = len(tasks)
        below = 0
        from apps.vpr.analytics.config import below_50_threshold, is_below_threshold

        thr50, incl50 = below_50_threshold()
        for t in tasks:
            full = int(getattr(t, "full_score_count", None) or getattr(t, "full_count", 0) or 0)
            partial = int(
                getattr(t, "partial_score_count", None) or getattr(t, "partial_count", 0) or 0
            )
            zero = int(getattr(t, "zero_score_count", None) or getattr(t, "zero_count", 0) or 0)
            answers = int(
                getattr(t, "total_students", None) or getattr(t, "answers_count", 0) or 0
            )
            if answers and full + partial + zero != answers:
                errors.append(
                    IntegrityIssue(
                        code="DATA_INTEGRITY_ERROR.task_fpz",
                        severity="error",
                        message=f"FULL+PARTIAL+ZERO != N for task {getattr(t, 'task_code', '?')}",
                        actual={"full": full, "partial": partial, "zero": zero, "N": answers},
                        expected=answers,
                    )
                )
            incorrect = int(getattr(t, "incorrect_count", zero) or 0)
            if answers and incorrect != zero:
                warnings.append(
                    IntegrityIssue(
                        code="integrity.incorrect_alias",
                        severity="warning",
                        message="incorrect_count != zero_score_count",
                        actual={"incorrect": incorrect, "zero": zero},
                    )
                )
            cp = getattr(t, "completion_percent", None)
            if is_below_threshold(cp, thr50, inclusive=incl50):
                below += 1
            if cp is not None and not (0.0 <= float(cp) <= 100.0 + 1e-6):
                errors.append(
                    IntegrityIssue(
                        code="DATA_INTEGRITY_ERROR.percent_range",
                        severity="error",
                        message="completion_percent out of [0,100]",
                        actual=cp,
                    )
                )
            max_score = int(getattr(t, "max_score", 0) or 0)
            if max_score == 0 and cp is not None:
                errors.append(
                    IntegrityIssue(
                        code="DATA_INTEGRITY_ERROR.max_score_zero",
                        severity="error",
                        message="max_score=0 but completion is numeric (should be NOT_APPLICABLE)",
                        actual={"task": getattr(t, "task_code", None), "completion": cp},
                    )
                )

        metrics["tasks_below_50"] = below
        if facts is not None and int(facts.tasks.below_50) != below:
            errors.append(
                IntegrityIssue(
                    code="DATA_INTEGRITY_ERROR.below_50_facts",
                    severity="error",
                    message="facts.tasks.below_50 != recount",
                    actual=facts.tasks.below_50,
                    expected=below,
                )
            )

        # Exclusive groups
        if facts is not None and n:
            exclusive = facts.exclusive_group_sum()
            metrics["exclusive_group_sum"] = exclusive
            if exclusive != n:
                errors.append(
                    IntegrityIssue(
                        code="DATA_INTEGRITY_ERROR.groups_sum",
                        severity="error",
                        message="high+medium+risk != N",
                        actual=exclusive,
                        expected=n,
                    )
                )
            pot = facts.groups.get("positive_potential")
            if pot is not None and pot.group_type != "OVERLAPPING":
                errors.append(
                    IntegrityIssue(
                        code="DATA_INTEGRITY_ERROR.positive_potential",
                        severity="error",
                        message="positive_potential must be OVERLAPPING",
                        actual=pot.group_type,
                    )
                )

        # Average primary / mark (rounding-tolerant)
        students = list(getattr(analytics, "students", None) or []) if analytics else []
        if students and summary is not None:
            scores = [
                float(getattr(s, "primary_score", None) or getattr(s, "score", 0) or 0)
                for s in students
            ]
            if scores:
                mean_score = sum(scores) / len(scores)
                reported = getattr(summary, "avg_primary_score", None)
                metrics["avg_primary_recomputed"] = round(mean_score, 6)
                if reported is not None and abs(float(reported) - mean_score) > 0.051:
                    errors.append(
                        IntegrityIssue(
                            code="DATA_INTEGRITY_ERROR.avg_primary",
                            severity="error",
                            message="sum(primary_scores)/N != report.average_primary_score",
                            actual=reported,
                            expected=mean_score,
                        )
                    )
            marks_list = [
                int(getattr(s, "mark_vpr", None) or 0)
                for s in students
                if getattr(s, "mark_vpr", None) is not None
            ]
            if marks_list:
                mean_mark = sum(marks_list) / len(marks_list)
                reported_m = getattr(summary, "avg_mark_vpr", None)
                metrics["avg_mark_recomputed"] = round(mean_mark, 6)
                if reported_m is not None and abs(float(reported_m) - mean_mark) > 0.051:
                    errors.append(
                        IntegrityIssue(
                            code="DATA_INTEGRITY_ERROR.avg_mark",
                            severity="error",
                            message="sum(marks)/N != report.average_mark",
                            actual=reported_m,
                            expected=mean_mark,
                        )
                    )

        # Sample tier
        from apps.vpr.analytics.config import distribution_sample_tier

        tier = distribution_sample_tier(n)
        metrics["sample_tier"] = tier["tier"]
        metrics["limited_sample"] = not tier["informative"]

        try:
            from apps.vpr.evidence.metric_fact import build_core_metric_facts

            metrics["metric_facts"] = build_core_metric_facts(
                tasks_below_50=below,
                participants=n,
                sample_tier=tier["tier"],
            )
        except Exception:  # noqa: BLE001
            pass

        return IntegrityResult(
            ok=not errors,
            protocol_id=int(pid) if pid is not None else None,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
        )
