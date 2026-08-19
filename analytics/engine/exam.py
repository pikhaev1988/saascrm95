from __future__ import annotations

from collections import defaultdict

from django.db.models import Avg, Count, Max, Min, Q

from analytics.engine.catalog import get_task_metadata, validate_topic_belongs_to_subject
from users.task_classification import _official_record as _catalog_official_record
from analytics.knowledge import get_task_knowledge
from analytics.knowledge.insights import build_rich_task_insight
from analytics.knowledge.validation import validate_task_knowledge
from analytics.engine.result import (
    ExamAnalysisResult,
    PrepLevelGroup,
    SkillAnalysis,
    TaskAnalysis,
    TopicAnalysis,
    VALIDATION_ERROR_MESSAGE,
)
from analytics.engine.report_builder import build_unified_recommendations, build_unified_sections
from analytics.engine.statistics import (
    classify_by_thresholds,
    difficulty_index,
    discrimination_index,
    dynamic_thresholds,
    pearson_correlation,
    safe_mean,
    safe_median,
    task_correlation_matrix,
)
from analytics.knowledge.graph import (
    TaskContext,
    build_class_deficit_analysis,
    build_intelligent_deficit_cause,
    build_part_analysis_narrative,
    build_risk_clusters,
    build_strength_summary,
    build_task_contexts,
    build_thematic_blocks,
    build_topic_dependency_graph,
    merge_deficits_by_section,
)
from analytics.engine.tokens import is_blank_token, is_error_token, is_success_token
from analytics.engine.validation import validate_exam_metrics, validation_error_message
from exams.models import ExamResult, TaskResult
from users.task_topics import parse_long_answer_mask, part2_start_task, skill_for_task, subject_key, topic_for_task
from exams.passing import is_gve_exam


class InsightBuilder:
    """Генерация выводов на основе FIPI Knowledge Base и расчётных показателей."""

    @staticmethod
    def task_insight(
        task: TaskAnalysis,
        subject_avg: float,
        subject_name: str = "",
        exam_type: str = "ege",
        task_success_map: dict[int, float] | None = None,
    ) -> str:
        knowledge = get_task_knowledge(subject_name, task.task_number, exam_type) if subject_name else None
        rich = build_rich_task_insight(
            knowledge=knowledge,
            task_number=task.task_number,
            success_rate=task.success_rate,
            subject_avg=subject_avg,
            classification=task.classification,
            subject_name=subject_name,
            exam_type=exam_type,
        )
        if task.success_rate < 50 and knowledge:
            ctx = TaskContext(
                task_number=task.task_number,
                success_rate=task.success_rate,
                classification=task.classification,
                topic=task.topic,
                section=task.section,
                subsection=task.subsection,
                skill_name=task.skill_name,
                grade_range=list(task.grade_range or []),
                exam_part=task.exam_part,
                knowledge=knowledge,
            )
            topic_graph = {
                knowledge.topic[:200]: {
                    "topic": knowledge.topic,
                    "section": knowledge.section,
                    "prerequisites": list(knowledge.previous_topics or []),
                    "tasks": [task.task_number],
                    "avg_success": task.success_rate,
                }
            }
            deficit = build_intelligent_deficit_cause(
                ctx,
                subject_name=subject_name,
                exam_type=exam_type,
                topic_graph=topic_graph,
                task_success_map=task_success_map or {},
            )
            if deficit.get("cause"):
                return deficit["cause"]
        return "\n".join(rich["summary"][:6])

    @staticmethod
    def topic_insight(topic: TopicAnalysis, subject_avg: float, subject_name: str = "") -> str:
        delta = round(subject_avg - topic.success_rate, 1)
        tasks_label = ", ".join(f"№{n}" for n in topic.task_numbers[:6])
        subject = (subject_name or "предмет").strip()
        return (
            f"Предмет «{subject}», тема «{topic.topic[:120]}» (задания {tasks_label}): "
            f"успешность {topic.success_rate}%, отклонение от среднего по предмету {delta:+.1f} п.п."
        )

    @staticmethod
    def part_gap_insight(part1: float, part2: float, part_boundary: int) -> str:
        gap = round(part1 - part2, 1)
        return (
            f"Часть 1 (задания 1–{part_boundary - 1}): {part1}%; "
            f"часть 2 (задания {part_boundary}+): {part2}%; разрыв {gap} п.п."
        )

    @staticmethod
    def methodical_recommendation(
        *,
        topic: str,
        task_numbers: list[int],
        success_rate: float,
        subject_avg: float,
        grade_range: list[int],
        skills: list[str],
    ) -> dict:
        gap = round(subject_avg - success_rate, 1)
        hours = max(1, min(12, int(round(gap / 5)) or 1))
        classes = ", ".join(str(g) for g in grade_range[:4]) or "по спецификации"
        tasks_label = ", ".join(f"№{n}" for n in task_numbers[:8])
        return {
            "topic": topic[:160],
            "tasks": tasks_label,
            "success_rate": success_rate,
            "gap_pp": gap,
            "recommended_hours": hours,
            "classes": classes,
            "skills": skills[:3],
            "exercises": [
                f"Серия заданий {tasks_label} в формате КИМ с разбором ошибок.",
                f"Контрольные мини-диагностики по теме с фиксацией динамики (целевой прирост ≥ {max(5, int(gap // 2))} п.п.).",
            ],
        }


class AnalyticsEngine:
    measure_mode = "percent"

    def analyze_exam(self, school_id: int, exam_id: int, measure_mode: str | None = None) -> ExamAnalysisResult:
        mode = measure_mode or self.measure_mode
        results_qs = ExamResult.objects.filter(student__school_id=school_id, exam_id=exam_id).select_related(
            "exam", "student"
        )
        if not results_qs.exists():
            return ExamAnalysisResult(valid=False, error_message="Нет данных для анализа.")

        first = results_qs.first()
        exam = first.exam
        exam_type = (exam.exam_type or "ege").lower()
        subject = exam.subject or ""
        sk = subject_key(subject, exam_type)
        part_boundary = part2_start_task(exam_type, sk)

        score_values = [float(v or 0) for v in results_qs.values_list("score", flat=True)]
        if not any(score_values):
            score_values = [float(v or 0) for v in results_qs.values_list("total_score", flat=True)]
        stats = results_qs.aggregate(
            avg=Avg("score"),
            min=Min("score"),
            max=Max("score"),
            cnt=Count("id"),
            passed=Count("id", filter=Q(passed=True)),
        )
        if stats["cnt"] and stats["avg"] is None:
            stats = results_qs.aggregate(
                avg=Avg("total_score"),
                min=Min("total_score"),
                max=Max("total_score"),
                cnt=Count("id"),
                passed=Count("id", filter=Q(passed=True)),
            )
        students_count = int(stats["cnt"] or 0)
        if is_gve_exam(exam_code=exam.code, subject_name=subject) or (
            exam_type == "oge" and score_values and max(score_values) <= 5
        ):
            # ГВЭ / оценки 2–5: порог сдачи — оценка ≥ 3.
            pass_count = sum(1 for value in score_values if 0 < float(value) <= 5 and float(value) >= 3)
        elif exam_type == "ege":
            from exams.passing import ege_result_passed

            threshold_cache: dict = {}
            pass_count = 0
            for row in results_qs.values("exam__subject", "exam__code", "exam__year", "score", "passed"):
                if ege_result_passed(
                    subject_name=row.get("exam__subject") or subject,
                    year=row.get("exam__year") or exam.year,
                    score=row.get("score"),
                    passed_flag=row.get("passed"),
                    exam_code=row.get("exam__code") or exam.code,
                    cache=threshold_cache,
                ):
                    pass_count += 1
        else:
            pass_count = int(stats["passed"] or 0)
        fail_count = students_count - pass_count
        avg_score = round(float(stats["avg"] or 0), 2)
        median_score = safe_median(score_values)
        min_score = round(float(stats["min"] or 0), 2)
        max_score = round(float(stats["max"] or 0), 2)
        pass_rate = round((pass_count / students_count) * 100, 1) if students_count else 0.0
        fail_rate = round(100.0 - pass_rate, 1)

        task_rows_qs = TaskResult.objects.filter(student__school_id=school_id, exam_id=exam_id).values(
            "task_number", "value", "student_id"
        )
        raw_task_rows = list(task_rows_qs.values("task_number", "value"))
        student_scores = {
            row["id"]: float(row["score"] or row["total_score"] or 0)
            for row in results_qs.values("id", "score", "total_score")
        }
        per_student_tasks: dict[int, dict[int, str]] = defaultdict(dict)
        task_agg: dict[int, dict[str, int | float]] = {}

        def _accumulate_task(student_id: int, task_num: int, value: str) -> None:
            per_student_tasks[student_id][task_num] = value
            bucket = task_agg.setdefault(
                task_num, {"total": 0, "correct": 0, "wrong": 0, "blank": 0, "score_sum": 0.0, "score_count": 0}
            )
            bucket["total"] += 1
            if is_blank_token(value):
                bucket["blank"] += 1
            elif is_success_token(value):
                bucket["correct"] += 1
            else:
                bucket["wrong"] += 1
            if str(value or "").strip().isdigit():
                bucket["score_sum"] += float(value)
                bucket["score_count"] += 1

        for row in task_rows_qs:
            _accumulate_task(int(row["student_id"]), int(row["task_number"]), row["value"])

        # Если TaskResult пуст, восстанавливаем маски из протокола ExamResult.
        # Отдельный queryset: .only() нельзя сочетать с select_related("exam").
        if not task_agg:
            mask_qs = ExamResult.objects.filter(
                student__school_id=school_id, exam_id=exam_id
            ).only("id", "student_id", "short_answer_tasks", "long_answer_tasks")
            for er in mask_qs:
                sid = er.student_id
                short_mask = er.short_answer_tasks or ""
                for idx, token in enumerate(short_mask, start=1):
                    _accumulate_task(sid, idx, token)
                    raw_task_rows.append({"task_number": idx, "value": token})
                part2_start = len(short_mask) + 1 if short_mask else part_boundary
                for task_number, token in parse_long_answer_mask(er.long_answer_tasks, part2_start):
                    _accumulate_task(sid, task_number, token)
                    raw_task_rows.append({"task_number": task_number, "value": token})

        task_dict_rows = []
        for task_num in sorted(task_agg):
            row = task_agg[task_num]
            total = int(row["total"])
            correct = int(row["correct"])
            wrong = int(row["wrong"])
            blank = int(row["blank"])
            success_rate = round((correct / total) * 100, 1) if total else 0.0
            task_dict_rows.append(
                {
                    "task_number": task_num,
                    "total": total,
                    "correct": correct,
                    "wrong": wrong,
                    "blank": blank,
                    "success_rate": success_rate,
                }
            )

        valid, validation_details = validate_exam_metrics(
            students_count=students_count,
            avg_score=avg_score,
            median_score=median_score,
            min_score=min_score,
            max_score=max_score,
            pass_count=pass_count,
            fail_count=fail_count,
            score_values=score_values,
            tasks=task_dict_rows,
            raw_task_rows=raw_task_rows,
        )
        if not valid:
            return ExamAnalysisResult(
                valid=False,
                error_message=validation_error_message(validation_details),
                validation_details=validation_details,
            )

        success_rates = [row["success_rate"] for row in task_dict_rows]
        thresholds = dynamic_thresholds(success_rates)
        subject_avg_tasks = round(safe_mean(success_rates), 1)

        task_flags: dict[int, list[int]] = defaultdict(list)
        student_ids_ordered = sorted(student_scores.keys())
        for student_id in student_ids_ordered:
            for task_num in sorted(task_agg):
                value = per_student_tasks.get(student_id, {}).get(task_num)
                task_flags[task_num].append(1 if is_success_token(value) else 0)

        sample_size = len(student_ids_ordered)
        task_analyses: list[TaskAnalysis] = []
        topic_bucket: dict[str, dict] = {}
        skill_bucket: dict[str, dict] = {}
        subject_errors: list[str] = []
        task_success_map = {int(r["task_number"]): float(r["success_rate"]) for r in task_dict_rows}
        task_knowledge_cards: list[dict] = []
        knowledge_by_task: dict[int, object] = {}
        raw_deficits: list[dict] = []

        for row in task_dict_rows:
            task_num = int(row["task_number"])
            knowledge = get_task_knowledge(subject, task_num, exam_type)
            kbase_errors = validate_task_knowledge(subject, exam_type, knowledge)
            if kbase_errors and float(getattr(knowledge, "confidence", 0) or 0) < 0.35:
                subject_errors.extend(kbase_errors)

            if knowledge:
                knowledge_by_task[task_num] = knowledge
                meta_topic = knowledge.topic
                meta_section = knowledge.section
                meta_subsection = knowledge.subsection
                meta_fipi = knowledge.fipi_content_code
                meta_skill = knowledge.skill
                meta_skill_name = knowledge.skill_name
                meta_grades = knowledge.fgos_classes or []
                meta_part = knowledge.exam_part
                meta_max = float(knowledge.max_score) if knowledge.max_score is not None else None
            else:
                meta = get_task_metadata(subject, task_num, exam_type)
                meta_topic = meta.topic
                meta_section = meta.section
                meta_subsection = meta.subsection
                meta_fipi = meta.fipi_code
                meta_skill = meta.skill
                meta_skill_name = meta.skill_name
                meta_grades = meta.grade_range
                meta_part = meta.exam_part
                meta_max = meta.max_score

            # Official catalog overrides: kim.part, theme, school_program, skills
            _cat_rec = _catalog_official_record(subject, task_num, exam_type, 2026)
            if _cat_rec:
                _cat_kim = _cat_rec.get("kim") or {}
                _cat_part = int(_cat_kim.get("part") or 0)
                if _cat_part in (1, 2):
                    meta_part = _cat_part
                _cat_theme = _cat_rec.get("theme") or {}
                _cat_display = str(_cat_theme.get("display_name") or "").strip()
                _cat_block = str(_cat_theme.get("block") or "").strip()
                if _cat_display:
                    meta_topic = _cat_display
                    meta_section = _cat_block or meta_section
                    meta_subsection = _cat_display if _cat_block and _cat_display != _cat_block else meta_subsection
                _cat_prog = _cat_rec.get("school_program") or {}
                _cat_grades = list(_cat_prog.get("grades") or [])
                if _cat_grades:
                    meta_grades = _cat_grades
                _cat_skills = list(_cat_rec.get("skills") or [])
                if _cat_skills and not meta_skill_name:
                    meta_skill_name = _cat_skills[0]

            topic_before_normalize = meta_topic
            meta_topic = topic_for_task(subject, task_num, exam_type)
            if meta_topic != topic_before_normalize:
                meta_section = ""
                meta_subsection = ""

            # Subject-specific skill normalization for final reporting text.
            meta_skill_name = skill_for_task(subject, task_num, exam_type, meta_skill_name or meta_topic)

            topic_errors = validate_topic_belongs_to_subject(subject, exam_type, meta_topic)
            subject_errors.extend(topic_errors)

            total = int(row["total"])
            correct = int(row["correct"])
            wrong = int(row["wrong"])
            blank = int(row["blank"])
            success_rate = float(row["success_rate"])
            flags = task_flags.get(task_num, [])
            scores_aligned = [student_scores[sid] for sid in student_ids_ordered]
            corr = pearson_correlation([float(f) for f in flags], scores_aligned)
            disc = discrimination_index(flags, scores_aligned)
            avg_task_score = None
            score_count = int(task_agg[task_num]["score_count"])
            if score_count:
                avg_task_score = round(float(task_agg[task_num]["score_sum"]) / score_count, 2)

            classification = classify_by_thresholds(success_rate, thresholds)
            task_meta = {}
            if sample_size >= 6 and corr is not None:
                task_meta["score_correlation"] = corr
            if sample_size >= 6 and disc is not None:
                task_meta["discrimination"] = disc
            task_analyses.append(
                TaskAnalysis(
                    task_number=task_num,
                    total=total,
                    correct=correct,
                    wrong=wrong,
                    blank=blank,
                    success_rate=success_rate,
                    error_rate=round((wrong / total) * 100, 1) if total else 0.0,
                    blank_rate=round((blank / total) * 100, 1) if total else 0.0,
                    avg_score=avg_task_score,
                    difficulty=difficulty_index(success_rate),
                    discrimination=disc if disc is not None else 0.0,
                    score_correlation=corr if corr is not None else 0.0,
                    result_contribution=round((corr or 0) * success_rate, 2),
                    classification=classification,
                    topic=meta_topic,
                    section=meta_section,
                    subsection=meta_subsection,
                    fipi_code=meta_fipi,
                    skill=meta_skill,
                    skill_name=meta_skill_name or meta_topic,
                    grade_range=meta_grades,
                    exam_part=meta_part,
                    max_score=meta_max,
                    metadata=task_meta,
                )
            )

            rich_card = build_rich_task_insight(
                knowledge=knowledge,
                task_number=task_num,
                success_rate=success_rate,
                subject_avg=subject_avg_tasks,
                classification=classification,
                subject_name=subject,
                exam_type=exam_type,
            )
            task_knowledge_cards.append(rich_card)

            topic_key = meta_topic[:200]
            tb = topic_bucket.setdefault(
                topic_key,
                {"topic": meta_topic, "section": meta_section, "tasks": [], "correct": 0, "wrong": 0, "total": 0},
            )
            tb["tasks"].append(task_num)
            tb["correct"] += correct
            tb["wrong"] += wrong
            tb["total"] += total

            skill_name = meta_skill_name or meta_topic
            sb = skill_bucket.setdefault(skill_name, {"success": 0, "total": 0, "tasks": []})
            sb["success"] += correct
            sb["total"] += total
            sb["tasks"].append(task_num)

        # Предупреждения базы знаний не блокируют расчёт: метрики по КИМ
        # строятся из ответов учеников; метаданные — вспомогательный слой.
        knowledge_warnings = list(dict.fromkeys(subject_errors))

        topics = []
        for payload in topic_bucket.values():
            total = int(payload["total"])
            success = int(payload["correct"])
            rate = round((success / total) * 100, 1) if total else 0.0
            topics.append(
                TopicAnalysis(
                    topic=payload["topic"],
                    section=payload["section"],
                    task_numbers=sorted(set(payload["tasks"])),
                    success_rate=rate,
                    error_count=int(payload["wrong"]),
                    student_attempts=total,
                )
            )
        topics.sort(key=lambda item: item.success_rate)

        skills = []
        for skill_name, payload in skill_bucket.items():
            total = int(payload["total"])
            success = int(payload["success"])
            rate = round((success / total) * 100, 1) if total else 0.0
            skills.append(
                SkillAnalysis(
                    skill=skill_name,
                    skill_name=skill_name,
                    success_rate=rate,
                    task_numbers=sorted(set(payload["tasks"])),
                    classification=classify_by_thresholds(rate, thresholds),
                )
            )
        skills.sort(key=lambda item: item.success_rate)

        part1_rates = [t.success_rate for t in task_analyses if t.exam_part == 1]
        part2_rates = [t.success_rate for t in task_analyses if t.exam_part == 2]
        part1_success = round(safe_mean(part1_rates), 1) if part1_rates else None
        part2_success = round(safe_mean(part2_rates), 1) if part2_rates else None
        part_gap = round(part1_success - part2_success, 1) if part1_success is not None and part2_success is not None else None

        task_contexts = build_task_contexts(task_analyses, knowledge_by_task, exam_type)
        ctx_by_task = {ctx.task_number: ctx for ctx in task_contexts}
        for task in task_analyses:
            ctx = ctx_by_task.get(task.task_number)
            if ctx:
                task.metadata.update(ctx.metadata)
        topic_graph = build_topic_dependency_graph(task_contexts)
        for ctx in task_contexts:
            if ctx.success_rate < 50:
                raw_deficits.append(
                    build_intelligent_deficit_cause(
                        ctx,
                        subject_name=subject,
                        exam_type=exam_type,
                        topic_graph=topic_graph,
                        task_success_map=task_success_map,
                    )
                )
        merged_deficits = merge_deficits_by_section(raw_deficits)
        thematic_blocks = build_thematic_blocks(task_contexts)
        strength_summary = build_strength_summary(
            task_contexts, subject_name=subject, subject_avg=subject_avg_tasks
        )
        part_narrative = build_part_analysis_narrative(part1_success, part2_success, part_boundary, exam_type)
        class_analysis = build_class_deficit_analysis(task_contexts)
        weak_task_numbers = [t.task_number for t in task_analyses if t.success_rate < 50]
        risk_clusters = build_risk_clusters(per_student_tasks, weak_task_numbers)

        prep_levels = self._build_prep_levels(score_values, pass_rate, exam_type, sk)
        strong_tasks = [t.task_number for t in task_analyses if t.classification == "сильное"]
        weak_tasks = [t.task_number for t in task_analyses if t.classification in {"слабое", "критическое"}]
        critical_tasks = [t.task_number for t in task_analyses if t.classification == "критическое"]

        builder = InsightBuilder()
        insights = [
            builder.task_insight(t, subject_avg_tasks, subject, exam_type, task_success_map)
            for t in task_analyses
            if t.classification in {"слабое", "критическое"}
        ][:8]
        insights.extend(
            builder.topic_insight(t, subject_avg_tasks, subject)
            for t in topics[:5]
            if t.success_rate < subject_avg_tasks
        )
        if part1_success is not None and part2_success is not None:
            insights.append(builder.part_gap_insight(part1_success, part2_success, part_boundary))
        if part_narrative:
            insights.extend(part_narrative[:2])
        for line in strength_summary.get("lines", [])[:2]:
            insights.append(line)

        unified_recs = build_unified_recommendations(
            merged_deficits,
            thematic_blocks,
            strength_summary,
            part_narrative,
            class_analysis,
            subject_name=subject,
        )
        recommendations = []
        for group_lines in unified_recs.values():
            recommendations.extend(group_lines[:4])
        recommendations = recommendations[:12]

        methodical = []
        for block in thematic_blocks[:6]:
            if block["avg_success"] >= subject_avg_tasks:
                continue
            methodical.append(
                builder.methodical_recommendation(
                    topic=f"{block['section']} → {block['subsection']}",
                    task_numbers=block["tasks"],
                    success_rate=block["avg_success"],
                    subject_avg=subject_avg_tasks,
                    grade_range=[],
                    skills=[block["subsection"]],
                )
            )

        correlations = {
            "task_pairs": task_correlation_matrix(task_flags),
            "weak_task_correlations": [
                {
                    "task": t.task_number,
                    "score_correlation": t.metadata.get("score_correlation"),
                    "discrimination": t.metadata.get("discrimination"),
                }
                for t in sorted(task_analyses, key=lambda x: x.success_rate)
                if t.metadata.get("score_correlation") is not None
            ][:6],
        }

        dynamics = self._load_dynamics(
            school_id, exam_type, subject, int(exam.year or exam.exam_date.year),
            current_exam_id=exam_id,
        )

        chart = {
            "labels": [f"№{t.task_number}" for t in task_analyses],
            "success_rates": [t.success_rate for t in task_analyses],
            "minus_counts": [t.wrong for t in task_analyses],
        }

        sections = build_unified_sections(
            subject=subject,
            exam_type=exam_type,
            students_count=students_count,
            avg_score=avg_score,
            median_score=median_score,
            min_score=min_score,
            max_score=max_score,
            pass_rate=pass_rate,
            task_contexts=task_contexts,
            thematic_blocks=thematic_blocks,
            merged_deficits=merged_deficits,
            strength_summary=strength_summary,
            part_narrative=part_narrative,
            class_analysis=class_analysis,
            risk_clusters=risk_clusters,
            insights=insights,
            prep_levels=prep_levels,
            dynamics=dynamics,
            part_boundary=part_boundary,
        )

        control_plan = []
        for item in methodical[:8]:
            control_plan.append(
                {
                    "task": item["tasks"],
                    "block": item["topic"],
                    "severity": "критический" if item["gap_pp"] >= 30 else "значимый",
                    "classes": item["classes"],
                    "action": "; ".join(item["exercises"]),
                }
            )

        return ExamAnalysisResult(
            valid=True,
            subject=subject,
            exam_type=exam_type,
            exam_id=exam_id,
            exam_year=int(exam.year or exam.exam_date.year),
            exam_date=exam.exam_date.strftime("%d.%m.%Y"),
            measure_mode=mode,
            students_count=students_count,
            avg_score=avg_score,
            median_score=median_score,
            min_score=min_score,
            max_score=max_score,
            pass_rate=pass_rate,
            fail_rate=fail_rate,
            tasks=task_analyses,
            topics=topics,
            skills=skills,
            prep_levels=prep_levels,
            part1_success_rate=part1_success,
            part2_success_rate=part2_success,
            part_gap=part_gap,
            strong_tasks=strong_tasks,
            weak_tasks=weak_tasks,
            critical_tasks=critical_tasks,
            insights=insights,
            recommendations=recommendations,
            methodical_recommendations=methodical,
            correlations=correlations,
            dynamics=dynamics,
            sections=sections,
            control_plan=control_plan,
            chart=chart,
            raw={
                "task_knowledge_cards": task_knowledge_cards,
                "deficit_paths": merged_deficits,
                "thematic_blocks": thematic_blocks,
                "strength_summary": strength_summary,
                "part_narrative": part_narrative,
                "class_analysis": class_analysis,
                "risk_clusters": risk_clusters,
                "topic_graph": {
                    k: {
                        "topic": v["topic"],
                        "section": v["section"],
                        "tasks": v["tasks"],
                        "prerequisites": v["prerequisites"][:4],
                        "avg_success": v["avg_success"],
                    }
                    for k, v in list(topic_graph.items())[:30]
                },
                "teacher_recommendations": recommendations[:6],
                "admin_recommendations": [
                    line
                    for lines in unified_recs.values()
                    for line in lines[:2]
                ][:6],
                "knowledge_warnings": knowledge_warnings,
                "unified_recommendations": unified_recs,
            },
            validation_details=knowledge_warnings,
        )

    def analyze_scope(self, scope_filter: dict, year: int | None = None) -> dict:
        from analytics.engine.aggregation import scope_overview

        return scope_overview(scope_filter, year=year)

    def _build_prep_levels(
        self, score_values: list[float], pass_rate: float, exam_type: str, subject_key_value: str
    ) -> list[PrepLevelGroup]:
        if not score_values:
            return []
        is_oge = (exam_type or "").lower() == "oge"
        if is_oge or (max(score_values) <= 5 and min(score_values) >= 2):
            bounds = [
                ("risk", "Группа риска", lambda s: s < 3),
                ("low", "Низкий уровень", lambda s: 3 <= s < 3.5),
                ("basic", "Базовый", lambda s: 3.5 <= s < 4),
                ("good", "Хороший", lambda s: 4 <= s < 5),
                ("high", "Высокий", lambda s: s >= 5),
            ]
        else:
            bounds = [
                ("risk", "Группа риска", lambda s: s < 40),
                ("low", "Низкий уровень", lambda s: 40 <= s < 55),
                ("basic", "Базовый", lambda s: 55 <= s < 70),
                ("good", "Хороший", lambda s: 70 <= s < 85),
                ("high", "Высокий", lambda s: s >= 85),
            ]
        total = len(score_values)
        groups: list[PrepLevelGroup] = []
        for key, label, predicate in bounds:
            bucket = [s for s in score_values if predicate(s)]
            if not bucket:
                continue
            groups.append(
                PrepLevelGroup(
                    key=key,
                    label=label,
                    count=len(bucket),
                    share=round((len(bucket) / total) * 100, 1),
                    avg_score=round(sum(bucket) / len(bucket), 2),
                    pass_rate=pass_rate,
                    weak_tasks=[],
                )
            )
        return groups

    def _load_dynamics(
        self, school_id: int, exam_type: str, subject: str, exam_year: int, *, current_exam_id: int | None = None,
    ) -> list[dict]:
        years = []
        if exam_year >= 2025:
            years = [y for y in (2023, 2024, 2025, 2026) if y <= exam_year][-4:]
        elif exam_year == 2024:
            years = [2023, 2024]
        if not years:
            return []
        base_qs = ExamResult.objects.filter(
            student__school_id=school_id,
            exam__exam_type=exam_type,
            exam__subject=subject,
            exam__year__in=years,
        )
        # For the current year, restrict to the same exam_id to avoid mixing
        # results from multiple exams of the same subject in one year.
        if current_exam_id is not None:
            base_qs = base_qs.exclude(
                exam__year=exam_year,
            ) | ExamResult.objects.filter(
                student__school_id=school_id,
                exam_id=current_exam_id,
            )
        rows = (
            base_qs
            .values("exam__year")
            .annotate(students=Count("id"), avg_score=Avg("score"), passed=Count("id", filter=Q(passed=True)))
            .order_by("exam__year")
        )
        dynamics = []
        for row in rows:
            students = int(row["students"] or 0)
            passed = int(row["passed"] or 0)
            dynamics.append(
                {
                    "year": int(row["exam__year"]),
                    "students": students,
                    "avg_score": round(float(row["avg_score"] or 0), 2),
                    "pass_rate": round((passed / students) * 100, 1) if students else 0.0,
                }
            )
        return dynamics

    def _build_sections(
        self,
        *,
        subject: str,
        exam_type: str,
        students_count: int,
        avg_score: float,
        median_score: float,
        min_score: float,
        max_score: float,
        pass_rate: float,
        task_analyses: list[TaskAnalysis],
        topics: list[TopicAnalysis],
        skills: list[SkillAnalysis],
        insights: list[str],
        part1_success: float | None,
        part2_success: float | None,
        part_boundary: int,
        prep_levels: list[PrepLevelGroup],
        dynamics: list[dict],
    ) -> dict[str, list[str]]:
        task_lines = [
            f"Участников: {students_count}; средний балл: {avg_score}; медиана: {median_score}; "
            f"диапазон: {min_score}–{max_score}; сдаваемость: {pass_rate}%."
        ]
        for task in task_analyses:
            task_lines.append(
                f"№{task.task_number}: успешность {task.success_rate}%, ошибок {task.wrong}, "
                f"пропусков {task.blank}, сложность {task.difficulty}, дискриминация {task.discrimination}, "
                f"корреляция с итоговым баллом {task.score_correlation} ({task.classification})."
            )
        topic_lines = [
            f"«{t.topic[:120]}»: {t.success_rate}% ({', '.join(f'№{n}' for n in t.task_numbers)})."
            for t in topics[:12]
        ] or ["Тематические блоки не выделены."]
        skill_lines = [
            f"{s.skill_name}: {s.success_rate}% ({', '.join(f'№{n}' for n in s.task_numbers[:6])}, {s.classification})."
            for s in skills[:8]
        ] or ["Навыковые блоки не выделены."]
        level_lines = [f"{g.label}: {g.count} чел. ({g.share}%), ср. балл {g.avg_score}." for g in prep_levels]
        dynamics_lines = [
            f"{row['year']}: ср. балл {row['avg_score']}, сдаваемость {row['pass_rate']}%, участников {row['students']}."
            for row in dynamics
        ]
        sections = {
            "Краткие выводы": insights[:5] or [f"Предмет {subject}: средняя успешность по заданиям рассчитана по {students_count} работам."],
            "1. Общие результаты": task_lines[:1],
            "2. Классификация обучающихся": level_lines or ["Недостаточно данных для группировки."],
            "5. Анализ выполнения заданий": task_lines[1:],
            "6. Тематические дефициты (по блокам)": topic_lines,
            "8. Дефициты учебных умений": skill_lines,
            "10. Выводы": insights[:3] or [f"Анализ предмета «{subject}» ({exam_type.upper()}) выполнен по данным протокола."],
        }
        if dynamics_lines:
            sections["3. Динамика результатов по годам"] = dynamics_lines
        if part1_success is not None and part2_success is not None:
            sections["5.1 Анализ частей экзамена"] = [
                f"Часть 1: {part1_success}%; часть 2: {part2_success}%; разрыв {round(part1_success - part2_success, 1)} п.п."
            ]
        return sections
