"""
Правила экспертной интерпретации результатов ВПР (ФИОКО).

Пороги применяются только к уже рассчитанным показателям Analytics/Deficit.
Новые математические метрики не вводятся.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Пороги освоения (согласованы со шкалой DeficitEngine / ФИОКО)
BAND_HIGH = 90.0
BAND_SUFFICIENT = 75.0
BAND_ACCEPTABLE = 60.0
BAND_PROBLEM = 40.0

# Коэффициент вариации: устойчивость / однородность
CV_HOMOGENEOUS = 15.0
CV_MODERATE = 30.0

# Доля отметок «2» / проблемных заданий — масштаб дефицитов
RISK_SHARE_LOCAL = 0.15
RISK_SHARE_MASS = 0.40

MasteryBand = Literal["high", "sufficient", "acceptable", "problem", "critical"]
SpreadBand = Literal["homogeneous", "moderate", "heterogeneous"]
DeficitScale = Literal["absent", "local", "mass", "systemic"]


@dataclass(frozen=True, slots=True)
class InterpretationContext:
    """Сжатый контекст интерпретации на основе готовых показателей."""

    mastery_band: MasteryBand
    quality_band: MasteryBand | None
    absolute_band: MasteryBand | None
    avg_share: float | None
    spread_band: SpreadBand | None
    skew: Literal["symmetric", "high_tail", "low_tail", "unknown"]
    mark2_share: float | None
    mark45_share: float | None
    strong_task_share: float | None
    weak_task_share: float | None
    basic_strong: bool
    advanced_weak: bool
    deficit_scale: DeficitScale
    strong_topics: tuple[str, ...]
    weak_topics: tuple[str, ...]
    strong_skills: tuple[str, ...]
    weak_skills: tuple[str, ...]
    subject: str
    parallel: int


def classify_mastery(percent: float | None) -> MasteryBand | None:
    if percent is None:
        return None
    value = float(percent)
    if value >= BAND_HIGH:
        return "high"
    if value >= BAND_SUFFICIENT:
        return "sufficient"
    if value >= BAND_ACCEPTABLE:
        return "acceptable"
    if value >= BAND_PROBLEM:
        return "problem"
    return "critical"


def classify_spread(cv_percent: float | None) -> SpreadBand | None:
    if cv_percent is None:
        return None
    value = float(cv_percent)
    if value < CV_HOMOGENEOUS:
        return "homogeneous"
    if value < CV_MODERATE:
        return "moderate"
    return "heterogeneous"


def classify_skew(avg: float | None, median: float | None) -> Literal["symmetric", "high_tail", "low_tail", "unknown"]:
    if avg is None or median is None:
        return "unknown"
    delta = float(avg) - float(median)
    if abs(delta) < 0.05 * max(abs(float(median)), 1.0):
        return "symmetric"
    if delta > 0:
        return "high_tail"
    return "low_tail"


def classify_deficit_scale(
    *,
    weak_task_share: float | None,
    topics_at_risk: int,
    topics_total: int,
    skills_at_risk: int,
    skills_total: int,
) -> DeficitScale:
    if weak_task_share is None:
        weak_task_share = 0.0
    topic_risk_share = (topics_at_risk / topics_total) if topics_total else 0.0
    skill_risk_share = (skills_at_risk / skills_total) if skills_total else 0.0

    if weak_task_share <= 0 and topics_at_risk <= 0 and skills_at_risk <= 0:
        return "absent"
    if (
        weak_task_share >= RISK_SHARE_MASS
        or topic_risk_share >= RISK_SHARE_MASS
        or skill_risk_share >= RISK_SHARE_MASS
    ):
        return "systemic"
    if (
        weak_task_share >= RISK_SHARE_LOCAL
        or topic_risk_share >= RISK_SHARE_LOCAL
        or skill_risk_share >= RISK_SHARE_LOCAL
    ):
        return "mass"
    return "local"


MASTERY_LABELS = {
    "high": "высокому уровню освоения образовательной программы",
    "sufficient": "достаточному уровню освоения образовательной программы",
    "acceptable": "допустимому уровню освоения образовательной программы",
    "problem": "уровню освоения образовательной программы ниже ожидаемого",
    "critical": "критически низкому уровню освоения образовательной программы",
}

QUALITY_INTERPRETATION = {
    "high": (
        "Доля обучающихся, достигших повышенного уровня подготовки, является высокой "
        "и отражает устойчивое освоение программного материала значительной частью участников."
    ),
    "sufficient": (
        "Доля обучающихся, достигших повышенного уровня подготовки, соответствует "
        "достаточному результату и свидетельствует о преобладании положительных "
        "образовательных достижений."
    ),
    "acceptable": (
        "Доля обучающихся, достигших повышенного уровня подготовки, находится "
        "на допустимом уровне, однако потенциал для более глубокого освоения "
        "отдельных разделов программы сохраняется."
    ),
    "problem": (
        "Доля обучающихся, достигших повышенного уровня подготовки, является "
        "недостаточной, что свидетельствует о необходимости более глубокого освоения "
        "отдельных разделов программы."
    ),
    "critical": (
        "Доля обучающихся, достигших повышенного уровня подготовки, крайне невелика, "
        "что указывает на существенные пробелы в освоении программного содержания."
    ),
}

SPREAD_INTERPRETATION = {
    "homogeneous": (
        "Разброс индивидуальных результатов невелик: подготовка участников "
        "характеризуется относительной однородностью."
    ),
    "moderate": (
        "Разброс индивидуальных результатов носит умеренный характер: наряду "
        "с устойчивой основной группой присутствуют различия в уровне подготовки."
    ),
    "heterogeneous": (
        "Разброс индивидуальных результатов значителен: подготовка участников "
        "существенно дифференцирована, что указывает на неоднородность образовательных достижений."
    ),
}

SKEW_INTERPRETATION = {
    "symmetric": (
        "Соотношение центральных характеристик распределения свидетельствует "
        "о сравнительно симметричной структуре результатов."
    ),
    "high_tail": (
        "Структура распределения указывает на наличие группы участников "
        "с более высокими индивидуальными результатами относительно основной части выборки."
    ),
    "low_tail": (
        "Структура распределения указывает на смещение в сторону более низких "
        "индивидуальных результатов у части участников."
    ),
}

DEFICIT_SCALE_INTERPRETATION = {
    "absent": (
        "Существенных образовательных дефицитов критического и высокого приоритета "
        "не зафиксировано."
    ),
    "local": (
        "Выявленные образовательные дефициты носят локальный характер и затрагивают "
        "ограниченный круг заданий либо предметных умений."
    ),
    "mass": (
        "Выявленные образовательные дефициты носят массовый характер: затруднения "
        "проявляются у заметной доли заданий и тематических направлений."
    ),
    "systemic": (
        "Выявленные образовательные дефициты носят системный характер и охватывают "
        "значительную часть проверяемых заданий, тем и предметных умений."
    ),
}
