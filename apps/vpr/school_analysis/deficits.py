"""Объединение образовательных дефицитов школы."""

from __future__ import annotations

from collections import Counter, defaultdict

from apps.vpr.school_analysis.metrics import PLACEHOLDER_SKILLS, PLACEHOLDER_TOPICS, subject_name
from apps.vpr.school_analysis.schemas import DeficitPriorityBucket, SchoolDeficitsProfile

PRIORITIES = ("Critical", "High", "Medium", "Low")


class SchoolDeficitsAggregator:
    def analyze(self, analyses: list) -> SchoolDeficitsProfile:
        by_subject: dict[str, Counter] = defaultdict(Counter)
        by_topic: dict[str, Counter] = defaultdict(Counter)
        by_skill: dict[str, Counter] = defaultdict(Counter)
        priority_total: Counter = Counter()

        for analysis in analyses:
            subject = subject_name(analysis) or "—"
            deficits = analysis.deficits
            if deficits is None:
                continue
            for task in getattr(deficits, "tasks", []) or []:
                priority = task.priority or "Low"
                if priority not in PRIORITIES:
                    priority = "Low"
                priority_total[priority] += 1
                by_subject[subject][priority] += 1
                topic = (task.topic or "").strip()
                if topic and topic not in PLACEHOLDER_TOPICS:
                    by_topic[topic][priority] += 1
                skill = (task.checked_skill or "").strip()
                if skill and skill not in PLACEHOLDER_SKILLS:
                    by_skill[skill][priority] += 1

        def _rows(source: dict[str, Counter]) -> list[dict]:
            rows = []
            for name, counter in source.items():
                total = sum(counter.values())
                rows.append(
                    {
                        "name": name,
                        "total": total,
                        "Critical": counter.get("Critical", 0),
                        "High": counter.get("High", 0),
                        "Medium": counter.get("Medium", 0),
                        "Low": counter.get("Low", 0),
                    }
                )
            rows.sort(key=lambda row: (-row["Critical"], -row["High"], -row["total"], row["name"]))
            return rows

        return SchoolDeficitsProfile(
            by_subject=_rows(by_subject),
            by_topic=_rows(by_topic),
            by_skill=_rows(by_skill),
            by_priority=[
                DeficitPriorityBucket(priority=code, count=int(priority_total.get(code, 0)))
                for code in PRIORITIES
            ],
            total_critical=int(priority_total.get("Critical", 0)),
            total_high=int(priority_total.get("High", 0)),
            total_medium=int(priority_total.get("Medium", 0)),
            total_low=int(priority_total.get("Low", 0)),
        )
