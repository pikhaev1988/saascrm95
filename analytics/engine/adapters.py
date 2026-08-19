from __future__ import annotations


def _task_row_payload(task) -> dict:
    meta = getattr(task, "metadata", {}) or {}
    fgos = meta.get("fgos") or {}
    return {
        "task_number": task.task_number,
        "success_rate": task.success_rate,
        "plus": task.correct,
        "minus": task.wrong,
        "total": task.total,
        "classification": task.classification,
        "topic": task.topic,
        "section": task.section,
        "subsection": task.subsection,
        "skill_name": task.skill_name,
        "fipi_code": task.fipi_code,
        "grade_range": task.grade_range,
        "exam_part": task.exam_part,
        "difficulty": task.difficulty,
        "fgos_studied": fgos.get("studied", ""),
        "fgos_reinforced": fgos.get("reinforced", ""),
        "fgos_exam": fgos.get("exam", ""),
        "source": meta.get("source", ""),
        "task_type": meta.get("task_type", ""),
        "max_score": meta.get("max_score"),
        "score_correlation": meta.get("score_correlation"),
        "discrimination": meta.get("discrimination"),
    }


def to_legacy_payload(result) -> dict:
    from analytics.engine.result import ExamAnalysisResult

    if not isinstance(result, ExamAnalysisResult) or not result.valid:
        return {
            "sections": {"Ошибка": [result.error_message or "Аналитика не построена."]},
            "recommendations": {},
            "control_plan": [],
        }

    unified = result.raw.get("unified_recommendations") or {}
    recommendations = unified or {
        "Задания": result.recommendations[:3],
        "Темы": [line for line in result.sections.get("6. Тематические блоки", [])[:3]],
        "Навыки": [line for line in result.sections.get("8. Дефициты учебных умений", [])[:3]],
        "Сильные стороны": result.sections.get("4. Сильные стороны", [])[:3],
        "Части экзамена": result.sections.get("5.1 Анализ частей экзамена", [])[:2],
        "Экзаменационная стратегия": [
            f"Контроль разрыва частей экзамена: {result.part_gap} п.п."
            if result.part_gap is not None
            else "Контроль динамики по ключевым заданиям протокола."
        ],
    }
    return {
        "sections": result.sections,
        "recommendations": recommendations,
        "control_plan": result.control_plan,
    }


def to_dashboard_analysis(result) -> dict | None:
    from analytics.engine.result import ExamAnalysisResult

    if not isinstance(result, ExamAnalysisResult):
        return None
    if not result.valid:
        return {"error": result.error_message, "valid": False}

    raw = result.raw or {}
    return {
        "valid": True,
        "students_count": result.students_count,
        "avg_score": result.avg_score,
        "median_score": result.median_score,
        "min_score": result.min_score,
        "max_score": result.max_score,
        "pass_rate": result.pass_rate,
        "task_rows": [_task_row_payload(t) for t in result.tasks],
        "recommendations": result.recommendations,
        "insights": result.insights,
        "topics": [
            {"topic": t.topic, "section": t.section, "success_rate": t.success_rate, "tasks": t.task_numbers}
            for t in result.topics
        ],
        "skills": [
            {"skill": s.skill_name, "success_rate": s.success_rate, "tasks": s.task_numbers}
            for s in result.skills
        ],
        "prep_levels": [
            {"label": g.label, "count": g.count, "share": g.share, "avg_score": g.avg_score}
            for g in result.prep_levels
        ],
        "part1_success_rate": result.part1_success_rate,
        "part2_success_rate": result.part2_success_rate,
        "part_gap": result.part_gap,
        "part_narrative": raw.get("part_narrative", []),
        "correlations": result.correlations,
        "chart": {
            **(result.chart or {}),
            "minus_counts": (result.chart or {}).get("minus_counts")
            or (result.chart or {}).get("error_counts")
            or [t.wrong for t in result.tasks],
            "labels": (result.chart or {}).get("labels") or [f"№{t.task_number}" for t in result.tasks],
            "success_rates": (result.chart or {}).get("success_rates") or [t.success_rate for t in result.tasks],
        },
        "control_plan": result.control_plan,
        "sections": result.sections,
        "thematic_blocks": raw.get("thematic_blocks", []),
        "strength_summary": raw.get("strength_summary", {}),
        "class_analysis": raw.get("class_analysis", {}),
        "risk_clusters": raw.get("risk_clusters", []),
        "topic_graph": raw.get("topic_graph", {}),
        "task_knowledge_cards": raw.get("task_knowledge_cards", []),
        "deficit_paths": raw.get("deficit_paths", []),
        "teacher_recommendations": raw.get("teacher_recommendations", []),
        "admin_recommendations": raw.get("admin_recommendations", []),
        "unified_recommendations": raw.get("unified_recommendations", {}),
        "strong_tasks": result.strong_tasks,
        "weak_tasks": result.weak_tasks,
        "critical_tasks": result.critical_tasks,
    }
