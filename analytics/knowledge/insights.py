from __future__ import annotations

from analytics.knowledge.parser import format_grade_label
from analytics.knowledge_models import TaskKnowledge
from users.task_topics import default_skill_profile


def _exam_label(exam_type: str) -> str:
    return "ОГЭ" if (exam_type or "").lower() == "oge" else "ЕГЭ"


def _subject_label(subject_name: str) -> str:
    return (subject_name or "предмет").strip()


def knowledge_to_dict(knowledge: TaskKnowledge | None) -> dict:
    if not knowledge:
        return {}
    grades = format_grade_label(
        knowledge.fgos_class_start,
        knowledge.fgos_class_repeat or [],
        knowledge.exam_type,
    )
    return {
        "task_number": knowledge.task_number,
        "topic": knowledge.topic,
        "section": knowledge.section,
        "subsection": knowledge.subsection,
        "subtopic": knowledge.subtopic,
        "fgos_class_start": knowledge.fgos_class_start,
        "fgos_class_repeat": knowledge.fgos_class_repeat,
        "fgos_classes": knowledge.fgos_classes,
        "fgos_studied_label": grades["studied"],
        "fgos_reinforced_label": grades["reinforced"],
        "fgos_exam_label": grades["exam"],
        "fipi_content_code": knowledge.fipi_content_code,
        "requirement_code": knowledge.requirement_code,
        "skill": knowledge.skill,
        "skill_name": knowledge.skill_name,
        "competency": knowledge.competency,
        "difficulty": knowledge.difficulty,
        "exam_part": knowledge.exam_part,
        "max_score": float(knowledge.max_score) if knowledge.max_score is not None else None,
        "related_tasks": knowledge.related_tasks or [],
        "previous_topics": knowledge.previous_topics or [],
        "next_topics": knowledge.next_topics or [],
        "source_document": knowledge.source_document,
        "confidence": float(knowledge.confidence or 0),
    }


def build_rich_task_insight(
    *,
    knowledge: TaskKnowledge | None,
    task_number: int,
    success_rate: float,
    subject_avg: float,
    classification: str,
    subject_name: str = "",
    exam_type: str = "ege",
) -> dict:
    delta = round(subject_avg - success_rate, 1)
    meta = knowledge_to_dict(knowledge)
    subject = _subject_label(subject_name)
    exam = _exam_label(exam_type)
    topic = meta.get("topic") or f"Задание №{task_number}"
    skill = meta.get("skill_name") or meta.get("competency") or ""
    if not skill and subject_name:
        profile = default_skill_profile(subject_name, exam_type)
        skill = profile[0] if profile else ""

    lines = [
        f"{exam}, {subject} — задание №{task_number}",
        f"Тема: {topic}",
    ]
    if meta.get("section"):
        lines.append(f"Раздел ({subject}): {meta['section']}")
    if meta.get("subsection"):
        lines.append(f"Подраздел: {meta['subsection']}")
    if meta.get("fgos_studied_label"):
        lines.append(f"Изучается: {meta['fgos_studied_label']}")
    if meta.get("fgos_reinforced_label"):
        lines.append(f"Закрепляется: {meta['fgos_reinforced_label']}")
    if meta.get("fgos_exam_label"):
        lines.append(f"Проверяется: {meta['fgos_exam_label']}")
    if meta.get("difficulty"):
        lines.append(f"Уровень сложности: {meta['difficulty'].capitalize()}")
    if meta.get("max_score"):
        lines.append(f"Максимальный балл: {meta['max_score']}")
    if skill:
        lines.append(f"Проверяемое умение ({subject}): {skill}.")
    lines.extend(
        [
            f"Успешность по предмету «{subject}»: {success_rate}%",
            f"Средняя успешность предмета: {subject_avg}%",
            f"Отклонение: {delta:+.1f} п.п.",
            f"Классификация: {classification}",
        ]
    )
    if meta.get("related_tasks"):
        related = ", ".join(f"№{n}" for n in meta["related_tasks"][:6])
        lines.append(f"Связанные задания КИМ ({subject}): {related}")

    return {"summary": lines, "meta": meta, "delta_pp": delta}


def build_deficit_analysis(
    *,
    knowledge: TaskKnowledge | None,
    task_number: int,
    success_rate: float,
    task_success_map: dict[int, float],
    subject_name: str = "",
    exam_type: str = "ege",
) -> dict:
    if success_rate >= 50 or not knowledge:
        return {"cause": "", "remediation_path": [], "control_plan": []}

    subject = _subject_label(subject_name)
    exam = _exam_label(exam_type)

    weak_prerequisites = []
    for topic in (knowledge.previous_topics or [])[-4:]:
        weak_prerequisites.append(topic)

    cause = ""
    if weak_prerequisites:
        bullets = "; ".join(f"«{t[:80]}»" for t in weak_prerequisites[:4])
        cause = (
            f"{exam}, {subject}: низкая успешность задания №{task_number} ({success_rate}%) "
            f"обусловлена недостаточным освоением тем программы по предмету «{subject}»: {bullets}. "
            f"Без устранения данных дефицитов успешное выполнение задания №{task_number} маловероятно."
        )
    else:
        cause = (
            f"{exam}, {subject}: низкая успешность задания №{task_number} ({success_rate}%) "
            f"по теме «{knowledge.topic[:100]}» — требуется адресная отработка содержания предмета."
        )

    path = list(weak_prerequisites)
    path.append(knowledge.topic)
    path.extend([f"Контрольная работа по {subject}", "Повторная диагностика КИМ"])
    expected = min(35, max(10, int(round((50 - success_rate) / 2))))
    path.append(f"Ожидаемый прирост по предмету «{subject}»: +{expected}%")

    control = []
    if knowledge.fgos_class_start:
        control.append(
            f"{knowledge.fgos_class_start} класс ({subject}) — повторить тему «{knowledge.topic[:60]}»"
        )
    if knowledge.fgos_class_repeat:
        repeat = knowledge.fgos_class_repeat[-1]
        control.append(f"{repeat} класс ({subject}) — закрепить, решить задания КИМ №{task_number}")
    control.append(f"Провести диагностику по предмету «{subject}» по связанным заданиям")
    if knowledge.related_tasks:
        control.append(
            f"Отработать связанные задания ({subject}): "
            + ", ".join(f"№{n}" for n in knowledge.related_tasks[:5])
        )

    return {
        "cause": cause,
        "remediation_path": path,
        "control_plan": control,
        "expected_growth": expected,
    }


def build_teacher_recommendations(
    knowledge: TaskKnowledge | None,
    success_rate: float,
    delta: float,
    *,
    subject_name: str = "",
    exam_type: str = "ege",
) -> list[str]:
    if not knowledge or success_rate >= 60:
        return []
    subject = _subject_label(subject_name)
    exam = _exam_label(exam_type)
    hours = max(2, min(12, int(round(abs(delta) / 4)) or 2))
    recs = [
        f"{exam}, {subject}: выделить {hours} академических часа на повторение темы "
        f"«{knowledge.topic[:100]}» (задание №{knowledge.task_number}, успешность {success_rate}%)."
    ]
    if knowledge.previous_topics:
        recs.append(
            f"По предмету «{subject}» повторить базовые темы: "
            + "; ".join(t[:60] for t in knowledge.previous_topics[-3:])
            + "."
        )
    if knowledge.related_tasks:
        recs.append(
            f"Провести серию заданий КИМ по {subject}: "
            + ", ".join(f"№{n}" for n in knowledge.related_tasks[:5])
            + "."
        )
    profile = default_skill_profile(subject_name, exam_type)
    if profile:
        recs.append(
            f"Сфокусироваться на ключевых умениях предмета «{subject}»: {', '.join(profile[:2])}."
        )
    return recs


def build_admin_recommendations(
    knowledge: TaskKnowledge | None,
    success_rate: float,
    students_count: int,
    *,
    subject_name: str = "",
    exam_type: str = "ege",
) -> list[str]:
    if not knowledge or success_rate >= 50:
        return []
    subject = _subject_label(subject_name)
    exam = _exam_label(exam_type)
    return [
        f"{exam}, {subject}: задание №{knowledge.task_number} («{knowledge.topic[:80]}») — "
        f"успешность {success_rate}% при {students_count} участниках. "
        f"Требуется адресная поддержка педагогов "
        f"{'класса ' + str(knowledge.fgos_class_start) if knowledge.fgos_class_start else 'предметной комиссии'} "
        f"по предмету «{subject}».",
        f"Организовать предметную диагностику по образовательной траектории темы «{knowledge.topic[:60]}» "
        f"({subject}).",
    ]
