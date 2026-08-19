"""
Движок выявления образовательных дефицитов ВПР (ФИОКО).

Вход: объект analytics из VprAnalyticsEngine.
Выход: единый объект deficits (tasks / topics / skills / students / summary).

Без рекомендаций, отчётов и текстовых заключений.
"""

from __future__ import annotations

from typing import Any

from apps.vpr.analytics.result import (
    VprAnalyticsResult,
    VprSkillAnalytics,
    VprStudentAnalytics,
    VprTaskAnalytics,
    VprTopicAnalytics,
)
from apps.vpr.analytics.stats import percent, to_float
from apps.vpr.deficits.config import DeficitThresholds, load_deficit_thresholds
from apps.vpr.deficits.result import (
    VprDeficitResult,
    VprDeficitSummary,
    VprSkillDeficit,
    VprStudentDeficit,
    VprTaskDeficit,
    VprTopicDeficit,
)
from apps.vpr.models import VprProtocol, VprStudentResult


class VprDeficitEngine:
    """
    Использование::

        analytics = VprAnalyticsEngine().analyze(protocol)
        deficits = VprDeficitEngine().analyze(analytics)
        payload = deficits.to_dict()
    """

    def __init__(self, *, thresholds: DeficitThresholds | None = None) -> None:
        self.thresholds = thresholds or load_deficit_thresholds()

    def analyze(
        self,
        analytics: VprAnalyticsResult | dict[str, Any],
        *,
        protocol: VprProtocol | None = None,
    ) -> VprDeficitResult:
        analytics_obj = self._normalize_analytics(analytics)
        task_deficits = self._build_task_deficits(analytics_obj.tasks)
        topic_deficits = self._build_topic_deficits(analytics_obj.topics, task_deficits)
        skill_deficits = self._build_skill_deficits(analytics_obj.skills, task_deficits)
        student_deficits = self._build_student_deficits(
            analytics_obj,
            task_deficits,
            protocol=protocol,
        )
        summary = self._build_summary(
            task_deficits,
            topic_deficits,
            skill_deficits,
            student_deficits,
        )
        return VprDeficitResult(
            protocol_id=analytics_obj.protocol_id,
            tasks=task_deficits,
            topics=topic_deficits,
            skills=skill_deficits,
            students=student_deficits,
            summary=summary,
        )

    def _normalize_analytics(
        self,
        analytics: VprAnalyticsResult | dict[str, Any],
    ) -> VprAnalyticsResult:
        if isinstance(analytics, VprAnalyticsResult):
            return analytics
        if not isinstance(analytics, dict):
            raise TypeError("analytics must be VprAnalyticsResult or dict")
        # поддержка to_dict() без пересчёта — минимальная реконструкция
        from apps.vpr.analytics.result import (
            VprMarksDistribution,
            VprScoresDistribution,
            VprSummaryMetrics,
        )

        summary_raw = analytics.get("summary") or {}
        return VprAnalyticsResult(
            protocol_id=int(analytics["protocol_id"]),
            subject=str(analytics.get("subject") or ""),
            parallel=int(analytics.get("parallel") or 0),
            academic_year=int(analytics.get("academic_year") or 0),
            organization_name=str(analytics.get("organization_name") or ""),
            summary=VprSummaryMetrics(**summary_raw),
            marks=VprMarksDistribution(**(analytics.get("marks") or {})),
            scores=VprScoresDistribution(**(analytics.get("scores") or {})),
            tasks=[VprTaskAnalytics(**item) for item in analytics.get("tasks") or []],
            topics=[VprTopicAnalytics(**item) for item in analytics.get("topics") or []],
            skills=[VprSkillAnalytics(**item) for item in analytics.get("skills") or []],
            students=[VprStudentAnalytics(**item) for item in analytics.get("students") or []],
        )

    def _classify(self, completion_percent: float | None):
        level = self.thresholds.classify(completion_percent)
        priority = self._title_priority(self.thresholds.priority_for(level.code))
        status = self._status_for(level.code)
        return level, priority, status

    @staticmethod
    def _title_priority(code: str) -> str:
        mapping = {
            "critical": "Critical",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
        }
        return mapping.get(code.lower(), code.capitalize() if code else "Medium")

    def _status_for(self, level_code: str) -> str:
        if self.thresholds.is_critical(level_code):
            return "critical_deficit"
        if self.thresholds.is_problem(level_code):
            return "problem_zone"
        return "ok"

    def _build_task_deficits(self, tasks: list[VprTaskAnalytics]) -> list[VprTaskDeficit]:
        rows: list[VprTaskDeficit] = []
        for task in tasks:
            level, priority, status = self._classify(task.completion_percent)
            rows.append(
                VprTaskDeficit(
                    task_code=task.task_code,
                    completion_percent=task.completion_percent,
                    mastery_level=level.code,
                    mastery_label=level.label,
                    status=status,
                    priority=priority,
                    topic=task.topic or "",
                    program_section=task.program_section or "",
                    checked_skill=task.checked_skill or "",
                    difficulty=task.difficulty or "",
                )
            )
        # критические и проблемные выше, затем по проценту возрастанию
        priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        rows.sort(
            key=lambda row: (
                priority_order.get(row.priority, 9),
                row.completion_percent if row.completion_percent is not None else -1,
                row.task_code,
            )
        )
        return rows

    def _build_topic_deficits(
        self,
        topics: list[VprTopicAnalytics],
        task_deficits: list[VprTaskDeficit],
    ) -> list[VprTopicDeficit]:
        by_code = {item.task_code: item for item in task_deficits}
        rows: list[VprTopicDeficit] = []
        for topic in topics:
            related = [by_code[code] for code in topic.task_codes if code in by_code]
            critical_count = sum(
                1 for item in related if self.thresholds.is_critical(item.mastery_level)
            )
            problem_count = sum(
                1 for item in related if self.thresholds.is_problem(item.mastery_level)
            )
            level, priority, _ = self._classify(topic.avg_completion_percent)
            risk = self._title_priority(self.thresholds.risk_for(level.code))
            # усиление риска при наличии критических заданий
            if critical_count > 0 and risk in ("Low", "Medium"):
                risk = "High"
                priority = "High"
            if critical_count >= max(1, topic.tasks_count // 2):
                risk = "Critical"
                priority = "Critical"
            rows.append(
                VprTopicDeficit(
                    topic=topic.topic,
                    avg_completion_percent=topic.avg_completion_percent,
                    tasks_count=topic.tasks_count,
                    critical_tasks_count=critical_count,
                    problem_tasks_count=problem_count,
                    mastery_level=level.code,
                    mastery_label=level.label,
                    risk=risk,
                    priority=priority,
                    task_codes=list(topic.task_codes),
                )
            )
        priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        rows.sort(
            key=lambda row: (
                priority_order.get(row.priority, 9),
                row.avg_completion_percent if row.avg_completion_percent is not None else -1,
                row.topic,
            )
        )
        return rows

    def _build_skill_deficits(
        self,
        skills: list[VprSkillAnalytics],
        task_deficits: list[VprTaskDeficit],
    ) -> list[VprSkillDeficit]:
        by_code = {item.task_code: item for item in task_deficits}
        rows: list[VprSkillDeficit] = []
        for skill in skills:
            related = [by_code[code] for code in skill.task_codes if code in by_code]
            critical_count = sum(
                1 for item in related if self.thresholds.is_critical(item.mastery_level)
            )
            problem_count = sum(
                1 for item in related if self.thresholds.is_problem(item.mastery_level)
            )
            level, priority, _ = self._classify(skill.avg_completion_percent)
            risk = self._title_priority(self.thresholds.risk_for(level.code))
            if critical_count > 0 and risk in ("Low", "Medium"):
                risk = "High"
                priority = "High"
            if critical_count >= max(1, skill.tasks_count // 2):
                risk = "Critical"
                priority = "Critical"
            rows.append(
                VprSkillDeficit(
                    checked_skill=skill.checked_skill,
                    avg_completion_percent=skill.avg_completion_percent,
                    tasks_count=skill.tasks_count,
                    critical_tasks_count=critical_count,
                    problem_tasks_count=problem_count,
                    mastery_level=level.code,
                    mastery_label=level.label,
                    risk=risk,
                    priority=priority,
                    task_codes=list(skill.task_codes),
                )
            )
        priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        rows.sort(
            key=lambda row: (
                priority_order.get(row.priority, 9),
                row.avg_completion_percent if row.avg_completion_percent is not None else -1,
                row.checked_skill,
            )
        )
        return rows

    def _build_student_deficits(
        self,
        analytics: VprAnalyticsResult,
        task_deficits: list[VprTaskDeficit],
        *,
        protocol: VprProtocol | None,
    ) -> list[VprStudentDeficit]:
        task_meta = {item.task_code: item for item in task_deficits}
        student_details = self._load_student_task_details(
            protocol_id=analytics.protocol_id,
            protocol=protocol,
            task_meta=task_meta,
        )

        rows: list[VprStudentDeficit] = []
        for student in analytics.students:
            level, priority, _ = self._classify(student.completion_percent)
            detail = student_details.get(student.participant_code, {})
            unfinished = int(detail.get("unfinished_tasks_count", 0))
            critical_count = int(detail.get("critical_tasks_count", 0))
            problem_count = int(detail.get("problem_tasks_count", 0))
            problem_topics = list(detail.get("problem_topics") or [])
            problem_skills = list(detail.get("problem_skills") or [])

            if critical_count > 0 and priority in ("Low", "Medium"):
                priority = "High"
            if self.thresholds.is_critical(level.code) or critical_count >= 3:
                priority = "Critical"

            rows.append(
                VprStudentDeficit(
                    participant_code=student.participant_code,
                    full_name=student.full_name,
                    class_group=student.class_group,
                    completion_percent=student.completion_percent,
                    mastery_level=level.code,
                    mastery_label=level.label,
                    priority=priority,
                    unfinished_tasks_count=unfinished,
                    critical_tasks_count=critical_count,
                    problem_tasks_count=problem_count,
                    problem_topics=problem_topics,
                    problem_skills=problem_skills,
                )
            )

        priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        rows.sort(
            key=lambda row: (
                priority_order.get(row.priority, 9),
                row.completion_percent if row.completion_percent is not None else -1,
                row.participant_code,
            )
        )
        return rows

    def _load_student_task_details(
        self,
        *,
        protocol_id: int,
        protocol: VprProtocol | None,
        task_meta: dict[str, VprTaskDeficit],
    ) -> dict[str, dict[str, Any]]:
        """
        Детализация по ученикам: невыполненные / критические задания,
        проблемные темы и умения. Читает модели протокола, не меняя аналитическое ядро.
        """
        protocol_obj = protocol
        if protocol_obj is None:
            try:
                protocol_obj = VprProtocol.objects.prefetch_related(
                    "student_results__task_scores__task",
                    "tasks",
                ).get(pk=protocol_id)
            except VprProtocol.DoesNotExist:
                return {}

        max_by_code = {
            task.code: int(task.max_score or 0)
            for task in protocol_obj.tasks.all()
        }
        result: dict[str, dict[str, Any]] = {}
        students: list[VprStudentResult] = list(
            protocol_obj.student_results.prefetch_related("task_scores__task").all()
        )
        for student in students:
            unfinished = 0
            critical_hit = 0
            problem_hit = 0
            topics: set[str] = set()
            skills: set[str] = set()
            for score_row in student.task_scores.all():
                code = score_row.task.code
                max_score = max_by_code.get(code, int(score_row.task.max_score or 0))
                raw = to_float(score_row.score)
                if raw is None or raw <= 0:
                    unfinished += 1

                if max_score <= 0:
                    task_pct = 100.0 if raw and raw > 0 else 0.0
                elif raw is None:
                    task_pct = 0.0
                else:
                    task_pct = percent(raw, max_score)

                level = self.thresholds.classify(task_pct)
                if not self.thresholds.is_problem(level.code):
                    continue

                problem_hit += 1
                if self.thresholds.is_critical(level.code):
                    critical_hit += 1
                meta = task_meta.get(code)
                if meta and (meta.topic or "").strip():
                    topics.add(meta.topic.strip())
                if meta and (meta.checked_skill or "").strip():
                    skills.add(meta.checked_skill.strip())

            result[student.participant_code] = {
                "unfinished_tasks_count": unfinished,
                "critical_tasks_count": critical_hit,
                "problem_tasks_count": problem_hit,
                "problem_topics": sorted(topics),
                "problem_skills": sorted(skills),
            }
        return result

    def _build_summary(
        self,
        tasks: list[VprTaskDeficit],
        topics: list[VprTopicDeficit],
        skills: list[VprSkillDeficit],
        students: list[VprStudentDeficit],
    ) -> VprDeficitSummary:
        tasks_critical = sum(1 for t in tasks if self.thresholds.is_critical(t.mastery_level))
        tasks_problem = sum(1 for t in tasks if self.thresholds.is_problem(t.mastery_level))
        topics_at_risk = sum(1 for t in topics if t.risk in ("Critical", "High"))
        skills_at_risk = sum(1 for s in skills if s.risk in ("Critical", "High"))
        students_at_risk = sum(
            1 for s in students if self.thresholds.is_problem(s.mastery_level) or s.priority in ("Critical", "High")
        )
        all_priorities = (
            [t.priority for t in tasks]
            + [t.priority for t in topics]
            + [s.priority for s in skills]
            + [s.priority for s in students]
        )
        return VprDeficitSummary(
            tasks_total=len(tasks),
            tasks_critical=tasks_critical,
            tasks_problem=tasks_problem,
            topics_at_risk=topics_at_risk,
            skills_at_risk=skills_at_risk,
            students_at_risk=students_at_risk,
            critical_priority_count=sum(1 for p in all_priorities if p == "Critical"),
            high_priority_count=sum(1 for p in all_priorities if p == "High"),
        )
