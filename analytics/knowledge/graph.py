from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from analytics.knowledge.parser import format_grade_label
from analytics.knowledge_models import TaskKnowledge


PRIORITY_LABELS = {
    "critical": ("🔴", "Критический"),
    "high": ("🟠", "Высокий"),
    "medium": ("🟡", "Средний"),
    "minor": ("🟢", "Незначительный"),
}


def priority_tier(success_rate: float, classification: str = "") -> str:
    if success_rate <= 25 or classification == "критическое":
        return "critical"
    if success_rate <= 45 or classification == "слабое":
        return "high"
    if success_rate <= 60 or classification == "среднее":
        return "medium"
    return "minor"


def priority_label(tier: str) -> str:
    emoji, label = PRIORITY_LABELS.get(tier, ("", tier))
    return f"{emoji} {label}".strip()


def source_label(knowledge: TaskKnowledge | None) -> str:
    if not knowledge:
        return "ФИПИ · спецификация"
    source = (knowledge.source_document or "ФИПИ").strip()
    year = knowledge.document_version or str(knowledge.document_year or "")
    if "enriched" in source.lower() or "school_program" in source.lower():
        doc = "Кодификатор / спецификатор"
    elif "oge" in source.lower():
        doc = "Спецификатор ОГЭ"
    else:
        doc = "Спецификатор"
    return f"{doc} · {year}"


def fgos_labels(knowledge: TaskKnowledge | None, exam_type: str) -> dict[str, str]:
    if not knowledge:
        return {}
    grades = format_grade_label(
        knowledge.fgos_class_start,
        knowledge.fgos_class_repeat or [],
        exam_type,
    )
    return {
        "studied": grades["studied"],
        "reinforced": grades["reinforced"],
        "exam": grades["exam"],
    }


def task_type_label(knowledge: TaskKnowledge | None, exam_part: int) -> str:
    if knowledge and knowledge.raw_payload:
        raw_type = str(knowledge.raw_payload.get("task_type") or "").strip()
        if raw_type:
            return raw_type
    return "Развёрнутый ответ" if exam_part == 2 else "Краткий ответ"


@dataclass
class TaskContext:
    task_number: int
    success_rate: float
    classification: str
    topic: str
    section: str
    subsection: str
    skill_name: str
    grade_range: list[int]
    exam_part: int
    knowledge: TaskKnowledge | None = None
    priority: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.priority:
            self.priority = priority_tier(self.success_rate, self.classification)


def build_task_contexts(
    task_analyses,
    knowledge_by_task: dict[int, TaskKnowledge | None],
    exam_type: str = "ege",
) -> list[TaskContext]:
    contexts: list[TaskContext] = []
    for task in task_analyses:
        knowledge = knowledge_by_task.get(task.task_number)
        contexts.append(
            TaskContext(
                task_number=task.task_number,
                success_rate=task.success_rate,
                classification=task.classification,
                topic=task.topic,
                section=task.section or (knowledge.section if knowledge else ""),
                subsection=task.subsection or (knowledge.subsection if knowledge else ""),
                skill_name=task.skill_name or task.topic,
                grade_range=list(task.grade_range or []),
                exam_part=task.exam_part,
                knowledge=knowledge,
                metadata={
                    "fipi_code": task.fipi_code,
                    "source": source_label(knowledge),
                    "fgos": fgos_labels(knowledge, knowledge.exam_type if knowledge else exam_type),
                    "task_type": task_type_label(knowledge, task.exam_part),
                    "max_score": float(task.max_score) if task.max_score is not None else None,
                    "score_correlation": task.metadata.get("score_correlation"),
                    "discrimination": task.metadata.get("discrimination"),
                },
            )
        )
    return contexts


def build_topic_dependency_graph(contexts: list[TaskContext]) -> dict[str, dict]:
    """Граф: тема → задания, где она проверяется; тема → базовые темы."""
    by_topic: dict[str, dict] = {}
    for ctx in contexts:
        key = ctx.topic[:200]
        node = by_topic.setdefault(
            key,
            {
                "topic": ctx.topic,
                "section": ctx.section,
                "subsection": ctx.subsection,
                "tasks": [],
                "prerequisites": [],
                "dependents": [],
                "avg_success": 0.0,
            },
        )
        node["tasks"].append(ctx.task_number)
        if ctx.knowledge:
            for prev in (ctx.knowledge.previous_topics or [])[-4:]:
                if prev and prev not in node["prerequisites"]:
                    node["prerequisites"].append(prev)
            for nxt in (ctx.knowledge.next_topics or [])[:4]:
                if nxt and nxt not in node["dependents"]:
                    node["dependents"].append(nxt)

    for node in by_topic.values():
        rates = [
            ctx.success_rate
            for ctx in contexts
            if ctx.task_number in node["tasks"]
        ]
        node["avg_success"] = round(sum(rates) / len(rates), 1) if rates else 0.0
        node["tasks"] = sorted(set(node["tasks"]))
    return by_topic


def build_intelligent_deficit_cause(
    ctx: TaskContext,
    *,
    subject_name: str,
    exam_type: str,
    topic_graph: dict[str, dict],
    task_success_map: dict[int, float],
) -> dict:
    if ctx.success_rate >= 50:
        return {"cause": "", "prerequisites": [], "priority": ctx.priority}

    exam = "ОГЭ" if exam_type == "oge" else "ЕГЭ"
    subject = subject_name.strip() or "предмет"
    node = topic_graph.get(ctx.topic[:200], {})
    prerequisites = list(node.get("prerequisites") or [])

    weak_prereqs = []
    for prereq in prerequisites:
        for other_key, other_node in topic_graph.items():
            if prereq in (other_node.get("topic"), other_key) or prereq in other_node.get("prerequisites", []):
                if other_node.get("avg_success", 100) < 55:
                    weak_prereqs.append(prereq[:100])
                    break
        else:
            weak_prereqs.append(prereq[:100])

    weak_prereqs = list(dict.fromkeys(weak_prereqs))[:4]
    base_topic = prerequisites[-1][:100] if prerequisites else (ctx.subsection or ctx.section or ctx.topic[:80])

    # Confirmed deficit: only state facts, avoid false causal claims
    lines = [
        f"{exam}, {subject}: задание №{ctx.task_number} — успешность {ctx.success_rate}%. "
        f"Тема: «{ctx.topic[:80]}»."
    ]
    if weak_prereqs:
        bullets = " • ".join(f"«{t}»" for t in weak_prereqs)
        lines.append(f"Вероятный дефицит связан с базовыми темами: {bullets}. Требует дополнительной диагностики.")
    elif base_topic and base_topic.lower() not in ctx.topic.lower():
        lines.append(
            f"Для уточнения причины рекомендуется проверить освоение темы «{base_topic}»."
        )

    related = []
    if ctx.knowledge and ctx.knowledge.related_tasks:
        related = [f"№{n}" for n in ctx.knowledge.related_tasks[:6]]
    elif node.get("tasks"):
        related = [f"№{n}" for n in node["tasks"] if n != ctx.task_number][:6]

    return {
        "cause": " ".join(lines),
        "prerequisites": weak_prereqs or prerequisites[:4],
        "related_tasks": related,
        "priority": ctx.priority,
        "priority_label": priority_label(ctx.priority),
        "topic": ctx.topic,
        "section": ctx.section,
        "subsection": ctx.subsection,
        "task_numbers": [ctx.task_number],
        "success_rate": ctx.success_rate,
        "remediation_path": (weak_prereqs or prerequisites[:3])
        + [ctx.topic, f"Контрольная работа по {subject}", "Повторная диагностика КИМ"],
        "source": ctx.metadata.get("source", source_label(ctx.knowledge)),
        "fgos": ctx.metadata.get("fgos", {}),
        "skill_name": ctx.skill_name,
    }


def merge_deficits_by_section(deficits: list[dict]) -> list[dict]:
    """Объединить дефициты одного раздела / подраздела."""
    buckets: dict[str, dict] = {}
    for item in deficits:
        if not item.get("cause"):
            continue
        key = "|".join(filter(None, [item.get("section", ""), item.get("subsection", "")])) or item.get("topic", "")[:80]
        bucket = buckets.setdefault(
            key,
            {
                "section": item.get("section", ""),
                "subsection": item.get("subsection", ""),
                "topic": item.get("topic", ""),
                "task_numbers": [],
                "success_rates": [],
                "causes": [],
                "prerequisites": [],
                "remediation_path": [],
                "priority": "minor",
                "priority_label": priority_label("minor"),
                "source": item.get("source", ""),
                "fgos": item.get("fgos", {}),
                "skill_name": item.get("skill_name", ""),
                "related_tasks": [],
            },
        )
        bucket["task_numbers"].extend(item.get("task_numbers") or [])
        bucket["success_rates"].append(float(item.get("success_rate") or 0))
        if item.get("cause") and item["cause"] not in bucket["causes"]:
            bucket["causes"].append(item["cause"])
        for p in item.get("prerequisites") or []:
            if p not in bucket["prerequisites"]:
                bucket["prerequisites"].append(p)
        for step in item.get("remediation_path") or []:
            if step not in bucket["remediation_path"]:
                bucket["remediation_path"].append(step)
        for rel in item.get("related_tasks") or []:
            if rel not in bucket["related_tasks"]:
                bucket["related_tasks"].append(rel)
        tier_order = {"critical": 0, "high": 1, "medium": 2, "minor": 3}
        if tier_order.get(item.get("priority", "minor"), 3) < tier_order.get(bucket["priority"], 3):
            bucket["priority"] = item["priority"]
            bucket["priority_label"] = item.get("priority_label") or priority_label(item["priority"])

    merged: list[dict] = []
    for bucket in buckets.values():
        tasks = sorted(set(bucket["task_numbers"]))
        avg_rate = round(sum(bucket["success_rates"]) / len(bucket["success_rates"]), 1) if bucket["success_rates"] else 0
        tasks_label = ", ".join(f"№{n}" for n in tasks)
        section_path = " → ".join(filter(None, [bucket["section"], bucket["subsection"], bucket["topic"][:60]]))
        merged.append(
            {
                **bucket,
                "task_numbers": tasks,
                "success_rate": avg_rate,
                "cause": bucket["causes"][0] if len(bucket["causes"]) == 1 else (
                    f"Дефициты по блоку «{section_path or bucket['topic'][:60]}» "
                    f"(задания {tasks_label}, средняя успешность {avg_rate}%): "
                    + " ".join(bucket["prerequisites"][:3])
                ),
                "tasks_label": tasks_label,
            }
        )
    merged.sort(key=lambda x: ({"critical": 0, "high": 1, "medium": 2, "minor": 3}.get(x["priority"], 3), x["success_rate"]))
    return merged


def build_thematic_blocks(contexts: list[TaskContext]) -> list[dict]:
    blocks: dict[str, dict] = {}
    for ctx in contexts:
        section = ctx.section or "Общий раздел"
        subsection = ctx.subsection or ctx.topic[:60]
        key = f"{section}|{subsection}"
        block = blocks.setdefault(
            key,
            {
                "section": section,
                "subsection": subsection,
                "topics": [],
                "tasks": [],
                "success_rates": [],
                "deficits": [],
                "strengths": [],
            },
        )
        if ctx.topic not in block["topics"]:
            block["topics"].append(ctx.topic)
        block["tasks"].append(ctx.task_number)
        block["success_rates"].append(ctx.success_rate)
        if ctx.success_rate < 50:
            block["deficits"].append(ctx.task_number)
        elif ctx.success_rate >= 75:
            block["strengths"].append(ctx.task_number)

    result = []
    for block in blocks.values():
        avg = round(sum(block["success_rates"]) / len(block["success_rates"]), 1) if block["success_rates"] else 0
        result.append(
            {
                **block,
                "tasks": sorted(set(block["tasks"])),
                "avg_success": avg,
                "priority": priority_tier(avg),
                "priority_label": priority_label(priority_tier(avg)),
            }
        )
    result.sort(key=lambda x: x["avg_success"])
    return result


def build_strength_summary(
    contexts: list[TaskContext],
    *,
    subject_name: str,
    subject_avg: float,
) -> dict:
    strong_ctxs = [c for c in contexts if c.classification == "сильное" or c.success_rate >= 75]
    strong_ctxs.sort(key=lambda x: -x.success_rate)
    strong_tasks = [c for c in contexts if c.success_rate >= 70]
    strong_tasks.sort(key=lambda x: -x.success_rate)

    # Deduplicate topics: group by topic name, aggregate tasks and avg rate
    topic_groups: dict[str, dict] = {}
    for c in strong_ctxs:
        key = c.topic[:200]
        grp = topic_groups.setdefault(key, {"topic": c.topic, "tasks": [], "rates": []})
        grp["tasks"].append(c.task_number)
        grp["rates"].append(c.success_rate)
    deduped_topics = []
    for grp in topic_groups.values():
        avg_rate = round(sum(grp["rates"]) / len(grp["rates"]), 1)
        deduped_topics.append({
            "topic": grp["topic"],
            "success_rate": avg_rate,
            "tasks": sorted(set(grp["tasks"])),
        })
    deduped_topics.sort(key=lambda x: -x["success_rate"])

    skill_rates: dict[str, list[float]] = defaultdict(list)
    for ctx in contexts:
        skill_rates[ctx.skill_name].append(ctx.success_rate)
    strong_skills = sorted(
        [
            {"skill": name, "success_rate": round(sum(rates) / len(rates), 1)}
            for name, rates in skill_rates.items()
            if sum(rates) / len(rates) >= subject_avg
        ],
        key=lambda x: -x["success_rate"],
    )[:5]

    lines = []
    if deduped_topics:
        lines.append(
            "Лучше всего освоены темы: "
            + "; ".join(
                f"«{t['topic'][:60]}» ({t['success_rate']}%, задания {', '.join(f'№{n}' for n in t['tasks'][:6])})"
                for t in deduped_topics[:5]
            )
            + "."
        )
    if strong_tasks:
        lines.append(
            "Лучше всего выполнены задания: "
            + ", ".join(f"№{c.task_number} ({c.success_rate}%)" for c in strong_tasks[:6])
            + "."
        )
    if strong_skills:
        lines.append(
            f"Сильные компетенции школы по предмету «{subject_name}»: "
            + "; ".join(f"«{s['skill'][:50]}» ({s['success_rate']}%)" for s in strong_skills[:4])
            + "."
        )
    return {
        "lines": lines,
        "topics": deduped_topics[:8],
        "tasks": [{"task_number": c.task_number, "success_rate": c.success_rate, "topic": c.topic} for c in strong_tasks[:8]],
        "skills": strong_skills,
    }


def build_part_analysis_narrative(
    part1_success: float | None,
    part2_success: float | None,
    part_boundary: int,
    exam_type: str,
) -> list[str]:
    if part1_success is None or part2_success is None:
        return []
    exam = "ОГЭ" if exam_type == "oge" else "ЕГЭ"
    gap = round(part1_success - part2_success, 1)
    lines = [
        f"Часть 1 (задания 1–{part_boundary - 1}): {part1_success}%; "
        f"часть 2 (задания {part_boundary}+): {part2_success}%; разрыв {gap} п.п."
    ]
    if part1_success >= 80 and part2_success <= 30:
        lines.append(
            f"Подготовка по {exam} ориентирована преимущественно на базовый уровень. "
            "Высокий уровень сложности (вторая часть) не сформирован."
        )
    elif part2_success > part1_success + 15:
        lines.append("Вторая часть выполняется лучше первой — возможен перекос в пользу развёрнутых заданий.")
    elif gap >= 25:
        lines.append("Существенный разрыв между частями: требуется системная работа над заданиями повышенной сложности.")
    return lines


def build_class_deficit_analysis(contexts: list[TaskContext]) -> dict:
    weak = [c for c in contexts if c.success_rate < 50]
    grade_counter: Counter[int] = Counter()
    for ctx in weak:
        if ctx.knowledge and ctx.knowledge.fgos_class_start:
            grade_counter[int(ctx.knowledge.fgos_class_start)] += 1
        elif ctx.grade_range:
            grade_counter[int(min(ctx.grade_range))] += 1

    if not grade_counter:
        return {"summary": "", "dominant_grade": None, "lines": []}

    dominant = grade_counter.most_common(1)[0][0]
    lines = [
        f"Большинство дефицитов связано с темами программы {dominant} класса "
        f"({grade_counter[dominant]} из {len(weak)} проблемных заданий)."
    ]
    if dominant <= 9:
        lines.append(
            f"Рекомендуется начать повторение с программы {dominant} класса и последовательно "
            "наращивать сложность к требованиям КИМ."
        )
    else:
        lines.append(
            f"Повторение целесообразно начинать с материала {dominant} класса "
            "с опорой на кодификатор ФИПИ."
        )
    return {
        "summary": lines[0],
        "dominant_grade": dominant,
        "lines": lines,
        "grade_distribution": dict(sorted(grade_counter.items())),
    }


def build_risk_clusters(
    per_student_tasks: dict[int, dict[int, str]],
    weak_task_numbers: list[int],
) -> list[dict]:
    from analytics.engine.tokens import is_success_token

    if not weak_task_numbers or not per_student_tasks:
        return []

    profiles: dict[tuple, list[int]] = defaultdict(list)
    for student_id, tasks in per_student_tasks.items():
        failed = tuple(sorted(n for n in weak_task_numbers if not is_success_token(tasks.get(n))))
        if failed:
            profiles[failed].append(student_id)

    clusters = []
    for failed_tasks, student_ids in sorted(profiles.items(), key=lambda x: -len(x[1])):
        if len(student_ids) < 1:
            continue
        clusters.append(
            {
                "failed_tasks": list(failed_tasks),
                "tasks_label": ", ".join(f"№{n}" for n in failed_tasks),
                "students_count": len(student_ids),
                "label": f"Группа риска: ошибки в заданиях {', '.join(f'№{n}' for n in failed_tasks[:6])}",
            }
        )
    return clusters[:8]
