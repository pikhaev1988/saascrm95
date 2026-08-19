"""Анализ проверяемых умений — поверх analytics.skills / deficits.skills."""

from __future__ import annotations

from apps.vpr.analytics.result import VprAnalyticsResult
from apps.vpr.comprehensive_analysis.schemas import VprSkillAnalysisProfile, VprSkillProfileItem
from apps.vpr.deficits.result import VprDeficitResult

PLACEHOLDER = "Без умения в справочнике"


class VprSkillAnalyzer:
    """Классифицирует сформированность умений по среднему % выполнения."""

    def analyze(
        self,
        analytics: VprAnalyticsResult,
        deficits: VprDeficitResult | None = None,
    ) -> VprSkillAnalysisProfile:
        deficit_skills = {
            item.checked_skill: item
            for item in (deficits.skills if deficits else [])
            if item.checked_skill
        }
        items: list[VprSkillProfileItem] = []
        formed: list[str] = []
        underformed: list[str] = []

        for skill_row in analytics.skills:
            skill = (skill_row.checked_skill or "").strip() or PLACEHOLDER
            avg = skill_row.avg_completion_percent
            d = deficit_skills.get(skill)
            if d is not None and d.avg_completion_percent is not None:
                avg = d.avg_completion_percent
            level = self._level(avg, d.mastery_level if d else "")
            items.append(
                VprSkillProfileItem(
                    skill=skill,
                    level=level,
                    tasks=list(skill_row.task_codes or []),
                    average=avg,
                )
            )
            if skill == PLACEHOLDER:
                continue
            if level == "high":
                formed.append(skill)
            elif level == "low":
                underformed.append(skill)

        return VprSkillAnalysisProfile(items=items, formed=formed, underformed=underformed)

    @staticmethod
    def _level(avg: float | None, mastery: str) -> str:
        if mastery in {"high", "sufficient"}:
            return "high"
        if mastery in {"critical", "problem"}:
            return "low"
        if avg is None:
            return "medium"
        if avg >= 75:
            return "high"
        if avg < 60:
            return "low"
        return "medium"
