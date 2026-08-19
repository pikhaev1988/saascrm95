"""
VPR Report Validator — проверка готовой аналитической модели перед DOCX/HTML.

Не изменяет данные: только checks / errors / warnings.
При критических ошибках генерация отчёта блокируется.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from apps.vpr.analytics.thresholds import VPR_THRESHOLDS, get_vpr_thresholds
from apps.vpr.conclusion.rules import classify_mastery
from apps.vpr.exceptions import VprError
from apps.vpr.expert_analysis.profiles import PROFILE_LABELS

RATE_SUM_TOLERANCE = 0.01  # percentage points after rounding
FORBIDDEN_PARTIAL_PHRASES = (
    "умение не сформировано",
    "не сформированы ключевые",
    "не сформированы отдельные предметные",
)
FORBIDDEN_OBJECTIVITY_PHRASES = (
    "необъективность доказана",
    "доказана необъективность",
)
VAGUE_KPI_PHRASES = (
    "позитивная динамика",
)

REQUIRED_SECTIONS = (
    ("passport", "1. Паспорт"),
    ("individual_groups", "2. Индивидуальные результаты"),
    ("marks_rows", "3. Статистика отметок"),
    ("objectivity_cycle", "4. ВПР/журнал"),
    ("scores_rows", "5. Первичные баллы"),
    ("task_performance_rows", "6. Задания"),
    ("planned_results", "7. Планируемые результаты"),
    ("group_task_insights", "8. Группы"),
    ("deficit_items", "9. Дефициты"),
    ("admin_director", "10. Администрация"),
    ("smo_actions", "11. ШМО"),
    ("teacher_deficits", "12. Педагоги"),
    ("parent_actions", "13. Родители"),
    ("method_recommendations", "14. Методические рекомендации"),
    ("action_plan", "15. План мероприятий"),
    ("final_conclusion", "16. Итоговое заключение"),
)


class VprReportBlockedError(VprError):
    """Генерация отчёта заблокирована validator'ом."""

    def __init__(self, message: str, *, validation: "VprReportValidationResult"):
        super().__init__(message)
        self.message = message
        self.validation = validation


@dataclass(slots=True)
class VprReportCheck:
    check_code: str
    severity: str  # ok | warning | error | critical
    message: str
    actual: Any = None
    expected: Any = None
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VprReportValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[VprReportCheck] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "checks": [c.to_dict() for c in self.checks],
            "summary": dict(self.summary),
        }


def _add(
    checks: list[VprReportCheck],
    *,
    code: str,
    severity: str,
    message: str,
    actual: Any = None,
    expected: Any = None,
    source: str = "",
) -> None:
    checks.append(
        VprReportCheck(
            check_code=code,
            severity=severity,
            message=message,
            actual=actual,
            expected=expected,
            source=source,
        )
    )


def _in_range(value: float | None, lo: float, hi: float) -> bool:
    if value is None:
        return True
    return lo <= float(value) <= hi


def _collect_report_text(report) -> str:
    chunks: list[str] = []
    for attr in (
        "passport_assessment",
        "final_conclusion",
        "content_pipeline",
        "teacher_deficits",
        "teacher_actions",
        "method_recommendations",
        "admin_director",
        "admin_deputy",
        "smo_actions",
        "parent_actions",
    ):
        val = getattr(report, attr, None) or []
        chunks.extend(str(x) for x in val)
    for cycle_name in (
        "individual_cycle",
        "marks_cycle",
        "objectivity_cycle",
        "scores_cycle",
        "content_cycle",
        "planned_cycle",
        "group_task_cycle",
        "deficits_cycle",
        "admin_cycle",
        "smo_cycle",
        "teachers_cycle",
        "parents_cycle",
        "method_cycle",
    ):
        cycle = getattr(report, cycle_name, None)
        if cycle is None:
            continue
        for field_name in (
            "interpretation",
            "causes",
            "org_decisions",
            "method_decisions",
            "expected_effect",
        ):
            chunks.extend(str(x) for x in (getattr(cycle, field_name, None) or []))
    for row in getattr(report, "planned_results", None) or []:
        chunks.append(str(getattr(row, "explanation", "") or ""))
        chunks.append(str(getattr(row, "subject_actions", "") or ""))
    for row in getattr(report, "action_plan", None) or []:
        chunks.append(str(getattr(row, "expected_result", "") or ""))
        chunks.append(str(getattr(row, "efficiency_indicator", "") or ""))
    return "\n".join(chunks).lower()


class VprReportValidator:
    """Проверяет analysis + готовый SubjectReport (если передан)."""

    def validate(self, analysis, report=None, *, expert=None) -> VprReportValidationResult:
        checks: list[VprReportCheck] = []
        self._check_participants(analysis, checks)
        self._check_groups(analysis, checks)
        self._check_scores(analysis, checks)
        self._check_task_metrics(analysis, report, checks)
        self._check_rates(analysis, report, checks)
        self._check_multi_score(analysis, report, checks)
        self._check_marks(analysis, checks)
        self._check_objectivity(analysis, report, checks)
        self._check_planned(report, checks)
        self._check_deficits(analysis, report, checks)
        self._check_profile(report, expert, checks)
        self._check_kpi(report, checks)
        self._check_sections(report, checks)
        self._check_wording_conflicts(analysis, report, checks)
        self._check_fioko_2026(analysis, report, checks)
        self._check_cross_consistency(analysis, report, checks)

        errors = [
            c.message
            for c in checks
            if c.severity in {"error", "critical"}
        ]
        warnings = [c.message for c in checks if c.severity == "warning"]
        critical = sum(1 for c in checks if c.severity == "critical")
        valid = critical == 0 and not any(c.severity == "error" for c in checks)
        return VprReportValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            checks=checks,
            summary={
                "checks_total": len(checks),
                "ok": sum(1 for c in checks if c.severity == "ok"),
                "warnings": len(warnings),
                "errors": sum(1 for c in checks if c.severity == "error"),
                "critical": critical,
                "thresholds_fingerprint": {
                    "groups": get_vpr_thresholds()["groups"],
                    "deficits": get_vpr_thresholds()["deficits"],
                },
            },
        )

    def validate_or_raise(self, analysis, report=None, *, expert=None) -> VprReportValidationResult:
        result = self.validate(analysis, report, expert=expert)
        if not result.valid:
            raise VprReportBlockedError(
                "VPR report validation failed: "
                + "; ".join(result.errors[:5]),
                validation=result,
            )
        return result

    # --- checks ---------------------------------------------------------

    def _check_participants(self, analysis, checks: list[VprReportCheck]) -> None:
        summary = getattr(analysis, "summary", None)
        n = int(getattr(summary, "participants_count", 0) or 0)
        students = list(getattr(getattr(analysis, "analytics", None), "students", None) or [])
        if n <= 0:
            _add(
                checks,
                code="participants.total_positive",
                severity="critical",
                message="total_students must be > 0",
                actual=n,
                expected=">0",
                source="summary.participants_count",
            )
        else:
            _add(
                checks,
                code="participants.total_positive",
                severity="ok",
                message="total_students > 0",
                actual=n,
                expected=">0",
                source="summary.participants_count",
            )

        if n and len(students) != n:
            _add(
                checks,
                code="participants.count_match",
                severity="critical",
                message="individual results count != total_students",
                actual=len(students),
                expected=n,
                source="analytics.students",
            )
        else:
            _add(
                checks,
                code="participants.count_match",
                severity="ok",
                message="individual results count matches N",
                actual=len(students),
                expected=n,
                source="analytics.students",
            )

        codes = [getattr(s, "participant_code", None) for s in students]
        dupes = sorted({c for c in codes if c and codes.count(c) > 1})
        if dupes:
            _add(
                checks,
                code="participants.unique",
                severity="critical",
                message="duplicate participant codes",
                actual=dupes[:10],
                expected="unique codes",
                source="analytics.students",
            )
        else:
            _add(
                checks,
                code="participants.unique",
                severity="ok",
                message="no duplicate participants",
                actual=len(codes),
                expected="unique",
                source="analytics.students",
            )

        groups = getattr(analysis, "participant_groups", None)
        incomplete = set(getattr(groups, "incomplete_participant_codes", None) or [])
        data_incomplete = bool(getattr(groups, "data_incomplete", False))
        missing = []
        for s in students:
            code = getattr(s, "participant_code", None)
            if getattr(s, "primary_score", None) is None and code not in incomplete and not data_incomplete:
                missing.append(code)
        if missing:
            _add(
                checks,
                code="participants.primary_or_incomplete",
                severity="critical",
                message="participants without primary_score and without data_incomplete flag",
                actual=missing[:10],
                expected="primary_score or data_incomplete",
                source="participant_groups",
            )
        else:
            _add(
                checks,
                code="participants.primary_or_incomplete",
                severity="ok",
                message="each participant has primary_score or is flagged incomplete",
                actual=len(incomplete),
                expected="documented",
                source="participant_groups",
            )

    def _check_groups(self, analysis, checks: list[VprReportCheck]) -> None:
        summary = getattr(analysis, "summary", None)
        n = int(getattr(summary, "participants_count", 0) or 0)
        groups = getattr(analysis, "participant_groups", None)
        gmap = getattr(groups, "groups", None) or {}
        high = int(getattr(gmap.get("high"), "count", 0) or 0)
        medium = int(getattr(gmap.get("medium"), "count", 0) or 0)
        risk = int(getattr(gmap.get("risk"), "count", 0) or 0)
        total = high + medium + risk
        if n and total != n:
            _add(
                checks,
                code="groups.sum_equals_n",
                severity="critical",
                message="high+medium+risk != total_students",
                actual={"high": high, "medium": medium, "risk": risk, "sum": total},
                expected=n,
                source="participant_groups",
            )
        else:
            _add(
                checks,
                code="groups.sum_equals_n",
                severity="ok",
                message="primary groups sum to N",
                actual=total,
                expected=n,
                source="participant_groups",
            )

        # positive potential must not inflate primary sum
        pot = list(getattr(groups, "positive_potential_codes", None) or [])
        _add(
            checks,
            code="groups.positive_potential_extra",
            severity="ok",
            message="positive_potential is extra flag (not a 4th exclusive group)",
            actual=len(pot),
            expected="not in high+medium+risk sum",
            source="participant_groups.positive_potential_codes",
        )

        # one group per participant
        codes_lists = []
        for key in ("high", "medium", "risk"):
            bucket = gmap.get(key)
            codes_lists.extend(list(getattr(bucket, "participant_codes", None) or []))
        overlap = sorted({c for c in codes_lists if codes_lists.count(c) > 1})
        if overlap:
            _add(
                checks,
                code="groups.exclusive",
                severity="critical",
                message="participant assigned to more than one primary group",
                actual=overlap[:10],
                expected="exactly one primary group",
                source="participant_groups",
            )
        else:
            _add(
                checks,
                code="groups.exclusive",
                severity="ok",
                message="each participant has exactly one primary group",
                actual=len(set(codes_lists)),
                expected=n,
                source="participant_groups",
            )

    def _check_scores(self, analysis, checks: list[VprReportCheck]) -> None:
        summary = getattr(analysis, "summary", None)
        if summary is None:
            return
        avg = getattr(summary, "avg_primary_score", None)
        amin = getattr(summary, "min_primary_score", None)
        amax = getattr(summary, "max_primary_result", None)
        if avg is not None and amin is not None and float(avg) < float(amin):
            _add(
                checks,
                code="scores.avg_ge_min",
                severity="critical",
                message="avg_primary < min_primary",
                actual=avg,
                expected=f">={amin}",
                source="summary",
            )
        else:
            _add(
                checks,
                code="scores.avg_ge_min",
                severity="ok",
                message="avg_primary >= min_primary",
                actual=avg,
                expected=amin,
                source="summary",
            )
        if avg is not None and amax is not None and float(avg) > float(amax):
            _add(
                checks,
                code="scores.avg_le_max",
                severity="critical",
                message="avg_primary > max_primary_result",
                actual=avg,
                expected=f"<={amax}",
                source="summary",
            )
        else:
            _add(
                checks,
                code="scores.avg_le_max",
                severity="ok",
                message="avg_primary <= max_primary_result",
                actual=avg,
                expected=amax,
                source="summary",
            )

    def _iter_tasks(self, analysis, report):
        tasks = list(getattr(getattr(analysis, "analytics", None), "tasks", None) or [])
        if tasks:
            for t in tasks:
                yield {
                    "code": getattr(t, "task_code", None),
                    "max_score": int(getattr(t, "max_score", 0) or 0),
                    "full": int(getattr(t, "full_score_count", None) or getattr(t, "full_count", 0) or 0),
                    "partial": int(
                        getattr(t, "partial_score_count", None) or getattr(t, "partial_count", 0) or 0
                    ),
                    "zero": int(getattr(t, "zero_score_count", None) or getattr(t, "zero_count", 0) or 0),
                    "n": int(getattr(t, "total_students", None) or getattr(t, "answers_count", 0) or 0),
                    "earned": getattr(t, "earned_points_sum", None),
                    "max_points": getattr(t, "max_points_sum", None),
                    "mean": getattr(t, "mean_score", None) if getattr(t, "mean_score", None) is not None else getattr(t, "avg_score", None),
                    "completion": getattr(t, "completion_percent", None),
                    "full_rate": getattr(t, "full_score_rate", None),
                    "partial_rate": getattr(t, "partial_score_rate", None),
                    "zero_rate": getattr(t, "zero_score_rate", None),
                }
            return
        for row in getattr(report, "task_performance_rows", None) or []:
            yield {
                "code": getattr(row, "task_code", None),
                "max_score": int(getattr(row, "max_score", 0) or 0),
                "full": int(getattr(row, "full_score_count", None) or getattr(row, "correct_count", 0) or 0),
                "partial": int(getattr(row, "partial_count", 0) or 0),
                "zero": int(getattr(row, "zero_score_count", None) or getattr(row, "incorrect_count", 0) or 0),
                "n": int(getattr(row, "answers_count", 0) or 0),
                "earned": getattr(row, "earned_points_sum", None),
                "max_points": getattr(row, "max_points_sum", None),
                "mean": getattr(row, "mean_score", None),
                "completion": getattr(row, "completion_percent", None),
                "full_rate": getattr(row, "full_score_rate", None),
                "partial_rate": getattr(row, "partial_score_rate", None),
                "zero_rate": getattr(row, "zero_score_rate", None),
            }

    def _check_task_metrics(self, analysis, report, checks: list[VprReportCheck]) -> None:
        for t in self._iter_tasks(analysis, report):
            code = t["code"]
            total = t["full"] + t["partial"] + t["zero"]
            if t["n"] and total != t["n"]:
                _add(
                    checks,
                    code="tasks.count_invariant",
                    severity="critical",
                    message=f"task {code}: full+partial+zero != N",
                    actual={"full": t["full"], "partial": t["partial"], "zero": t["zero"], "sum": total},
                    expected=t["n"],
                    source=f"task:{code}",
                )
            earned = t["earned"]
            max_points = t["max_points"]
            if earned is not None and float(earned) < 0:
                _add(
                    checks,
                    code="tasks.earned_ge_0",
                    severity="critical",
                    message=f"task {code}: earned_points < 0",
                    actual=earned,
                    expected=">=0",
                    source=f"task:{code}",
                )
            if earned is not None and max_points is not None and float(earned) > float(max_points):
                _add(
                    checks,
                    code="tasks.earned_le_max",
                    severity="critical",
                    message=f"task {code}: earned_points > max_points",
                    actual=earned,
                    expected=max_points,
                    source=f"task:{code}",
                )

    def _check_rates(self, analysis, report, checks: list[VprReportCheck]) -> None:
        for t in self._iter_tasks(analysis, report):
            code = t["code"]
            for name, val in (
                ("full_score_rate", t["full_rate"]),
                ("partial_score_rate", t["partial_rate"]),
                ("zero_score_rate", t["zero_rate"]),
                ("completion_percent", t["completion"]),
            ):
                if val is None:
                    continue
                if not _in_range(float(val), 0.0, 100.0):
                    _add(
                        checks,
                        code=f"rates.{name}_range",
                        severity="critical",
                        message=f"task {code}: {name} out of [0,100]",
                        actual=val,
                        expected="0..100",
                        source=f"task:{code}",
                    )
            fr, pr, zr = t["full_rate"], t["partial_rate"], t["zero_rate"]
            if fr is not None and pr is not None and zr is not None:
                s = float(fr) + float(pr) + float(zr)
                if abs(s - 100.0) > RATE_SUM_TOLERANCE + 0.5:
                    # allow ~0.5 for typical 2-digit rounding of three rates
                    _add(
                        checks,
                        code="rates.sum_approx_100",
                        severity="critical",
                        message=f"task {code}: rate sum not ≈100%",
                        actual=round(s, 4),
                        expected="≈100",
                        source=f"task:{code}",
                    )
                elif abs(s - 100.0) > RATE_SUM_TOLERANCE:
                    _add(
                        checks,
                        code="rates.sum_approx_100",
                        severity="warning",
                        message=f"task {code}: rate sum rounding drift",
                        actual=round(s, 4),
                        expected="≈100 (±0.01 ideal)",
                        source=f"task:{code}",
                    )

    def _check_multi_score(self, analysis, report, checks: list[VprReportCheck]) -> None:
        for t in self._iter_tasks(analysis, report):
            if int(t["max_score"] or 0) <= 1:
                continue
            code = t["code"]
            missing = []
            for name, val in (
                ("mean_score", t["mean"]),
                ("completion_percent", t["completion"]),
                ("full_score_rate", t["full_rate"]),
                ("partial_score_rate", t["partial_rate"]),
                ("zero_score_rate", t["zero_rate"]),
            ):
                if val is None and t["n"]:
                    missing.append(name)
            if missing:
                _add(
                    checks,
                    code="multi_score.fields",
                    severity="error",
                    message=f"multi-score task {code} missing metrics: {', '.join(missing)}",
                    actual=missing,
                    expected="mean/completion/full/partial/zero rates",
                    source=f"task:{code}",
                )

    def _check_marks(self, analysis, checks: list[VprReportCheck]) -> None:
        summary = getattr(analysis, "summary", None)
        n = int(getattr(summary, "participants_count", 0) or 0)
        marks = getattr(getattr(analysis, "analytics", None), "marks", None)
        vpr = getattr(marks, "vpr", None) or {}
        m2 = int(vpr.get("2", 0) or 0)
        m3 = int(vpr.get("3", 0) or 0)
        m4 = int(vpr.get("4", 0) or 0)
        m5 = int(vpr.get("5", 0) or 0)
        total = m2 + m3 + m4 + m5
        if n and total and total != n:
            _add(
                checks,
                code="marks.sum_equals_n",
                severity="critical",
                message="marks 2+3+4+5 != total_students",
                actual={"2": m2, "3": m3, "4": m4, "5": m5, "sum": total},
                expected=n,
                source="marks.vpr",
            )
        elif n:
            _add(
                checks,
                code="marks.sum_equals_n",
                severity="ok",
                message="marks sum equals N",
                actual=total,
                expected=n,
                source="marks.vpr",
            )
        if n and total == n:
            quality_calc = round(100.0 * (m4 + m5) / n, 2)
            absolute_calc = round(100.0 * (n - m2) / n, 2)
            quality = getattr(summary, "knowledge_quality_percent", None)
            absolute = getattr(summary, "absolute_achievement_percent", None)
            if quality is not None and abs(float(quality) - quality_calc) > 0.6:
                _add(
                    checks,
                    code="marks.quality_match",
                    severity="error",
                    message="knowledge_quality_percent mismatch vs (4+5)/N",
                    actual=quality,
                    expected=quality_calc,
                    source="summary",
                )
            if absolute is not None and abs(float(absolute) - absolute_calc) > 0.6:
                _add(
                    checks,
                    code="marks.absolute_match",
                    severity="error",
                    message="absolute_achievement_percent mismatch vs (N-2)/N",
                    actual=absolute,
                    expected=absolute_calc,
                    source="summary",
                )

    def _check_objectivity(self, analysis, report, checks: list[VprReportCheck]) -> None:
        obj = getattr(analysis, "objectivity", None)
        if obj is None:
            return
        cmp_ = getattr(obj, "journal_comparison", None) or {}
        equal = int(cmp_.get("equal", 0) or 0)
        lower = int(cmp_.get("lower", 0) or 0)
        higher = int(cmp_.get("higher", 0) or 0)
        compared = int(getattr(obj, "compared_count", 0) or 0)
        if equal + lower + higher != compared:
            _add(
                checks,
                code="objectivity.pair_sum",
                severity="critical",
                message="equal+lower+higher != compared_count",
                actual={"equal": equal, "lower": lower, "higher": higher, "sum": equal + lower + higher},
                expected=compared,
                source="objectivity",
            )
        else:
            _add(
                checks,
                code="objectivity.pair_sum",
                severity="ok",
                message="objectivity pair counts consistent",
                actual=compared,
                expected=compared,
                source="objectivity",
            )
        n = int(getattr(getattr(analysis, "summary", None), "participants_count", 0) or 0)
        if compared > n:
            _add(
                checks,
                code="objectivity.compared_le_n",
                severity="critical",
                message="compared_count > total_students",
                actual=compared,
                expected=f"<={n}",
                source="objectivity",
            )
        text = _collect_report_text(report) if report is not None else ""
        for phrase in FORBIDDEN_OBJECTIVITY_PHRASES:
            if phrase in text:
                _add(
                    checks,
                    code="objectivity.forbidden_proven",
                    severity="error",
                    message=f"forbidden objectivity wording: {phrase!r}",
                    actual=phrase,
                    expected="признаки риска расхождения…",
                    source="report_text",
                )

    def _check_planned(self, report, checks: list[VprReportCheck]) -> None:
        if report is None:
            return
        rows = list(getattr(report, "planned_results", None) or [])
        if not rows:
            _add(
                checks,
                code="planned.present",
                severity="warning",
                message="planned results list is empty",
                actual=0,
                expected=">=1 when catalog linked",
                source="planned_results",
            )
            return
        for row in rows:
            linked = getattr(row, "linked_tasks", None)
            evidence = getattr(row, "evidence", None)
            tasks_count = int(getattr(row, "tasks_count", 0) or 0)
            if tasks_count <= 0 and not linked:
                _add(
                    checks,
                    code="planned.linked_tasks",
                    severity="warning",
                    message=f"planned result without linked tasks: {getattr(row, 'result', '')[:60]}",
                    actual=tasks_count,
                    expected=">=1",
                    source="planned_results",
                )
            status = getattr(row, "status", None)
            pct = getattr(row, "average_percent", None)
            expected_status = None
            band = classify_mastery(pct)
            if band in {"high", "sufficient"}:
                expected_status = "achieved"
            elif band == "acceptable":
                expected_status = "partial"
            elif band is not None:
                expected_status = "not_achieved"
            if expected_status and status != expected_status:
                _add(
                    checks,
                    code="planned.status_mastery",
                    severity="error",
                    message="planned status does not match classify_mastery",
                    actual=status,
                    expected=expected_status,
                    source=str(getattr(row, "result", "")[:80]),
                )
            if not evidence and not getattr(row, "explanation", None):
                _add(
                    checks,
                    code="planned.evidence",
                    severity="warning",
                    message="planned result without evidence/explanation",
                    actual=None,
                    expected="evidence",
                    source=str(getattr(row, "result", "")[:80]),
                )

    def _check_deficits(self, analysis, report, checks: list[VprReportCheck]) -> None:
        items = list(getattr(report, "deficit_items", None) or []) if report else []
        for item in items:
            pct = getattr(item, "average_percent", None)
            priority = str(getattr(item, "priority", "") or "")
            evidence_status = str(getattr(item, "evidence_status", "") or "ESTABLISHED")
            evidence = getattr(item, "evidence", None) or ""
            linked = list(getattr(item, "linked_tasks", None) or [])
            linked_results = list(getattr(item, "linked_results", None) or [])
            impact = str(getattr(item, "impact_results", "") or "")

            if evidence_status == "INSUFFICIENT_DATA":
                # Neutral insufficient-data claim is allowed; categorical claim is not.
                categorical = any(
                    x in impact.lower()
                    for x in (
                        "выявлен дефицит",
                        "существенно снижает",
                        "устойчивый дефицит по направлению",
                    )
                ) and "недостаточно данных" not in impact.lower()
                if categorical:
                    _add(
                        checks,
                        code="deficits.insufficient_categorical",
                        severity="error",
                        message=(
                            "INSUFFICIENT_DATA deficit with categorical wording: "
                            f"{getattr(item, 'name', '')[:60]}"
                        ),
                        actual=impact[:120],
                        expected="neutral INSUFFICIENT_DATA wording",
                        source="deficit_items",
                    )
                elif not evidence:
                    _add(
                        checks,
                        code="deficits.insufficient_marked",
                        severity="warning",
                        message="INSUFFICIENT_DATA without explicit evidence note",
                        actual=getattr(item, "name", None),
                        expected="evidence_status + evidence note",
                        source="deficit_items",
                    )
                continue

            # ESTABLISHED (or legacy missing field): require real evidence gate
            if not evidence and not linked and not linked_results and pct is None:
                _add(
                    checks,
                    code="deficits.evidence",
                    severity="error",
                    message=(
                        "categorical deficit without evidence/linked_tasks: "
                        f"{getattr(item, 'name', '')[:60]}"
                    ),
                    actual=None,
                    expected="evidence or linked_tasks or stats",
                    source="deficit_items",
                )
            elif (
                not evidence
                and not linked
                and not linked_results
                and "недостаточно данных" not in impact.lower()
            ):
                # Narrative claim without linkage/evidence note — High/error even if pct present
                # (pct alone without evidence string is weak for categorical wording)
                if any(
                    x in impact.lower()
                    for x in ("выявлен дефицит", "существенно снижает", "дефицит «")
                ):
                    _add(
                        checks,
                        code="deficits.evidence",
                        severity="error",
                        message=(
                            "categorical deficit without evidence/linked_tasks: "
                            f"{getattr(item, 'name', '')[:60]}"
                        ),
                        actual=impact[:120] or None,
                        expected="evidence or linked_tasks",
                        source="deficit_items",
                    )
                elif not impact:
                    _add(
                        checks,
                        code="deficits.evidence",
                        severity="error",
                        message=(
                            "deficit without evidence: "
                            f"{getattr(item, 'name', '')[:60]}"
                        ),
                        actual=None,
                        expected="evidence from results",
                        source="deficit_items",
                    )
            # priority vs thresholds (informational consistency)
            thr = VPR_THRESHOLDS["deficits"]
            if pct is not None and priority and priority != "INSUFFICIENT_DATA":
                band = classify_mastery(float(pct))
                if band == "critical" and priority.lower() not in {"critical", "высокий", "high"}:
                    _add(
                        checks,
                        code="deficits.priority_threshold",
                        severity="warning",
                        message="deficit priority may not match mastery band",
                        actual={"priority": priority, "pct": pct, "band": band},
                        expected=thr,
                        source="deficit_items",
                    )

        # engine deficits without linked tasks
        deficits = getattr(analysis, "deficits", None)
        for kind, collection in (
            ("topic", getattr(deficits, "topics", None) or []),
            ("skill", getattr(deficits, "skills", None) or []),
        ):
            for d in collection:
                linked = getattr(d, "task_codes", None) or getattr(d, "tasks", None) or []
                if not linked and getattr(d, "priority", None) in {"Critical", "High", "critical", "high"}:
                    _add(
                        checks,
                        code="deficits.linked_tasks",
                        severity="warning",
                        message=f"{kind} deficit without linked tasks",
                        actual=getattr(d, "name", None) or getattr(d, "topic", None) or getattr(d, "skill", None),
                        expected="linked_tasks",
                        source="analysis.deficits",
                    )

    def _check_profile(self, report, expert, checks: list[VprReportCheck]) -> None:
        code = ""
        if expert is not None:
            code = str(getattr(expert, "profile_code", "") or "")
        if not code and report is not None:
            # quality_level is label; try to reverse-map
            label = str(getattr(report, "quality_level", "") or "")
            for k, v in PROFILE_LABELS.items():
                if v == label:
                    code = k
                    break
        if not code:
            _add(
                checks,
                code="profile.exists",
                severity="warning",
                message="profile code not available on report/expert",
                actual=None,
                expected="valid profile code",
                source="expert.profile_code",
            )
            return
        if code not in PROFILE_LABELS:
            _add(
                checks,
                code="profile.valid_code",
                severity="error",
                message="invalid profile code",
                actual=code,
                expected=sorted(PROFILE_LABELS.keys()),
                source="expert.profile_code",
            )
        else:
            _add(
                checks,
                code="profile.valid_code",
                severity="ok",
                message="profile code is allowed",
                actual=code,
                expected="PROFILE_LABELS",
                source="expert.profile_code",
            )
        evidence = []
        if expert is not None:
            evidence = list(getattr(expert, "profile_explanation", None) or [])
        if not evidence:
            _add(
                checks,
                code="profile.evidence",
                severity="warning",
                message="profile without evidence/explanation",
                actual=code,
                expected="evidence",
                source="expert.profile_explanation",
            )
        # thresholds alignment (structure only)
        thr = get_vpr_thresholds()
        _add(
            checks,
            code="profile.thresholds",
            severity="ok",
            message="profile uses shared VPR_THRESHOLDS bands via classify_mastery/spread",
            actual={"groups": thr["groups"], "cv": thr["achievement_cv"]},
            expected="VPR_THRESHOLDS",
            source="thresholds",
        )

    def _check_kpi(self, report, checks: list[VprReportCheck]) -> None:
        if report is None:
            return
        for i, row in enumerate(getattr(report, "action_plan", None) or []):
            action = str(getattr(row, "action", "") or "").strip()
            kpi = str(
                getattr(row, "kpi", None)
                or getattr(row, "efficiency_indicator", None)
                or ""
            ).strip()
            expected = str(getattr(row, "expected_result", "") or "").strip()
            responsible = str(getattr(row, "executor", "") or getattr(row, "responsible", "") or "").strip()
            deadline = str(getattr(row, "deadline", "") or "").strip()
            source = f"action_plan[{i}]"
            if not action or not responsible or not deadline or not expected:
                _add(
                    checks,
                    code="kpi.required_fields",
                    severity="error",
                    message="plan row missing action/responsible/deadline/expected_result",
                    actual={
                        "action": bool(action),
                        "responsible": bool(responsible),
                        "deadline": bool(deadline),
                        "expected_result": bool(expected),
                    },
                    expected="all present",
                    source=source,
                )
            if not kpi:
                _add(
                    checks,
                    code="kpi.missing",
                    severity="error",
                    message=f"plan row without KPI: {action[:60]}",
                    actual=None,
                    expected="measurable KPI",
                    source=source,
                )
            low = (kpi + " " + expected).lower()
            if any(p in low for p in VAGUE_KPI_PHRASES):
                _add(
                    checks,
                    code="kpi.vague",
                    severity="warning",
                    message=f"vague KPI wording: {action[:60]}",
                    actual=expected or kpi,
                    expected="measurable baseline/target or operational KPI",
                    source=source,
                )

    def _check_sections(self, report, checks: list[VprReportCheck]) -> None:
        if report is None:
            _add(
                checks,
                code="sections.report_present",
                severity="critical",
                message="report object is missing",
                actual=None,
                expected="SubjectReport",
                source="report",
            )
            return
        for attr, title in REQUIRED_SECTIONS:
            val = getattr(report, attr, None)
            missing = val is None
            if isinstance(val, list) and attr in {
                "passport",
                "final_conclusion",
                "method_recommendations",
                "action_plan",
            }:
                # empty list for these is treated as missing section content
                missing = len(val) == 0
            if missing and attr == "scores_rows":
                # empty scores may happen; still require attribute existence
                missing = not hasattr(report, attr)
            if missing and attr in {"group_task_insights", "deficit_items", "smo_actions"}:
                # may be empty analytically — presence of cycle/field is enough
                missing = not hasattr(report, attr)
            if missing:
                _add(
                    checks,
                    code="sections.present",
                    severity="critical",
                    message=f"missing report section: {title}",
                    actual=attr,
                    expected="present",
                    source="SubjectReport",
                )
            else:
                _add(
                    checks,
                    code="sections.present",
                    severity="ok",
                    message=f"section present: {title}",
                    actual=attr,
                    expected="present",
                    source="SubjectReport",
                )

    def _check_wording_conflicts(self, analysis, report, checks: list[VprReportCheck]) -> None:
        if report is None:
            return
        # multi-score partial without full → forbid "not formed" style claims nearby
        conflict_tasks = []
        for t in self._iter_tasks(analysis, report):
            if int(t["max_score"] or 0) <= 1:
                continue
            fr = t["full_rate"]
            pr = t["partial_rate"]
            if fr is not None and pr is not None and float(fr) == 0 and float(pr) > 0:
                conflict_tasks.append(t["code"])
        text = _collect_report_text(report)
        if conflict_tasks:
            for phrase in FORBIDDEN_PARTIAL_PHRASES:
                if phrase in text:
                    _add(
                        checks,
                        code="wording.partial_not_formed",
                        severity="error",
                        message=(
                            "expert wording 'умение не сформировано' conflicts with "
                            f"multi-score partial>0 (tasks={conflict_tasks[:5]})"
                        ),
                        actual=phrase,
                        expected="полного выполнения не достиг… при этом зафиксировано частичное выполнение",
                        source="report_text",
                    )
                    break
            else:
                _add(
                    checks,
                    code="wording.partial_not_formed",
                    severity="ok",
                    message="no forbidden 'not formed' wording with partial>0 multi-score tasks",
                    actual=conflict_tasks[:5],
                    expected="safe wording",
                    source="report_text",
                )

    def _check_cross_consistency(self, analysis, report, checks: list[VprReportCheck]) -> None:
        from apps.vpr.validation.consistency import CrossReportConsistencyValidator

        result = CrossReportConsistencyValidator().validate(analysis, report)
        for err in result.errors:
            _add(
                checks,
                code=err.code,
                severity="error",
                message=err.message,
                actual=err.actual,
                expected=err.expected,
                source="cross_consistency",
            )
        for warn in result.warnings:
            _add(
                checks,
                code=warn.code,
                severity="warning",
                message=warn.message,
                actual=warn.actual,
                expected=warn.expected,
                source="cross_consistency",
            )
        if result.ok:
            _add(
                checks,
                code="consistency.ok",
                severity="ok",
                message="cross-report numeric consistency OK",
                source="cross_consistency",
            )

    def _check_fioko_2026(self, analysis, report, checks: list[VprReportCheck]) -> None:
        """FIOKO 2026 methodology checks — mostly warnings, not DOCX blockers."""
        layer = getattr(analysis, "fioko_2026", None)
        if layer is None and report is not None:
            # evidence may live only on report
            evidence = getattr(report, "fioko_evidence", None) or {}
        else:
            evidence = layer.to_dict() if hasattr(layer, "to_dict") else (layer or {})

        if not evidence and layer is None:
            _add(
                checks,
                code="fioko.layer_missing",
                severity="warning",
                message="FIOKO 2026 layer отсутствует в analysis/report",
                source="fioko_2026",
            )
            return

        mapping = getattr(report, "fioko_mapping", None) if report is not None else None
        if not mapping:
            mapping = evidence.get("mapping") if isinstance(evidence, dict) else None
        if mapping:
            _add(
                checks,
                code="fioko.mapping_present",
                severity="ok",
                message="FIOKO direction→sections mapping present",
                source="FIOKO_2026",
            )
        else:
            _add(
                checks,
                code="fioko.mapping_present",
                severity="warning",
                message="FIOKO mapping matrix отсутствует",
                source="FIOKO_2026",
            )

        if report is not None and not getattr(report, "methodology_basis", None):
            _add(
                checks,
                code="fioko.methodology_basis",
                severity="warning",
                message="methodology_basis не заполнен",
                source="FIOKO_2026",
            )
        elif report is not None:
            _add(
                checks,
                code="fioko.methodology_basis",
                severity="ok",
                message="methodology_basis заполнен",
                source="FIOKO_2026",
            )

        catalog = (
            getattr(report, "catalog_mapping_status", None)
            or (evidence.get("catalog_mapping_status") if isinstance(evidence, dict) else None)
            or "NOT_AVAILABLE"
        )
        if catalog in {"NOT_AVAILABLE", "NOT_MAPPED"}:
            _add(
                checks,
                code="fioko.catalog_mapping",
                severity="warning",
                message=f"catalog_mapping_status={catalog}",
                actual=catalog,
                source="FIOKO_2026",
            )
        else:
            _add(
                checks,
                code="fioko.catalog_mapping",
                severity="ok",
                message=f"catalog_mapping_status={catalog}",
                actual=catalog,
                source="FIOKO_2026",
            )

        # Threshold classification consistency on task rows
        tasks = []
        if isinstance(evidence, dict):
            tasks = evidence.get("tasks") or []
        if not tasks and layer is not None:
            tasks = [t.to_dict() if hasattr(t, "to_dict") else t for t in (getattr(layer, "tasks", None) or [])]
        bad_cls = 0
        for t in tasks:
            if not isinstance(t, dict):
                continue
            status = t.get("fioko_level_status")
            diff = t.get("difficulty")
            pct = t.get("completion_percent")
            if status == "not_available":
                continue
            if diff == "unknown" and status != "not_available":
                bad_cls += 1
            if pct is None and status != "not_available":
                bad_cls += 1
        if bad_cls:
            _add(
                checks,
                code="fioko.threshold_classification",
                severity="warning",
                message=f"противоречивая FIOKO-классификация заданий: {bad_cls}",
                actual=bad_cls,
                source="FIOKO_2026",
            )
        else:
            _add(
                checks,
                code="fioko.threshold_classification",
                severity="ok",
                message="FIOKO threshold classification consistent",
                source="FIOKO_2026",
            )

        # Sample size warnings
        dist = evidence.get("distribution") if isinstance(evidence, dict) else None
        if dist and dist.get("sample_warning"):
            _add(
                checks,
                code="fioko.sample.distribution",
                severity="warning",
                message=(
                    f"distribution sample N={dist.get('sample_size')} "
                    f"quality={dist.get('sample_quality')}"
                ),
                source="FIOKO_2026",
            )
        groups = evidence.get("groups") if isinstance(evidence, dict) else None
        if groups and groups.get("sample_warning"):
            _add(
                checks,
                code="fioko.sample.groups",
                severity="warning",
                message=f"groups sample N={groups.get('sample_size')} < 10 informational_only",
                source="FIOKO_2026",
            )

        journal = evidence.get("journal") if isinstance(evidence, dict) else None
        if journal:
            if journal.get("status") == "NOT_AVAILABLE":
                _add(
                    checks,
                    code="fioko.journal_gap",
                    severity="warning",
                    message="journal comparison NOT_AVAILABLE",
                    source="FIOKO_2026",
                )
            else:
                _add(
                    checks,
                    code="fioko.journal_gap",
                    severity="ok",
                    message=f"journal gap_ge_2_count={journal.get('gap_ge_2_count')}",
                    actual=journal.get("gap_ge_2_count"),
                    source="FIOKO_2026",
                )

        if dist is not None:
            flags = dist.get("boundary_peak_flags") or []
            bstatus = dist.get("boundary_peak_status") or "NOT_AVAILABLE"
            bsource = dist.get("boundary_source") or "NOT_AVAILABLE"
            marker = bool(dist.get("possible_objectivity_marker"))
            gp = dist.get("general_peak") or {}
            if bsource != "official" and marker:
                _add(
                    checks,
                    code="fioko.boundary_peak_without_official",
                    severity="error",
                    message="possible_objectivity_marker=true без official boundaries",
                    actual={"boundary_source": bsource, "marker": marker},
                    source="FIOKO_2026",
                )
            elif marker and bstatus not in {"HAS_MARKER", "OK"}:
                _add(
                    checks,
                    code="fioko.boundary_peak_status",
                    severity="warning",
                    message=f"marker=true but boundary_peak_status={bstatus}",
                    source="FIOKO_2026",
                )
            else:
                _add(
                    checks,
                    code="fioko.distribution_boundaries",
                    severity="ok",
                    message=(
                        f"boundary_peak_status={bstatus}; source={bsource}; "
                        f"marker={marker}; general_peak={gp.get('is_peak')}"
                    ),
                    source="FIOKO_2026",
                )
            if gp.get("is_peak") and marker and bsource != "official":
                _add(
                    checks,
                    code="fioko.general_peak_as_objectivity",
                    severity="error",
                    message="GENERAL_PEAK не должен автоматически создавать objectivity marker",
                    source="FIOKO_2026",
                )

        deficits = evidence.get("skill_deficits") if isinstance(evidence, dict) else None
        if deficits is not None:
            _add(
                checks,
                code="fioko.skill_deficit_evidence",
                severity="ok",
                message=f"skill_deficits entries={len(deficits)}",
                source="FIOKO_2026",
            )

        cy = evidence.get("cross_year") if isinstance(evidence, dict) else None
        if cy:
            st = cy.get("status")
            sev = "ok" if st in {"OK", "NOT_AVAILABLE", "NOT_COMPARABLE"} else "warning"
            _add(
                checks,
                code="fioko.cross_year",
                severity=sev,
                message=f"cross_year status={st}",
                source="FIOKO_2026",
            )

        cs = evidence.get("cross_subject") if isinstance(evidence, dict) else None
        if cs:
            _add(
                checks,
                code="fioko.cross_subject",
                severity="ok",
                message=f"cross_subject status={cs.get('status')}",
                source="FIOKO_2026",
            )

        recs = getattr(report, "management_recommendations", None) if report else None
        if not recs and isinstance(evidence, dict):
            recs = evidence.get("management_recommendations")
        if recs:
            _add(
                checks,
                code="fioko.management_recommendations",
                severity="ok",
                message=f"management_recommendations={len(recs)}",
                source="FIOKO_2026",
            )
        else:
            _add(
                checks,
                code="fioko.management_recommendations",
                severity="warning",
                message="management_recommendations пуст",
                source="FIOKO_2026",
            )

        # HTML/DOCX consistency proxy: report evidence tasks vs layer tasks
        if report is not None and tasks:
            report_tasks = getattr(report, "task_performance_rows", None) or []
            mismatches = 0
            by_code = {t.get("task_code"): t for t in tasks if isinstance(t, dict)}
            for row in report_tasks:
                code = getattr(row, "task_code", None)
                ft = by_code.get(code)
                if not ft:
                    continue
                rp = getattr(row, "completion_percent", None)
                fp = ft.get("completion_percent")
                if rp is not None and fp is not None and abs(float(rp) - float(fp)) > 0.51:
                    mismatches += 1
                rs = getattr(row, "fioko_level_status", None) or ""
                fs = ft.get("fioko_level_status") or ""
                if rs and fs and rs != fs:
                    mismatches += 1
            _add(
                checks,
                code="fioko.html_docx_consistency",
                severity="warning" if mismatches else "ok",
                message=(
                    f"HTML/DOCX FIOKO field mismatches={mismatches}"
                    if mismatches
                    else "HTML/DOCX FIOKO fields consistent"
                ),
                actual=mismatches,
                source="FIOKO_2026",
            )

        # --- Stage 7.1: group sample + SYSTEM/FIOKO wording ---
        if report is not None:
            bad_groups = []
            limited_unmarked = []
            for g in getattr(report, "individual_groups", None) or []:
                n = int(getattr(g, "count", 0) or 0)
                informative = bool(getattr(g, "informative", True))
                status = str(getattr(g, "sample_status", "") or "")
                if n < 10 and getattr(g, "key", "") in {"risk", "medium", "high"}:
                    if informative or status == "INFORMATIVE":
                        bad_groups.append(getattr(g, "key", "?"))
                    text_blob = str(getattr(g, "characteristic", "") or "").lower()
                    if "limited_sample" not in status.lower() and "недостаточна" not in text_blob and "менее 10" not in text_blob:
                        limited_unmarked.append(getattr(g, "key", "?"))
            if bad_groups:
                _add(
                    checks,
                    code="fioko.group_sample_informative",
                    severity="error",
                    message=f"N<10 groups marked informative: {bad_groups}",
                    source="FIOKO_2026",
                )
            else:
                _add(
                    checks,
                    code="fioko.group_sample_informative",
                    severity="ok",
                    message="group N<10 => LIMITED_SAMPLE / informative=false",
                    source="FIOKO_2026",
                )
            if limited_unmarked:
                _add(
                    checks,
                    code="fioko.group_sample_wording",
                    severity="warning",
                    message=f"LIMITED_SAMPLE without explicit wording: {limited_unmarked}",
                    source="FIOKO_2026",
                )

            text = _collect_report_text(report)
            forbidden_mix = (
                "в логике фиоко: выделены группа риска",
                "в логике фиоко выделены группы риска",
                "проведено в логике фиоко",
            )
            mixed = [p for p in forbidden_mix if p in text]
            # softer check: SYSTEM groups claimed as FIOKO classification
            if "в логике рекомендаций фиоко: выделены группа риска" in text:
                mixed.append("legacy_fioko_groups_claim")
            if mixed:
                _add(
                    checks,
                    code="fioko.system_vs_fioko_wording",
                    severity="error",
                    message=f"SYSTEM_ANALYTICS groups presented as FIOKO: {mixed[:3]}",
                    source="FIOKO_2026",
                )
            else:
                _add(
                    checks,
                    code="fioko.system_vs_fioko_wording",
                    severity="ok",
                    message="SYSTEM_ANALYTICS not presented as FIOKO requirement",
                    source="FIOKO_2026",
                )
