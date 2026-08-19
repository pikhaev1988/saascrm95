"""
Фиксированные формулировки причин образовательных дефицитов ВПР.

Выбор формулировки — по аналитическим правилам, без ИИ и свободной генерации текста.
"""

from __future__ import annotations

CAUSE_THEMATIC = (
    "Недостаточное освоение содержания тематического раздела программы"
)
CAUSE_SKILL = (
    "Недостаточная сформированность проверяемого предметного умения"
)
CAUSE_APPLICATION = (
    "Недостаточная сформированность навыка применения правила "
    "в практической ситуации"
)
CAUSE_COMPLEXITY = (
    "Недостаточная сформированность навыков применения знаний "
    "в заданиях повышенного уровня сложности"
)
CAUSE_TASK_TYPE = (
    "Затруднения, связанные с особенностями типа задания"
)
CAUSE_BASIC = (
    "Недостаточное освоение базового программного содержания"
)
CAUSE_UNKNOWN = (
    "Характер причины не определяется по имеющимся справочным данным"
)

CAUSE_TYPE_THEMATIC = "thematic"
CAUSE_TYPE_SKILL = "skill"
CAUSE_TYPE_APPLICATION = "application"
CAUSE_TYPE_COMPLEXITY = "complexity"
CAUSE_TYPE_TASK_TYPE = "task_type"
CAUSE_TYPE_BASIC = "basic"
CAUSE_TYPE_UNKNOWN = "unknown"

SCALE_LOCAL = "локальная"
SCALE_MASS = "массовая"
SCALE_SYSTEMIC = "системная"
SCALE_NONE = "отсутствует"

CHARACTER_THEMATIC = "тематический дефицит"
CHARACTER_SKILL = "дефицит сформированности умения"
CHARACTER_APPLICATION = "дефицит применения знаний"
CHARACTER_COMPLEXITY = "дефицит выполнения заданий повышенной сложности"
CHARACTER_TASK_TYPE = "дефицит, связанный с типом задания"
CHARACTER_BASIC = "дефицит базового содержания"
CHARACTER_UNKNOWN = "характер затруднения не определён"

# Доли значимых дефицитов среди всех заданий (классификация масштаба)
SHARE_LOCAL_MAX = 0.15
SHARE_MASS_MAX = 0.40
