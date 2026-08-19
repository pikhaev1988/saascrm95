"""Классификация профиля подготовки класса."""

from __future__ import annotations

from apps.vpr.conclusion.rules import classify_mastery, classify_spread


PROFILE_LABELS = {
    "high": "высокий уровень подготовки",
    "stable": "устойчивый профиль",
    "balanced": "сбалансированная подготовка",
    "reproductive": "репродуктивный профиль",
    "practice": "практико-ориентированный профиль",
    "analytical": "аналитический профиль",
    "theoretical": "теоретический профиль",
    "heterogeneous": "неоднородная подготовка",
    "elevated_risk": "профиль повышенного риска",
    "critical": "критический профиль",
}


def classify_preparation_profile(
    *,
    summary,
    cognitive_code: str,
    groups,
    weak_topic_share: float,
    strong_topic_share: float,
) -> tuple[str, str, list[str]]:
    """Определить профиль подготовки по уже рассчитанным показателям."""
    quality = getattr(summary, "knowledge_quality_percent", None) if summary else None
    absolute = getattr(summary, "absolute_achievement_percent", None) if summary else None
    cv = getattr(summary, "cv_primary_score_percent", None) if summary else None
    avg_share = None
    if summary and summary.avg_primary_score is not None and summary.max_primary_score:
        avg_share = float(summary.avg_primary_score) / float(summary.max_primary_score) * 100.0

    mastery = classify_mastery(avg_share) or classify_mastery(quality)
    spread = classify_spread(cv)

    risk_pct = 0.0
    high_pct = 0.0
    if groups:
        gmap = getattr(groups, "groups", None) or {}
        risk = gmap.get("risk")
        high = gmap.get("high")
        if risk is not None:
            risk_pct = float(getattr(risk, "percent", 0) or 0)
        if high is not None:
            high_pct = float(getattr(high, "percent", 0) or 0)

    explanations: list[str] = []

    if mastery == "critical" or (absolute is not None and absolute < 40) or risk_pct >= 45:
        code = "critical"
        explanations.append(
            "Критический профиль фиксируется при низком среднем результате и "
            "высокой доле обучающихся группы риска. Подготовка класса требует "
            "системной коррекции базового содержания."
        )
    elif mastery == "problem" or risk_pct >= 30 or weak_topic_share >= 0.4:
        code = "elevated_risk"
        explanations.append(
            "Профиль повышенного риска определяется сочетанием недостаточного "
            "уровня освоения и заметной доли проблемных тем/участников. "
            "Без адресной работы дефициты будут закрепляться."
        )
    elif spread == "heterogeneous" or (cv is not None and cv >= 30):
        code = "heterogeneous"
        explanations.append(
            "Неоднородная подготовка проявляется в высоком разбросе индивидуальных "
            "результатов: в классе одновременно присутствуют успешные обучающиеся "
            "и выраженная группа риска."
        )
    elif cognitive_code == "advanced_deficit" and (mastery in {"high", "sufficient", "acceptable"}):
        code = "reproductive"
        explanations.append(
            "Репродуктивный профиль: базовый уровень удерживается, но применение "
            "знаний в новой ситуации (задания повышенного уровня) остаётся слабым. "
            "Класс воспроизводит знакомые алгоритмы лучше, чем решает нестандартные задачи."
        )
    elif cognitive_code in {"balanced_high", "balanced"} and strong_topic_share >= 0.45 and high_pct >= 25:
        if mastery in {"high", "sufficient"}:
            code = "high"
            explanations.append(
                "Высокий уровень подготовки подтверждается устойчивым выполнением "
                "заданий, значительной долей сильных тем и наличием группы "
                "высокого уровня."
            )
        else:
            code = "stable"
            explanations.append(
                "Устойчивый профиль: результаты стабильны, сильные стороны "
                "выражены, а дефициты носят локальный характер."
            )
    elif cognitive_code == "basic_deficit":
        code = "practice"
        explanations.append(
            "Практико-ориентированный, но неустойчивый профиль: затруднения "
            "на базовом уровне показывают, что даже типовые операции не "
            "автоматизированы у значительной части класса."
        )
    elif cognitive_code in {"advanced_gap", "advanced_deficit"}:
        code = "analytical"
        explanations.append(
            "Аналитический потенциал ограничен: класс лучше справляется с "
            "репродуктивными заданиями, чем с заданиями, требующими переноса "
            "и анализа в новой ситуации."
        )
    elif spread == "homogeneous" and mastery in {"sufficient", "acceptable", "high"}:
        code = "balanced"
        explanations.append(
            "Сбалансированная подготовка: результаты относительно однородны, "
            "без доминирования одной критической зоны. Профиль отражает "
            "равномерное освоение значительной части содержания."
        )
    else:
        code = "stable" if mastery in {"high", "sufficient"} else "balanced"
        explanations.append(
            "Профиль подготовки определяется сочетанием среднего уровня освоения, "
            "структуры тематических результатов и распределения обучающихся по группам."
        )

    if high_pct >= 20:
        explanations.append(
            f"Группа высокого уровня составляет около {high_pct:.0f}% участников "
            "и формирует ресурсный потенциал класса."
        )
    if risk_pct >= 15:
        explanations.append(
            f"Группа риска ({risk_pct:.0f}%) оказывает заметное влияние на "
            "средний результат и устойчивость профиля."
        )
    if weak_topic_share >= 0.25:
        explanations.append(
            f"Доля проблемных тем каталога составляет около {weak_topic_share * 100:.0f}%, "
            "что усиливает вывод о наличии устойчивых содержательных дефицитов."
        )
    if strong_topic_share >= 0.35:
        explanations.append(
            f"Доля устойчиво освоенных тем около {strong_topic_share * 100:.0f}% "
            "подтверждает наличие опорных зон предметной подготовки."
        )

    return code, PROFILE_LABELS[code], explanations
