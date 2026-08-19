"""Школьные рекомендации на базе VprRecommendationEngine (через протокольные analysis)."""

from __future__ import annotations

from collections import defaultdict

from apps.vpr.comprehensive_analysis.recommendations import VprRecommendationEngine
from apps.vpr.school_analysis.metrics import subject_name
from apps.vpr.school_analysis.schemas import (
    SchoolRecommendationGroup,
    SchoolRecommendationsProfile,
    SubjectSchoolRow,
)


class SchoolRecommendationsBuilder:
    """
    Не пересчитывает дефициты: для каждого протокола берёт уже собранные
    topics/skills/deficits/causes и прогоняет через VprRecommendationEngine,
    затем агрегирует по школе.
    """

    def __init__(self, engine: VprRecommendationEngine | None = None) -> None:
        self.engine = engine or VprRecommendationEngine()

    def build(
        self,
        analyses: list,
        *,
        subjects: list[SubjectSchoolRow],
    ) -> SchoolRecommendationsProfile:
        by_subject: dict[str, list[str]] = defaultdict(list)
        by_topic: dict[str, list[str]] = defaultdict(list)
        by_risk: dict[str, list[str]] = defaultdict(list)
        all_actions: list[str] = []

        subject_risk = {row.subject: row.risk_level for row in subjects}

        for analysis in analyses:
            subject = subject_name(analysis) or "—"
            profile = self.engine.build(
                topics=analysis.topic_analysis,
                skills=analysis.skill_analysis,
                deficits=analysis.deficits,
                causes=analysis.causes,
            )
            risk = subject_risk.get(subject, "medium")
            for action in profile.actions:
                all_actions.append(action)
                by_subject[subject].append(action)
                by_risk[risk].append(action)
            for item in profile.items:
                if item.topic:
                    by_topic[item.topic].extend(item.actions)
                for action in item.actions:
                    if action not in by_subject[subject]:
                        by_subject[subject].append(action)

        return SchoolRecommendationsProfile(
            by_subject=[
                SchoolRecommendationGroup(
                    key=name,
                    title=name,
                    actions=_unique(actions)[:8],
                    risk_level=subject_risk.get(name, ""),
                )
                for name, actions in sorted(by_subject.items())
                if actions
            ],
            by_topic=[
                SchoolRecommendationGroup(
                    key=name,
                    title=name,
                    actions=_unique(actions)[:6],
                )
                for name, actions in sorted(by_topic.items())
                if actions
            ][:20],
            by_risk=[
                SchoolRecommendationGroup(
                    key=level,
                    title=level,
                    actions=_unique(actions)[:8],
                    risk_level=level,
                )
                for level in ("high", "medium", "low")
                if by_risk.get(level)
                for actions in [by_risk[level]]
            ],
            actions=_unique(all_actions)[:30],
        )


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = (item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out
