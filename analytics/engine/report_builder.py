from __future__ import annotations

from analytics.knowledge.graph import priority_label


def build_unified_sections(
    *,
    subject: str,
    exam_type: str,
    students_count: int,
    avg_score: float,
    median_score: float,
    min_score: float,
    max_score: float,
    pass_rate: float,
    task_contexts,
    thematic_blocks: list[dict],
    merged_deficits: list[dict],
    strength_summary: dict,
    part_narrative: list[str],
    class_analysis: dict,
    risk_clusters: list[dict],
    insights: list[str],
    prep_levels: list,
    dynamics: list[dict],
    part_boundary: int,
) -> dict[str, list[str]]:
    exam = exam_type.upper()
    header = (
        f"Предмет «{subject}» ({exam}): участников {students_count}, "
        f"средний балл {avg_score}, медиана {median_score}, "
        f"диапазон {min_score}–{max_score}, сдаваемость {pass_rate}%."
    )

    task_lines = [header]
    for ctx in task_contexts:
        meta = ctx.metadata or {}
        fgos = meta.get("fgos") or {}
        fgos_text = ""
        if fgos.get("studied"):
            fgos_text = f" Изучается: {fgos['studied']}; закрепляется: {fgos.get('reinforced', '—')}; проверяется: {fgos.get('exam', exam)}."
        corr = meta.get("score_correlation")
        disc = meta.get("discrimination")
        stats_bits = [f"успешность {ctx.success_rate}%", f"{priority_label(ctx.priority)}"]
        if corr is not None:
            stats_bits.append(f"корреляция с итоговым баллом {corr}")
        if disc is not None:
            stats_bits.append(f"дискриминация {disc}")
        path = " → ".join(filter(None, [ctx.section, ctx.subsection, ctx.topic[:80]]))
        task_lines.append(
            f"№{ctx.task_number}: {path or ctx.topic[:80]}. "
            f"Умение: {ctx.skill_name[:80]}.{fgos_text} "
            + "; ".join(stats_bits)
            + f". Источник: {meta.get('source', 'ФИПИ')}."
        )

    block_lines = []
    for block in thematic_blocks[:10]:
        tasks_label = ", ".join(f"№{n}" for n in block["tasks"][:10])
        block_lines.append(
            f"{block['priority_label']} {block['section']} → {block['subsection']}: "
            f"средняя успешность {block['avg_success']}% (задания {tasks_label})."
        )

    deficit_lines = []
    for item in merged_deficits[:8]:
        deficit_lines.append(f"{item['priority_label']} {item['cause']}")

    strength_lines = list(strength_summary.get("lines") or [])
    if not strength_lines:
        strength_lines = ["Сильные стороны не выделены — все задания ниже 75% успешности."]

    level_lines = [f"{g.label}: {g.count} чел. ({g.share}%), ср. балл {g.avg_score}." for g in prep_levels]
    dynamics_lines = [
        f"{row['year']}: ср. балл {row['avg_score']}, сдаваемость {row['pass_rate']}%, участников {row['students']}."
        for row in dynamics
    ]
    risk_lines = [c["label"] + f" — {c['students_count']} чел." for c in risk_clusters[:6]]
    class_lines = list(class_analysis.get("lines") or [])

    sections = {
        "Краткие выводы": (insights[:5] or [header])[:6],
        "1. Общие результаты": [header],
        "2. Классификация обучающихся": level_lines or ["Недостаточно данных для группировки."],
        "4. Сильные стороны": strength_lines,
        "5. Анализ выполнения заданий": task_lines[1:],
        "5.1 Анализ частей экзамена": part_narrative or ["Части экзамена не разделены в протоколе."],
        "6. Тематические блоки": block_lines or ["Тематические блоки не выделены."],
        "6.1 Причины дефицитов": deficit_lines or ["Критических дефицитов не выявлено."],
        "7. Анализ классов программы": class_lines or ["Классы программы по дефицитам не определены."],
        "8. Группы риска": risk_lines or ["Одинаковые профили дефицитов не выявлены."],
        "10. Выводы": (insights[:3] or [f"Анализ предмета «{subject}» ({exam}) выполнен по данным протокола и базе ФИПИ."])[:5],
    }
    if dynamics_lines:
        sections["3. Динамика результатов по годам"] = dynamics_lines
    return sections


def build_unified_recommendations(
    merged_deficits: list[dict],
    thematic_blocks: list[dict],
    strength_summary: dict,
    part_narrative: list[str],
    class_analysis: dict,
    *,
    subject_name: str,
) -> dict[str, list[str]]:
    recs: dict[str, list[str]] = {
        "Приоритетные дефициты": [],
        "Тематические блоки": [],
        "Сильные стороны": [],
        "Части экзамена": [],
        "Классы программы": [],
    }
    for item in merged_deficits[:6]:
        tasks = item.get("tasks_label") or ", ".join(f"№{n}" for n in item.get("task_numbers", []))
        recs["Приоритетные дефициты"].append(
            f"{item['priority_label']} Блок «{item.get('section') or item.get('topic', '')[:50]}» "
            f"(задания {tasks}, {item.get('success_rate', 0)}%): "
            + "; ".join(item.get("prerequisites", [])[:3])
            + ". План: "
            + " → ".join(item.get("remediation_path", [])[:4])
        )
    for block in thematic_blocks:
        if block["avg_success"] >= 60:
            continue
        recs["Тематические блоки"].append(
            f"{block['priority_label']} {block['section']} → {block['subsection']}: "
            f"отработать задания {', '.join(f'№{n}' for n in block['tasks'][:8])}."
        )
    for line in strength_summary.get("lines", [])[:2]:
        recs["Сильные стороны"].append(line)
    for line in part_narrative[1:]:
        recs["Части экзамена"].append(line)
    for line in class_analysis.get("lines", []):
        recs["Классы программы"].append(line)
    return {k: v for k, v in recs.items() if v}
