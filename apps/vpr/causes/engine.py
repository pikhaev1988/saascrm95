"""
Движок анализа причин образовательных дефицитов ВПР.

Вход: analytics (VprAnalyticsEngine), deficits (VprDeficitEngine),
опционально справочник заданий (VprTaskCatalogLookup).

Выход: cause_analysis — возможные причины дефицитов.
Без рекомендаций, мероприятий, ИИ и новых расчётов показателей.
"""

from __future__ import annotations

from collections import defaultdict

from apps.vpr.analytics.result import VprAnalyticsResult
from apps.vpr.causes.labels import (
    CAUSE_APPLICATION,
    CAUSE_BASIC,
    CAUSE_COMPLEXITY,
    CAUSE_SKILL,
    CAUSE_TASK_TYPE,
    CAUSE_THEMATIC,
    CAUSE_TYPE_APPLICATION,
    CAUSE_TYPE_BASIC,
    CAUSE_TYPE_COMPLEXITY,
    CAUSE_TYPE_SKILL,
    CAUSE_TYPE_TASK_TYPE,
    CAUSE_TYPE_THEMATIC,
    CAUSE_TYPE_UNKNOWN,
    CAUSE_UNKNOWN,
    CHARACTER_APPLICATION,
    CHARACTER_BASIC,
    CHARACTER_COMPLEXITY,
    CHARACTER_SKILL,
    CHARACTER_TASK_TYPE,
    CHARACTER_THEMATIC,
    CHARACTER_UNKNOWN,
    SCALE_LOCAL,
    SCALE_MASS,
    SCALE_NONE,
    SCALE_SYSTEMIC,
    SHARE_LOCAL_MAX,
    SHARE_MASS_MAX,
)
from apps.vpr.causes.result import (
    VprCauseAnalysisResult,
    VprCauseFinding,
    VprCausePattern,
    VprCauseSummary,
)
from apps.vpr.deficits.result import VprDeficitResult, VprTaskDeficit
from apps.vpr.services.catalog_lookup import VprTaskCatalogLookup

PROBLEM_PRIORITIES = frozenset({"Critical", "High"})
PLACEHOLDER_TOPICS = frozenset({"", "Без темы в справочнике"})
PLACEHOLDER_SKILLS = frozenset({"", "Без умения в справочнике"})


class VprCauseAnalysisEngine:
    """
    Использование::

        analytics = VprAnalyticsEngine().analyze(protocol)
        deficits = VprDeficitEngine().analyze(analytics)
        causes = VprCauseAnalysisEngine().analyze(analytics, deficits)
    """

    def __init__(self, *, catalog_lookup: VprTaskCatalogLookup | None = None) -> None:
        self.catalog = catalog_lookup or VprTaskCatalogLookup()

    def analyze(
        self,
        analytics: VprAnalyticsResult,
        deficits: VprDeficitResult,
    ) -> VprCauseAnalysisResult:
        catalog_meta = self._catalog_meta(analytics)
        significant = [
            t for t in deficits.tasks if t.priority in PROBLEM_PRIORITIES
        ]
        enriched = [self._enrich_task(t, catalog_meta) for t in significant]

        task_findings = self._build_task_findings(enriched, deficits, analytics)
        topic_findings = self._build_topic_findings(enriched, deficits)
        skill_findings = self._build_skill_findings(enriched, deficits)
        patterns = self._build_patterns(enriched, deficits, analytics)
        summary = self._build_summary(
            significant=significant,
            findings=task_findings + topic_findings + skill_findings,
            patterns=patterns,
            catalog_meta=catalog_meta,
            analytics=analytics,
        )
        return VprCauseAnalysisResult(
            protocol_id=analytics.protocol_id,
            subject=analytics.subject,
            parallel=analytics.parallel,
            academic_year=analytics.academic_year,
            summary=summary,
            tasks=task_findings,
            topics=topic_findings,
            skills=skill_findings,
            patterns=patterns,
        )

    # ------------------------------------------------------------------ enrich

    def _catalog_meta(
        self,
        analytics: VprAnalyticsResult,
    ) -> dict[str, dict[str, str]]:
        """task_code -> {task_type, difficulty, topic, ...} из справочника."""
        result: dict[str, dict[str, str]] = {}
        for task in analytics.tasks:
            info = self.catalog.resolve(
                subject=analytics.subject,
                parallel=analytics.parallel,
                academic_year=analytics.academic_year,
                task_code=task.task_code,
            )
            if info is None:
                continue
            result[task.task_code] = {
                "task_type": (info.task_type or "").strip(),
                "difficulty": (info.difficulty or "").strip(),
                "topic": (info.topic or "").strip(),
                "program_section": (info.program_section or "").strip(),
                "checked_skill": (info.checked_skill or "").strip(),
            }
        return result

    def _enrich_task(
        self,
        deficit: VprTaskDeficit,
        catalog_meta: dict[str, dict[str, str]],
    ) -> dict:
        meta = catalog_meta.get(deficit.task_code, {})
        topic = (deficit.topic or meta.get("topic") or "").strip()
        skill = (deficit.checked_skill or meta.get("checked_skill") or "").strip()
        section = (deficit.program_section or meta.get("program_section") or "").strip()
        difficulty = (deficit.difficulty or meta.get("difficulty") or "").strip()
        task_type = (meta.get("task_type") or "").strip()
        return {
            "deficit": deficit,
            "topic": topic,
            "skill": skill,
            "section": section,
            "difficulty": difficulty,
            "task_type": task_type,
            "has_catalog": bool(meta) or bool(deficit.topic or deficit.checked_skill),
        }

    # ------------------------------------------------------------------ findings

    def _build_task_findings(
        self,
        enriched: list[dict],
        deficits: VprDeficitResult,
        analytics: VprAnalyticsResult,
    ) -> list[VprCauseFinding]:
        if not enriched:
            return []

        # группировка для определения характера причины
        by_topic: dict[str, list[dict]] = defaultdict(list)
        by_skill: dict[str, list[dict]] = defaultdict(list)
        by_type: dict[str, list[dict]] = defaultdict(list)
        advanced: list[dict] = []
        basic: list[dict] = []

        for item in enriched:
            topic_key = item["topic"] if item["topic"] not in PLACEHOLDER_TOPICS else ""
            skill_key = item["skill"] if item["skill"] not in PLACEHOLDER_SKILLS else ""
            if topic_key:
                by_topic[topic_key].append(item)
            if skill_key:
                by_skill[skill_key].append(item)
            if item["task_type"]:
                by_type[item["task_type"]].append(item)
            if self._is_advanced(item["difficulty"]):
                advanced.append(item)
            elif self._is_basic(item["difficulty"]):
                basic.append(item)

        global_cause = self._resolve_group_cause(
            items=enriched,
            by_topic=by_topic,
            by_skill=by_skill,
            by_type=by_type,
            advanced=advanced,
            basic=basic,
            all_tasks_count=max(len(deficits.tasks), len(analytics.tasks), 1),
        )

        findings: list[VprCauseFinding] = []
        # объединяем связанные задания в findings по причине/теме/умению
        clustered = self._cluster_findings(
            enriched=enriched,
            by_topic=by_topic,
            by_skill=by_skill,
            by_type=by_type,
            advanced=advanced,
            default_cause=global_cause,
            all_tasks_count=max(len(deficits.tasks), len(analytics.tasks), 1),
            students_at_risk=deficits.summary.students_at_risk,
            participants=analytics.summary.participants_count,
        )
        findings.extend(clustered)

        # одиночные значимые дефициты, не вошедшие в кластеры
        covered = {code for f in findings for code in f.task_codes}
        for item in enriched:
            code = item["deficit"].task_code
            if code in covered:
                continue
            cause_type, cause, character = self._cause_for_single(
                item, by_topic, by_skill, by_type, advanced
            )
            scale = self._scale_for_share(
                share=1 / max(len(deficits.tasks), 1),
                related_count=1,
                students_at_risk=deficits.summary.students_at_risk,
                participants=analytics.summary.participants_count,
            )
            findings.append(
                VprCauseFinding(
                    problem=f"Задание {code}",
                    skill=item["skill"] or "—",
                    topic=item["topic"] or "—",
                    section=item["section"] or "—",
                    difficulty=item["difficulty"] or "—",
                    task_type=item["task_type"] or "—",
                    cause=cause,
                    cause_type=cause_type,
                    scale=scale,
                    character=character,
                    task_codes=[code],
                )
            )
        return findings

    def _cluster_findings(
        self,
        *,
        enriched: list[dict],
        by_topic: dict[str, list[dict]],
        by_skill: dict[str, list[dict]],
        by_type: dict[str, list[dict]],
        advanced: list[dict],
        default_cause: tuple[str, str, str],
        all_tasks_count: int,
        students_at_risk: int,
        participants: int,
    ) -> list[VprCauseFinding]:
        findings: list[VprCauseFinding] = []
        used: set[str] = set()

        # 1) тематические кластеры (несколько заданий одной темы)
        for topic, items in sorted(by_topic.items(), key=lambda p: -len(p[1])):
            if len(items) < 2:
                continue
            codes = [i["deficit"].task_code for i in items]
            if all(c in used for c in codes):
                continue
            scale = self._scale_for_share(
                share=len(items) / all_tasks_count,
                related_count=len(items),
                students_at_risk=students_at_risk,
                participants=participants,
            )
            findings.append(
                VprCauseFinding(
                    problem=self._problem_label(codes),
                    skill=self._common_or_join(i["skill"] for i in items),
                    topic=topic,
                    section=self._common_or_join(i["section"] for i in items),
                    difficulty=self._common_or_join(i["difficulty"] for i in items),
                    task_type=self._common_or_join(i["task_type"] for i in items),
                    cause=CAUSE_THEMATIC,
                    cause_type=CAUSE_TYPE_THEMATIC,
                    scale=scale,
                    character=CHARACTER_THEMATIC,
                    task_codes=codes,
                )
            )
            used.update(codes)

        # 2) кластеры по умению
        for skill, items in sorted(by_skill.items(), key=lambda p: -len(p[1])):
            codes = [i["deficit"].task_code for i in items if i["deficit"].task_code not in used]
            if len(codes) < 2:
                continue
            selected = [i for i in items if i["deficit"].task_code in codes]
            scale = self._scale_for_share(
                share=len(selected) / all_tasks_count,
                related_count=len(selected),
                students_at_risk=students_at_risk,
                participants=participants,
            )
            findings.append(
                VprCauseFinding(
                    problem=self._problem_label(codes),
                    skill=skill,
                    topic=self._common_or_join(i["topic"] for i in selected),
                    section=self._common_or_join(i["section"] for i in selected),
                    difficulty=self._common_or_join(i["difficulty"] for i in selected),
                    task_type=self._common_or_join(i["task_type"] for i in selected),
                    cause=CAUSE_SKILL,
                    cause_type=CAUSE_TYPE_SKILL,
                    scale=scale,
                    character=CHARACTER_SKILL,
                    task_codes=codes,
                )
            )
            used.update(codes)

        # 3) только сложные задания
        adv_codes = [
            i["deficit"].task_code for i in advanced if i["deficit"].task_code not in used
        ]
        if len(adv_codes) >= 2 and len(advanced) >= max(2, int(0.5 * max(len(enriched), 1))):
            selected = [i for i in advanced if i["deficit"].task_code in adv_codes]
            scale = self._scale_for_share(
                share=len(selected) / all_tasks_count,
                related_count=len(selected),
                students_at_risk=students_at_risk,
                participants=participants,
            )
            findings.append(
                VprCauseFinding(
                    problem=self._problem_label(adv_codes),
                    skill=self._common_or_join(i["skill"] for i in selected),
                    topic=self._common_or_join(i["topic"] for i in selected),
                    section=self._common_or_join(i["section"] for i in selected),
                    difficulty=self._common_or_join(i["difficulty"] for i in selected),
                    task_type=self._common_or_join(i["task_type"] for i in selected),
                    cause=CAUSE_COMPLEXITY,
                    cause_type=CAUSE_TYPE_COMPLEXITY,
                    scale=scale,
                    character=CHARACTER_COMPLEXITY,
                    task_codes=adv_codes,
                )
            )
            used.update(adv_codes)

        # 4) тип задания
        for task_type, items in sorted(by_type.items(), key=lambda p: -len(p[1])):
            codes = [i["deficit"].task_code for i in items if i["deficit"].task_code not in used]
            if len(codes) < 2:
                continue
            selected = [i for i in items if i["deficit"].task_code in codes]
            scale = self._scale_for_share(
                share=len(selected) / all_tasks_count,
                related_count=len(selected),
                students_at_risk=students_at_risk,
                participants=participants,
            )
            findings.append(
                VprCauseFinding(
                    problem=self._problem_label(codes),
                    skill=self._common_or_join(i["skill"] for i in selected),
                    topic=self._common_or_join(i["topic"] for i in selected),
                    section=self._common_or_join(i["section"] for i in selected),
                    difficulty=self._common_or_join(i["difficulty"] for i in selected),
                    task_type=task_type,
                    cause=CAUSE_TASK_TYPE,
                    cause_type=CAUSE_TYPE_TASK_TYPE,
                    scale=scale,
                    character=CHARACTER_TASK_TYPE,
                    task_codes=codes,
                )
            )
            used.update(codes)

        _ = default_cause  # доступен для одиночных findings
        return findings

    def _cause_for_single(
        self,
        item: dict,
        by_topic: dict[str, list[dict]],
        by_skill: dict[str, list[dict]],
        by_type: dict[str, list[dict]],
        advanced: list[dict],
    ) -> tuple[str, str, str]:
        if not item["has_catalog"] and not item["topic"] and not item["skill"]:
            return CAUSE_TYPE_UNKNOWN, CAUSE_UNKNOWN, CHARACTER_UNKNOWN
        if item["topic"] and len(by_topic.get(item["topic"], [])) >= 2:
            return CAUSE_TYPE_THEMATIC, CAUSE_THEMATIC, CHARACTER_THEMATIC
        if item["skill"] and len(by_skill.get(item["skill"], [])) >= 2:
            return CAUSE_TYPE_SKILL, CAUSE_SKILL, CHARACTER_SKILL
        if self._is_advanced(item["difficulty"]) and item in advanced:
            return CAUSE_TYPE_COMPLEXITY, CAUSE_COMPLEXITY, CHARACTER_COMPLEXITY
        if item["task_type"] and len(by_type.get(item["task_type"], [])) >= 2:
            return CAUSE_TYPE_TASK_TYPE, CAUSE_TASK_TYPE, CHARACTER_TASK_TYPE
        if self._is_basic(item["difficulty"]):
            return CAUSE_TYPE_BASIC, CAUSE_BASIC, CHARACTER_BASIC
        if item["skill"]:
            return CAUSE_TYPE_APPLICATION, CAUSE_APPLICATION, CHARACTER_APPLICATION
        if item["topic"]:
            return CAUSE_TYPE_THEMATIC, CAUSE_THEMATIC, CHARACTER_THEMATIC
        return CAUSE_TYPE_UNKNOWN, CAUSE_UNKNOWN, CHARACTER_UNKNOWN

    def _build_topic_findings(
        self,
        enriched: list[dict],
        deficits: VprDeficitResult,
    ) -> list[VprCauseFinding]:
        findings: list[VprCauseFinding] = []
        weak_topics = [
            t
            for t in deficits.topics
            if t.risk in PROBLEM_PRIORITIES or t.mastery_level in {"problem", "critical"}
        ]
        enriched_by_topic: dict[str, list[dict]] = defaultdict(list)
        for item in enriched:
            if item["topic"] and item["topic"] not in PLACEHOLDER_TOPICS:
                enriched_by_topic[item["topic"]].append(item)

        for topic in weak_topics:
            if topic.topic in PLACEHOLDER_TOPICS:
                continue
            items = enriched_by_topic.get(topic.topic) or [
                {
                    "deficit": None,
                    "skill": "",
                    "topic": topic.topic,
                    "section": "",
                    "difficulty": "",
                    "task_type": "",
                    "has_catalog": bool(topic.topic),
                }
            ]
            codes = list(topic.task_codes) or [
                i["deficit"].task_code for i in items if i.get("deficit")
            ]
            scale = self._scale_for_share(
                share=(topic.problem_tasks_count or len(codes)) / max(len(deficits.tasks), 1),
                related_count=max(topic.tasks_count, len(codes)),
                students_at_risk=deficits.summary.students_at_risk,
                participants=0,
            )
            # тематический дефицит, если несколько связанных заданий
            if topic.tasks_count >= 2 or topic.problem_tasks_count >= 2:
                cause, cause_type, character = CAUSE_THEMATIC, CAUSE_TYPE_THEMATIC, CHARACTER_THEMATIC
            else:
                cause, cause_type, character = CAUSE_THEMATIC, CAUSE_TYPE_THEMATIC, CHARACTER_THEMATIC
            findings.append(
                VprCauseFinding(
                    problem=f"Тема «{topic.topic}»",
                    skill=self._common_or_join(i.get("skill", "") for i in items),
                    topic=topic.topic,
                    section=self._common_or_join(i.get("section", "") for i in items),
                    difficulty=self._common_or_join(i.get("difficulty", "") for i in items),
                    task_type=self._common_or_join(i.get("task_type", "") for i in items),
                    cause=cause,
                    cause_type=cause_type,
                    scale=scale,
                    character=character,
                    task_codes=codes,
                )
            )
        return findings

    def _build_skill_findings(
        self,
        enriched: list[dict],
        deficits: VprDeficitResult,
    ) -> list[VprCauseFinding]:
        findings: list[VprCauseFinding] = []
        weak_skills = [
            s
            for s in deficits.skills
            if s.risk in PROBLEM_PRIORITIES or s.mastery_level in {"problem", "critical"}
        ]
        for skill in weak_skills:
            if skill.checked_skill in PLACEHOLDER_SKILLS:
                continue
            codes = list(skill.task_codes)
            scale = self._scale_for_share(
                share=(skill.problem_tasks_count or len(codes)) / max(len(deficits.tasks), 1),
                related_count=max(skill.tasks_count, len(codes)),
                students_at_risk=deficits.summary.students_at_risk,
                participants=0,
            )
            # несколько заданий одного умения → дефицит умения
            if skill.tasks_count >= 2:
                cause, cause_type, character = CAUSE_SKILL, CAUSE_TYPE_SKILL, CHARACTER_SKILL
            else:
                cause, cause_type, character = (
                    CAUSE_APPLICATION,
                    CAUSE_TYPE_APPLICATION,
                    CHARACTER_APPLICATION,
                )
            related = [i for i in enriched if i["skill"] == skill.checked_skill]
            findings.append(
                VprCauseFinding(
                    problem=f"Умение «{skill.checked_skill}»",
                    skill=skill.checked_skill,
                    topic=self._common_or_join(i["topic"] for i in related),
                    section=self._common_or_join(i["section"] for i in related),
                    difficulty=self._common_or_join(i["difficulty"] for i in related),
                    task_type=self._common_or_join(i["task_type"] for i in related),
                    cause=cause,
                    cause_type=cause_type,
                    scale=scale,
                    character=character,
                    task_codes=codes,
                )
            )
        return findings

    def _build_patterns(
        self,
        enriched: list[dict],
        deficits: VprDeficitResult,
        analytics: VprAnalyticsResult,
    ) -> list[VprCausePattern]:
        patterns: list[VprCausePattern] = []
        if not enriched:
            return patterns

        all_count = max(len(deficits.tasks), len(analytics.tasks), 1)
        by_topic: dict[str, list[dict]] = defaultdict(list)
        by_skill: dict[str, list[dict]] = defaultdict(list)
        for item in enriched:
            if item["topic"] and item["topic"] not in PLACEHOLDER_TOPICS:
                by_topic[item["topic"]].append(item)
            if item["skill"] and item["skill"] not in PLACEHOLDER_SKILLS:
                by_skill[item["skill"]].append(item)

        multi_topics = {k: v for k, v in by_topic.items() if len(v) >= 2}
        if multi_topics:
            codes = [i["deficit"].task_code for items in multi_topics.values() for i in items]
            scale = self._scale_for_share(
                share=len(codes) / all_count,
                related_count=len(codes),
                students_at_risk=deficits.summary.students_at_risk,
                participants=analytics.summary.participants_count,
            )
            patterns.append(
                VprCausePattern(
                    pattern_type="thematic_cluster",
                    title="Кластер тематических дефицитов",
                    cause=CAUSE_THEMATIC,
                    scale=scale,
                    task_codes=sorted(set(codes)),
                    related_topics=sorted(multi_topics.keys()),
                    related_skills=[],
                )
            )

        multi_skills = {k: v for k, v in by_skill.items() if len(v) >= 2}
        if multi_skills:
            codes = [i["deficit"].task_code for items in multi_skills.values() for i in items]
            scale = self._scale_for_share(
                share=len(codes) / all_count,
                related_count=len(codes),
                students_at_risk=deficits.summary.students_at_risk,
                participants=analytics.summary.participants_count,
            )
            patterns.append(
                VprCausePattern(
                    pattern_type="skill_cluster",
                    title="Кластер дефицитов умений",
                    cause=CAUSE_SKILL,
                    scale=scale,
                    task_codes=sorted(set(codes)),
                    related_topics=[],
                    related_skills=sorted(multi_skills.keys()),
                )
            )

        advanced = [i for i in enriched if self._is_advanced(i["difficulty"])]
        basic_ok = [
            t
            for t in analytics.tasks
            if self._is_basic(t.difficulty or "")
            and t.completion_percent is not None
            and t.completion_percent >= 75
        ]
        if advanced and len(advanced) >= 2 and basic_ok:
            codes = [i["deficit"].task_code for i in advanced]
            scale = self._scale_for_share(
                share=len(codes) / all_count,
                related_count=len(codes),
                students_at_risk=deficits.summary.students_at_risk,
                participants=analytics.summary.participants_count,
            )
            patterns.append(
                VprCausePattern(
                    pattern_type="complexity_gap",
                    title="Разрыв между базовым и повышенным уровнем",
                    cause=CAUSE_COMPLEXITY,
                    scale=scale,
                    task_codes=codes,
                    related_topics=sorted(
                        {i["topic"] for i in advanced if i["topic"]}
                    ),
                    related_skills=sorted(
                        {i["skill"] for i in advanced if i["skill"]}
                    ),
                )
            )

        weak_share = len(enriched) / all_count
        if weak_share >= SHARE_MASS_MAX:
            patterns.append(
                VprCausePattern(
                    pattern_type="systemic_deficit",
                    title="Системный характер образовательных дефицитов",
                    cause=CAUSE_SKILL if multi_skills else CAUSE_THEMATIC,
                    scale=SCALE_SYSTEMIC,
                    task_codes=[i["deficit"].task_code for i in enriched],
                    related_topics=sorted({i["topic"] for i in enriched if i["topic"]}),
                    related_skills=sorted({i["skill"] for i in enriched if i["skill"]}),
                )
            )
        elif not enriched:
            pass
        elif weak_share <= SHARE_LOCAL_MAX:
            patterns.append(
                VprCausePattern(
                    pattern_type="local_deficit",
                    title="Локальный характер образовательных дефицитов",
                    cause=CAUSE_APPLICATION,
                    scale=SCALE_LOCAL,
                    task_codes=[i["deficit"].task_code for i in enriched],
                    related_topics=sorted({i["topic"] for i in enriched if i["topic"]}),
                    related_skills=sorted({i["skill"] for i in enriched if i["skill"]}),
                )
            )

        return patterns

    def _build_summary(
        self,
        *,
        significant: list[VprTaskDeficit],
        findings: list[VprCauseFinding],
        patterns: list[VprCausePattern],
        catalog_meta: dict[str, dict[str, str]],
        analytics: VprAnalyticsResult,
    ) -> VprCauseSummary:
        scales = [f.scale for f in findings]
        local_count = sum(1 for s in scales if s == SCALE_LOCAL)
        mass_count = sum(1 for s in scales if s == SCALE_MASS)
        systemic_count = sum(1 for s in scales if s == SCALE_SYSTEMIC)

        cause_counter: dict[str, int] = defaultdict(int)
        for finding in findings:
            cause_counter[finding.cause_type] += 1
        dominant_cause = ""
        if cause_counter:
            dominant_cause = max(cause_counter.items(), key=lambda p: p[1])[0]

        if systemic_count:
            dominant_scale = SCALE_SYSTEMIC
        elif mass_count:
            dominant_scale = SCALE_MASS
        elif local_count:
            dominant_scale = SCALE_LOCAL
        elif not significant:
            dominant_scale = SCALE_NONE
        else:
            dominant_scale = SCALE_LOCAL

        matched = len(catalog_meta)
        total = len(analytics.tasks)
        if total == 0 or matched == 0:
            coverage = "none"
        elif matched >= total:
            coverage = "full"
        else:
            coverage = "partial"

        return VprCauseSummary(
            significant_deficits_count=len(significant),
            causes_count=len(findings),
            local_count=local_count,
            mass_count=mass_count,
            systemic_count=systemic_count,
            dominant_cause_type=dominant_cause or CAUSE_TYPE_UNKNOWN,
            dominant_scale=dominant_scale,
            catalog_coverage=coverage,
        )

    # ------------------------------------------------------------------ helpers

    def _resolve_group_cause(self, **kwargs) -> tuple[str, str, str]:
        by_topic = kwargs["by_topic"]
        by_skill = kwargs["by_skill"]
        advanced = kwargs["advanced"]
        items = kwargs["items"]
        if any(len(v) >= 2 for v in by_topic.values()):
            return CAUSE_TYPE_THEMATIC, CAUSE_THEMATIC, CHARACTER_THEMATIC
        if any(len(v) >= 2 for v in by_skill.values()):
            return CAUSE_TYPE_SKILL, CAUSE_SKILL, CHARACTER_SKILL
        if advanced and len(advanced) >= max(2, int(0.5 * max(len(items), 1))):
            return CAUSE_TYPE_COMPLEXITY, CAUSE_COMPLEXITY, CHARACTER_COMPLEXITY
        return CAUSE_TYPE_APPLICATION, CAUSE_APPLICATION, CHARACTER_APPLICATION

    @staticmethod
    def _is_advanced(difficulty: str) -> bool:
        text = (difficulty or "").strip().lower()
        if text in {"п", "p"}:
            return True
        return any(
            token in text
            for token in ("повыш", "сложн", "высокий", "advanced", "трудн")
        )

    @staticmethod
    def _is_basic(difficulty: str) -> bool:
        text = (difficulty or "").strip().lower()
        if text in {"б", "b"}:
            return True
        return any(token in text for token in ("базов", "basic", "лёгк", "легк"))

    @staticmethod
    def _scale_for_share(
        *,
        share: float,
        related_count: int,
        students_at_risk: int,
        participants: int,
    ) -> str:
        small_group = (
            participants > 0
            and students_at_risk > 0
            and (students_at_risk / participants) < SHARE_LOCAL_MAX
        )
        if share >= SHARE_MASS_MAX or related_count >= 5:
            return SCALE_SYSTEMIC
        if share >= SHARE_LOCAL_MAX or related_count >= 3:
            return SCALE_MASS
        if related_count <= 2 and small_group:
            return SCALE_LOCAL
        if related_count <= 2:
            return SCALE_LOCAL
        return SCALE_MASS

    @staticmethod
    def _problem_label(codes: list[str]) -> str:
        ordered = sorted(codes, key=lambda c: (len(c), c))
        if not ordered:
            return "Задания"
        if len(ordered) == 1:
            return f"Задание {ordered[0]}"
        if len(ordered) == 2:
            return f"Задания {ordered[0]} и {ordered[1]}"
        return "Задания " + ", ".join(ordered[:-1]) + f" и {ordered[-1]}"

    @staticmethod
    def _common_or_join(values) -> str:
        clean = sorted({(v or "").strip() for v in values if (v or "").strip()})
        if not clean:
            return "—"
        if len(clean) == 1:
            return clean[0]
        return "; ".join(clean)
