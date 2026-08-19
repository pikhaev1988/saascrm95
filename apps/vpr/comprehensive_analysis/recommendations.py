"""Управленческие рекомендации: дефицит → причина → действие (правила, без ИИ)."""

from __future__ import annotations

from apps.vpr.causes.result import VprCauseAnalysisResult
from apps.vpr.comprehensive_analysis.schemas import (
    VprRecommendationItem,
    VprRecommendationsProfile,
    VprSkillAnalysisProfile,
    VprTopicAnalysisProfile,
)
from apps.vpr.deficits.result import VprDeficitResult

PLACEHOLDER_TOPICS = frozenset({"", "Без темы в справочнике"})
PLACEHOLDER_SKILLS = frozenset({"", "Без умения в справочнике"})


class VprRecommendationEngine:
    """
    Связывает тематические/умениевые дефициты с причинами и формирует
    типовые управленческие действия по правилам.
    """

    def build(
        self,
        *,
        topics: VprTopicAnalysisProfile,
        skills: VprSkillAnalysisProfile,
        deficits: VprDeficitResult | None = None,
        causes: VprCauseAnalysisResult | None = None,
    ) -> VprRecommendationsProfile:
        cause_by_topic = {
            item.topic: item
            for item in (causes.topics if causes else [])
            if item.topic and item.topic not in PLACEHOLDER_TOPICS
        }
        cause_by_skill = {
            item.skill: item
            for item in (causes.skills if causes else [])
            if item.skill and item.skill not in PLACEHOLDER_SKILLS
        }

        items: list[VprRecommendationItem] = []
        actions_flat: list[str] = []

        for topic_item in topics.items:
            if topic_item.deficit_type == "none" or topic_item.topic in PLACEHOLDER_TOPICS:
                continue
            cause = cause_by_topic.get(topic_item.topic)
            cause_text = cause.cause if cause else ""
            actions = self._actions_for_topic(
                topic=topic_item.topic,
                deficit_type=topic_item.deficit_type,
                cause_type=cause.cause_type if cause else "",
            )
            items.append(
                VprRecommendationItem(
                    topic=topic_item.topic,
                    skill="",
                    deficit=topic_item.deficit_type,
                    cause=cause_text,
                    actions=actions,
                )
            )
            actions_flat.extend(actions)

        for skill_item in skills.items:
            if skill_item.level != "low" or skill_item.skill in PLACEHOLDER_SKILLS:
                continue
            cause = cause_by_skill.get(skill_item.skill)
            cause_text = cause.cause if cause else ""
            actions = self._actions_for_skill(
                skill=skill_item.skill,
                cause_type=cause.cause_type if cause else "",
            )
            items.append(
                VprRecommendationItem(
                    topic="",
                    skill=skill_item.skill,
                    deficit="skill_low",
                    cause=cause_text,
                    actions=actions,
                )
            )
            actions_flat.extend(actions)

        # если дефициты есть, а тем/умений из справочника нет — общие действия
        if not items and deficits is not None:
            if deficits.summary.tasks_critical or deficits.summary.tasks_problem:
                actions = [
                    "Провести поэлементный анализ заданий с низким процентом выполнения",
                    "Сопоставить результаты со справочником заданий ВПР и уточнить темы/умения",
                    "Организовать работу методического объединения по выявленным дефицитам",
                ]
                items.append(
                    VprRecommendationItem(
                        topic="",
                        skill="",
                        deficit="tasks",
                        cause="",
                        actions=actions,
                    )
                )
                actions_flat.extend(actions)

        # уникальные действия с сохранением порядка
        seen: set[str] = set()
        unique_actions: list[str] = []
        for action in actions_flat:
            if action in seen:
                continue
            seen.add(action)
            unique_actions.append(action)

        return VprRecommendationsProfile(items=items, actions=unique_actions)

    @staticmethod
    def _actions_for_topic(*, topic: str, deficit_type: str, cause_type: str) -> list[str]:
        scale_label = "массовый" if deficit_type == "mass" else "локальный"
        actions = [
            f"Провести анализ методики преподавания темы «{topic}» ({scale_label} дефицит)",
            "Организовать работу методического объединения по коррекции выявленного дефицита",
            f"Разработать комплект заданий для коррекции дефицита по теме «{topic}»",
        ]
        if cause_type:
            actions.append(
                "Учесть в плане работы установленную причину дефицита и скорректировать рабочие программы"
            )
        if deficit_type == "mass":
            actions.append(
                "Включить тему в план внутришкольного контроля и провести повторную диагностику"
            )
        return actions

    @staticmethod
    def _actions_for_skill(*, skill: str, cause_type: str) -> list[str]:
        actions = [
            f"Спланировать систему упражнений на формирование умения: {skill}",
            "Провести взаимопосещение уроков с фокусом на проверяемое умение",
            "Подготовить дифференцированные задания для групп риска",
        ]
        if cause_type:
            actions.append("Соотнести приёмы работы на уроке с характером установленной причины дефицита")
        return actions
