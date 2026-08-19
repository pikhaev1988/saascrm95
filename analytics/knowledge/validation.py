from __future__ import annotations

from analytics.engine.catalog import validate_topic_belongs_to_subject
from analytics.knowledge_models import TaskKnowledge


def validate_task_knowledge(
    subject_name: str,
    exam_type: str,
    knowledge: TaskKnowledge | None,
) -> list[str]:
    if not knowledge:
        return [f"В базе знаний ФИПИ отсутствует запись для задания предмета «{subject_name}»."]

    errors: list[str] = []
    if not knowledge.topic or len(knowledge.topic.strip()) < 3:
        errors.append("Тема задания не определена.")

    errors.extend(validate_topic_belongs_to_subject(subject_name, exam_type, knowledge.topic))

    if knowledge.fgos_class_start and knowledge.fgos_exam_class:
        if exam_type == "ege" and knowledge.fgos_class_start > knowledge.fgos_exam_class:
            errors.append("Класс изучения не может быть выше класса проверки ЕГЭ.")
        if exam_type == "oge" and knowledge.fgos_class_start > 9:
            errors.append("Класс изучения для ОГЭ не соответствует ФГОС.")

    if knowledge.fipi_content_code and len(knowledge.fipi_content_code) < 2:
        errors.append("Код элемента содержания ФИПИ некорректен.")

    if knowledge.skill and knowledge.skill_name and knowledge.skill_name == knowledge.topic:
        pass  # допустимо

    prev = knowledge.previous_topics or []
    nxt = knowledge.next_topics or []
    if prev and nxt and prev[-1] == nxt[0]:
        errors.append("Образовательная траектория содержит циклическую связь.")

    if float(knowledge.confidence or 0) < 0.3:
        errors.append("Достоверность метаданных ниже допустимого порога.")

    return errors
