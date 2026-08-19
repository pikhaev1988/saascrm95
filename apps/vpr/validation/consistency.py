"""Cross-report numeric consistency validator (global, all protocols)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConsistencyIssue:
    code: str
    severity: str  # error | warning
    message: str
    actual: Any = None
    expected: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "actual": self.actual,
            "expected": self.expected,
        }


@dataclass
class ConsistencyResult:
    ok: bool
    errors: list[ConsistencyIssue] = field(default_factory=list)
    warnings: list[ConsistencyIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


class CrossReportConsistencyValidator:
    """
    Проверяет согласованность чисел между разделами отчёта/analysis.

    Не молча «чинит» данные — только фиксирует ERROR/WARNING.
    """

    RATE_TOLERANCE = 0.05  # absolute pp for percent vs count/N

    def validate(self, analysis, report=None) -> ConsistencyResult:
        errors: list[ConsistencyIssue] = []
        warnings: list[ConsistencyIssue] = []

        n = self._participants(analysis, report)
        facts = getattr(analysis, "facts", None) or getattr(report, "facts", None)
        self._check_groups(analysis, report, n, errors, warnings)
        self._check_task_metric_contract(analysis, errors, warnings)
        self._check_marks(analysis, n, errors, warnings)
        self._check_facts(facts, analysis, report, n, errors, warnings)
        self._check_scores_invariants(facts, errors, warnings)
        self._check_journal_invariants(facts, errors, warnings)
        self._check_not_available_zero(report, errors, warnings)

        return ConsistencyResult(ok=not errors, errors=errors, warnings=warnings)

    def _participants(self, analysis, report) -> int:
        summary = getattr(analysis, "summary", None)
        n = int(getattr(summary, "participants_count", None) or 0)
        if not n:
            n = int(getattr(analysis, "participants_count", None) or 0)
        if report is not None:
            for item in getattr(report, "passport", None) or []:
                label = str(getattr(item, "label", "") or "").lower()
                if "участник" in label or "обучающ" in label:
                    try:
                        n = max(n, int(float(str(getattr(item, "value", "0")).replace("%", "").strip() or 0)))
                    except (TypeError, ValueError):
                        pass
        return n

    def _check_groups(self, analysis, report, n: int, errors, warnings) -> None:
        profile = getattr(analysis, "participant_groups", None) or getattr(
            analysis, "groups_profile", None
        )
        groups = None
        if profile is not None:
            groups = getattr(profile, "groups", None)
        if isinstance(groups, dict) and groups:
            high = int(getattr(groups.get("high"), "count", 0) or 0) if groups.get("high") else 0
            medium = int(getattr(groups.get("medium"), "count", 0) or 0) if groups.get("medium") else 0
            # alias stable == medium
            stable = medium
            if groups.get("stable") is not None:
                stable = int(getattr(groups.get("stable"), "count", 0) or 0)
            risk = int(getattr(groups.get("risk"), "count", 0) or 0) if groups.get("risk") else 0
            total = high + medium + risk
            # If stable key used instead of medium
            if "stable" in groups and "medium" not in groups:
                total = high + stable + risk
            if n and total != n:
                errors.append(
                    ConsistencyIssue(
                        code="consistency.groups_sum",
                        severity="error",
                        message="risk + stable/medium + high != participants",
                        actual={"high": high, "medium": medium, "stable": stable, "risk": risk, "sum": total, "N": n},
                        expected={"sum": n},
                    )
                )
            # percent ↔ count
            for key in ("high", "medium", "risk", "stable"):
                bucket = groups.get(key)
                if bucket is None:
                    continue
                count = int(getattr(bucket, "count", 0) or 0)
                pct = getattr(bucket, "percent", None)
                if pct is None or not n:
                    continue
                expected_pct = round(100.0 * count / n, 1)
                if abs(float(pct) - expected_pct) > self.RATE_TOLERANCE + 0.15:
                    errors.append(
                        ConsistencyIssue(
                            code="consistency.group_percent",
                            severity="error",
                            message=f"group {key}: percent does not match count/N",
                            actual={"count": count, "percent": pct, "N": n},
                            expected={"percent": expected_pct},
                        )
                    )

        # Report individual_groups vs analysis (same labels)
        if report is not None and n:
            by_key = {}
            for g in getattr(report, "individual_groups", None) or []:
                key = str(getattr(g, "key", "") or "")
                if key in {"high", "medium", "risk", "stable"}:
                    by_key[key] = int(getattr(g, "count", 0) or 0)
            if len(by_key) >= 3:
                s = by_key.get("high", 0) + by_key.get("medium", by_key.get("stable", 0)) + by_key.get("risk", 0)
                if s != n:
                    errors.append(
                        ConsistencyIssue(
                            code="consistency.report_groups_sum",
                            severity="error",
                            message="report individual_groups high+medium+risk != N",
                            actual={**by_key, "sum": s, "N": n},
                            expected={"sum": n},
                        )
                    )

    def _check_task_metric_contract(self, analysis, errors, warnings) -> None:
        task_analysis = getattr(analysis, "task_analysis", None)
        tasks = list(getattr(task_analysis, "items", None) or []) if task_analysis else []
        if not tasks:
            tasks = list(getattr(analysis, "task_rows", None) or getattr(analysis, "tasks", None) or [])
        for t in tasks:
            n = int(getattr(t, "participants_count", None) or getattr(t, "n", None) or 0)
            full = int(getattr(t, "full_score_count", 0) or 0)
            partial = int(getattr(t, "partial_score_count", 0) or 0)
            zero = int(getattr(t, "zero_score_count", 0) or 0)
            if n > 0 and full + partial + zero != n:
                code = str(getattr(t, "task_code", None) or getattr(t, "code", "?"))
                errors.append(
                    ConsistencyIssue(
                        code="consistency.task_fpz",
                        severity="error",
                        message=f"task {code}: FULL+PARTIAL+ZERO != N",
                        actual={"full": full, "partial": partial, "zero": zero, "sum": full + partial + zero, "N": n},
                        expected={"sum": n},
                    )
                )

    def _check_marks(self, analysis, n: int, errors, warnings) -> None:
        marks = getattr(analysis, "marks", None)
        if marks is None:
            analytics = getattr(analysis, "analytics", None)
            marks = getattr(analytics, "marks", None) if analytics is not None else None
        if marks is None:
            return
        dist = (
            getattr(marks, "distribution", None)
            or getattr(marks, "by_mark", None)
            or getattr(marks, "vpr", None)
        )
        if isinstance(dist, dict) and n:
            total = sum(int(v or 0) for v in dist.values())
            if total and total != n:
                warnings.append(
                    ConsistencyIssue(
                        code="consistency.marks_sum",
                        severity="warning",
                        message="sum of mark distribution != N",
                        actual={"sum": total, "N": n},
                        expected={"sum": n},
                    )
                )

    def _check_facts(self, facts, analysis, report, n: int, errors, warnings) -> None:
        if facts is None:
            return
        if n and int(facts.participants or 0) != n:
            errors.append(
                ConsistencyIssue(
                    code="consistency.facts_participants",
                    severity="error",
                    message="facts.participants != N",
                    actual=facts.participants,
                    expected=n,
                )
            )
        exclusive = facts.exclusive_group_sum()
        if n and exclusive != n:
            errors.append(
                ConsistencyIssue(
                    code="consistency.facts_groups_sum",
                    severity="error",
                    message="facts exclusive groups != participants",
                    actual={"sum": exclusive, "N": n},
                    expected={"sum": n},
                )
            )
        pot = facts.groups.get("positive_potential")
        if pot is not None and pot.group_type != "OVERLAPPING":
            errors.append(
                ConsistencyIssue(
                    code="consistency.overlapping_potential",
                    severity="error",
                    message="positive_potential must be OVERLAPPING",
                    actual=pot.group_type,
                    expected="OVERLAPPING",
                )
            )
        if report is not None:
            for g in getattr(report, "individual_groups", None) or []:
                key = str(getattr(g, "key", "") or "")
                if key not in {"high", "medium", "risk", "stable"}:
                    continue
                fact = facts.group(key)
                if int(getattr(g, "count", 0) or 0) != fact.count:
                    errors.append(
                        ConsistencyIssue(
                            code="consistency.report_vs_facts_group",
                            severity="error",
                            message=f"report {key} count != facts",
                            actual=getattr(g, "count", None),
                            expected=fact.count,
                        )
                    )
            rows = list(getattr(report, "task_performance_rows", None) or [])
            if rows and facts.tasks.total and len(rows) != facts.tasks.total:
                errors.append(
                    ConsistencyIssue(
                        code="consistency.task_count",
                        severity="error",
                        message="task table count != facts.tasks.total",
                        actual=len(rows),
                        expected=facts.tasks.total,
                    )
                )
            from apps.vpr.analytics.config import below_50_threshold, is_below_threshold

            thr50, incl50 = below_50_threshold()
            below = [
                r
                for r in rows
                if is_below_threshold(
                    getattr(r, "completion_percent", None),
                    thr50,
                    inclusive=incl50,
                )
            ]
            if rows and len(below) != facts.tasks.below_50:
                errors.append(
                    ConsistencyIssue(
                        code="consistency.tasks_below_50",
                        severity="error",
                        message="task table below_50 != facts",
                        actual=len(below),
                        expected=facts.tasks.below_50,
                    )
                )

    def _check_scores_invariants(self, facts, errors, warnings) -> None:
        if facts is None:
            return
        scores = facts.scores
        mean, median, mn, mx, cv = scores.mean, scores.median, scores.min, scores.max, scores.cv
        if mean is not None and mn is not None and float(mean) < float(mn) - 1e-6:
            errors.append(
                ConsistencyIssue(
                    code="invariant.mean_ge_min",
                    severity="error",
                    message="mean < min",
                    actual={"mean": mean, "min": mn},
                )
            )
        if mean is not None and mx is not None and float(mean) > float(mx) + 1e-6:
            errors.append(
                ConsistencyIssue(
                    code="invariant.mean_le_max",
                    severity="error",
                    message="mean > max",
                    actual={"mean": mean, "max": mx},
                )
            )
        if median is not None and mn is not None and float(median) < float(mn) - 1e-6:
            errors.append(
                ConsistencyIssue(
                    code="invariant.median_ge_min",
                    severity="error",
                    message="median < min",
                    actual={"median": median, "min": mn},
                )
            )
        if median is not None and mx is not None and float(median) > float(mx) + 1e-6:
            errors.append(
                ConsistencyIssue(
                    code="invariant.median_le_max",
                    severity="error",
                    message="median > max",
                    actual={"median": median, "max": mx},
                )
            )
        if cv is not None and float(cv) < -1e-6:
            errors.append(
                ConsistencyIssue(
                    code="invariant.cv_ge_0",
                    severity="error",
                    message="cv < 0",
                    actual=cv,
                )
            )

    def _check_journal_invariants(self, facts, errors, warnings) -> None:
        if facts is None:
            return
        c = facts.comparison
        total = c.equal + c.vpr_lower_than_journal + c.vpr_higher_than_journal
        if c.compared and total != c.compared:
            errors.append(
                ConsistencyIssue(
                    code="invariant.journal_sum",
                    severity="error",
                    message="journal equal+lower+higher != compared",
                    actual={"sum": total, "compared": c.compared},
                    expected={"sum": c.compared},
                )
            )

    def _check_not_available_zero(self, report, errors, warnings) -> None:
        if report is None:
            return
        for row in getattr(report, "action_plan", None) or []:
            base = str(getattr(row, "baseline_value", "") or "").strip()
            target = str(getattr(row, "target_value", "") or "").strip()
            if base in {"данные отсутствуют", "NOT_AVAILABLE"} and target in {"0", "0%", "100%"}:
                errors.append(
                    ConsistencyIssue(
                        code="kpi.not_available_as_zero",
                        severity="error",
                        message="NOT_AVAILABLE baseline converted to numeric KPI target",
                        actual={"baseline": base, "target": target},
                    )
                )
