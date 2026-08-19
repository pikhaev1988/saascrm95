"""Агрегация по параллелям (классам)."""



from __future__ import annotations



from apps.vpr.school_analysis.metrics import (

    PLACEHOLDER_SKILLS,

    PLACEHOLDER_TOPICS,

    classify_item_risk,

    completion_percent,

    deficits_count,

    participants_count,

    quality_percent,

    safe_mean,

    parallel_value,

)

from apps.vpr.school_analysis.schemas import GradeSchoolRow



PRIORITY_WEIGHT = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}





class SchoolGradesAnalyzer:

    def analyze(self, analyses: list) -> list[GradeSchoolRow]:

        by_grade: dict[int, list] = {}

        for analysis in analyses:

            by_grade.setdefault(parallel_value(analysis), []).append(analysis)



        rows: list[GradeSchoolRow] = []

        for parallel, items in sorted(by_grade.items()):

            completion = safe_mean([completion_percent(a) for a in items])

            quality = safe_mean([quality_percent(a) for a in items])

            deficits = sum(deficits_count(a) for a in items)

            rows.append(

                GradeSchoolRow(

                    parallel=parallel,

                    protocols_count=len(items),

                    participants=sum(participants_count(a) for a in items),

                    avg_completion_percent=completion,

                    quality_percent=quality,

                    risk_level=classify_item_risk(

                        completion=completion,

                        quality=quality,

                        deficits=deficits,

                    ),

                    main_topics=self._main_topics(items),

                    main_skills=self._main_skills(items),

                )

            )

        return rows



    def _main_topics(self, items: list, *, limit: int = 3) -> list[str]:

        ranked = self._rank_topics(items, weak=True)

        if ranked:

            return [name for name, _ in ranked[:limit]]

        return []



    def _main_skills(self, items: list, *, limit: int = 3) -> list[str]:

        ranked = self._rank_skills(items, weak=True)

        if ranked:

            return [name for name, _ in ranked[:limit]]

        return []



    def _rank_topics(self, items: list, *, weak: bool) -> list[tuple[str, float]]:

        scores: dict[str, list[float]] = {}

        weights: dict[str, int] = {}



        for analysis in items:

            topic_profile = getattr(analysis, "topic_analysis", None)

            if topic_profile is not None:

                for name in getattr(topic_profile, "mass_deficits", []) or []:

                    if name and name not in PLACEHOLDER_TOPICS:

                        weights[name] = weights.get(name, 0) + 3

                for name in getattr(topic_profile, "local_deficits", []) or []:

                    if name and name not in PLACEHOLDER_TOPICS:

                        weights[name] = weights.get(name, 0) + 2



            for topic in getattr(topic_profile, "items", []) or []:

                name = (topic.topic or "").strip()

                if not name or name in PLACEHOLDER_TOPICS or topic.average is None:

                    continue

                scores.setdefault(name, []).append(float(topic.average))

                if topic.deficit_type in {"mass", "local"}:

                    weights[name] = weights.get(name, 0) + (3 if topic.deficit_type == "mass" else 2)



            deficits = getattr(analysis, "deficits", None)

            if deficits is not None:

                for item in getattr(deficits, "topics", []) or []:

                    name = (item.topic or "").strip()

                    if not name or name in PLACEHOLDER_TOPICS:

                        continue

                    weight = PRIORITY_WEIGHT.get(item.priority or "Low", 1)

                    weights[name] = weights.get(name, 0) + weight

                    if item.avg_completion_percent is not None:

                        scores.setdefault(name, []).append(float(item.avg_completion_percent))



        ranked: list[tuple[str, float]] = []

        for name, vals in scores.items():

            avg = sum(vals) / len(vals)

            # Чем ниже результат и выше вес дефицита — тем выше приоритет для «основных тем»

            score = avg - weights.get(name, 0) * 3.0

            ranked.append((name, score))

        ranked.sort(key=lambda pair: pair[1], reverse=not weak)

        return ranked



    def _rank_skills(self, items: list, *, weak: bool) -> list[tuple[str, float]]:

        scores: dict[str, list[float]] = {}

        weights: dict[str, int] = {}



        for analysis in items:

            skill_profile = getattr(analysis, "skill_analysis", None)

            if skill_profile is not None:

                for name in getattr(skill_profile, "underformed", []) or []:

                    if name and name not in PLACEHOLDER_SKILLS:

                        weights[name] = weights.get(name, 0) + 3



            for skill in getattr(skill_profile, "items", []) or []:

                name = (skill.skill or "").strip()

                if not name or name in PLACEHOLDER_SKILLS or skill.average is None:

                    continue

                scores.setdefault(name, []).append(float(skill.average))

                if skill.level == "low":

                    weights[name] = weights.get(name, 0) + 2



            deficits = getattr(analysis, "deficits", None)

            if deficits is not None:

                for item in getattr(deficits, "skills", []) or []:

                    name = (item.checked_skill or "").strip()

                    if not name or name in PLACEHOLDER_SKILLS:

                        continue

                    weight = PRIORITY_WEIGHT.get(item.priority or "Low", 1)

                    weights[name] = weights.get(name, 0) + weight

                    if item.avg_completion_percent is not None:

                        scores.setdefault(name, []).append(float(item.avg_completion_percent))



        ranked: list[tuple[str, float]] = []

        for name, vals in scores.items():

            avg = sum(vals) / len(vals)

            score = avg - weights.get(name, 0) * 3.0

            ranked.append((name, score))

        ranked.sort(key=lambda pair: pair[1], reverse=not weak)

        return ranked


