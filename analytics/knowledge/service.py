from __future__ import annotations

from pathlib import Path

from django.core.cache import cache

from analytics.knowledge.parser import infer_difficulty, parse_topic_text
from analytics.knowledge_models import TaskKnowledge
from exams.models import ExamTaskTopic
from users.task_topics import (
    is_usable_catalog_topic,
    load_subject_task_catalog,
    part2_start_task,
    subject_key,
    subject_key_candidates,
    topic_for_task,
)
from users.task_classification import _official_record as _catalog_official_record


CACHE_TTL = 86400
GLOBAL_SKILLS: dict[str, str] = {}

CATALOG_KEY_TO_SUBJECT_NAME: dict[str, str] = {
    "russian": "Русский язык",
    "math_basic": "Математика",
    "math_profile": "Математика профильная",
    "physics": "Физика",
    "chemistry": "Химия",
    "biology": "Биология",
    "geography": "География",
    "history": "История",
    "social_studies": "Обществознание",
    "literature": "Литература",
    "informatics": "Информатика",
    "english": "Английский язык",
    "german": "Немецкий язык",
    "french": "Французский язык",
    "spanish": "Испанский язык",
    "chinese": "Китайский язык",
}


def _load_global_skills() -> dict[str, str]:
    global GLOBAL_SKILLS
    if GLOBAL_SKILLS:
        return GLOBAL_SKILLS
    from json import loads

    path = Path(__file__).resolve().parents[2] / "data" / "ege_2026_enriched.json"
    if path.exists():
        payload = loads(path.read_text(encoding="utf-8"))
        GLOBAL_SKILLS = {
            str(item.get("code", "")).strip(): str(item.get("name", "")).strip()
            for item in payload.get("global_skills", [])
            if item.get("code")
        }
    return GLOBAL_SKILLS


def _skill_name(skill_code: str, fallback: str) -> str:
    if not skill_code:
        return fallback
    return _load_global_skills().get(skill_code, fallback)


def _manual_override(exam_type: str, subject_key_value: str, task_number: int) -> dict | None:
    row = ExamTaskTopic.objects.filter(
        exam_type=exam_type, subject_key=subject_key_value, task_number=task_number
    ).first()
    if not row:
        return None
    return {"topic": row.topic, "grade_range": row.grade_range or []}


def _subject_display_name(subject_key_value: str) -> str:
    return CATALOG_KEY_TO_SUBJECT_NAME.get(subject_key_value, subject_key_value.replace("_", " ").title())


def _resolve_index_topic(
    *,
    exam_type: str,
    subject_key_value: str,
    task_number: int,
    topic_raw: str,
    grade_range: list[int],
) -> tuple[str, list[int]]:
    subject_name = _subject_display_name(subject_key_value)
    resolved = topic_for_task(subject_name, task_number, exam_type)

    if is_usable_catalog_topic(topic_raw):
        parsed_probe = parse_topic_text(
            topic_raw,
            grade_range,
            subject_key=subject_key_value,
            exam_type=exam_type,
        )
        if is_usable_catalog_topic(parsed_probe.topic):
            return topic_raw, grade_range

    if is_usable_catalog_topic(resolved):
        return resolved, grade_range

    return resolved, grade_range


class TaskKnowledgeIndexer:
    """Индексация базы знаний из официальных каталогов ФИПИ (enriched JSON)."""

    def index_all(self, document_year: int = 2026) -> dict[str, int]:
        stats = {"ege": 0, "oge": 0, "updated": 0}
        for exam_type in ("ege", "oge"):
            catalog = load_subject_task_catalog(exam_type)
            for subject_key_value, tasks in catalog.items():
                records = self._build_subject_records(exam_type, subject_key_value, tasks, document_year)
                self._apply_trajectory(records)
                for record in records:
                    obj, created = TaskKnowledge.objects.update_or_create(
                        exam_type=exam_type,
                        subject_key=subject_key_value,
                        task_number=record["task_number"],
                        document_year=document_year,
                        defaults=record,
                    )
                    stats[exam_type] += 1
                    if not created:
                        stats["updated"] += 1
                    cache.delete(
                        TaskKnowledgeService._cache_key(
                            exam_type, subject_key_value, record["task_number"], document_year
                        )
                    )
        return stats

    def _build_subject_records(
        self, exam_type: str, subject_key_value: str, tasks: dict, document_year: int
    ) -> list[dict]:
        part_boundary = part2_start_task(exam_type, subject_key_value)
        records: list[dict] = []
        for task_number, meta in sorted(tasks.items(), key=lambda item: int(item[0])):
            task_number = int(task_number)
            if exam_type == "oge":
                topic_raw = (meta.get("topic_oge") or meta.get("topic") or "").strip()
                grade_range = list(meta.get("grade_range_oge") or meta.get("grade_range") or [])
            else:
                topic_raw = (meta.get("topic") or "").strip()
                grade_range = list(meta.get("grade_range") or [])

            manual = _manual_override(exam_type, subject_key_value, task_number)
            if manual and manual.get("topic"):
                topic_raw = manual["topic"]
                if manual.get("grade_range"):
                    grade_range = manual["grade_range"]

            topic_for_parse, grade_range = _resolve_index_topic(
                exam_type=exam_type,
                subject_key_value=subject_key_value,
                task_number=task_number,
                topic_raw=topic_raw,
                grade_range=grade_range,
            )
            parsed = parse_topic_text(
                topic_for_parse,
                grade_range,
                subject_key=subject_key_value,
                exam_type=exam_type,
            )

            subject_name = _subject_display_name(subject_key_value)
            if not is_usable_catalog_topic(parsed.topic):
                parsed.topic = topic_for_task(subject_name, task_number, exam_type)
                parsed.skill_text = parsed.topic

            skill_code = str(meta.get("skill") or "").strip()
            # Official catalog kim.part has priority
            _cat_rec = _catalog_official_record(
                _subject_display_name(subject_key_value), task_number, exam_type, document_year,
            )
            _cat_kim_part = int((_cat_rec.get("kim") or {}).get("part") or 0) if _cat_rec else 0
            if _cat_kim_part in (1, 2):
                exam_part = _cat_kim_part
            else:
                exam_part = 2 if task_number >= part_boundary else 1
            confidence = float(meta.get("confidence") or 0.85)
            source = str(meta.get("source") or "ege_2026_enriched")

            records.append(
                {
                    "task_number": task_number,
                    "official_task_name": f"Задание №{task_number}",
                    "section": parsed.section,
                    "subsection": parsed.subsection,
                    "topic": parsed.topic,
                    "subtopic": parsed.subtopic,
                    "fgos_class_start": parsed.fgos_class_start,
                    "fgos_class_repeat": parsed.fgos_class_repeat,
                    "fgos_classes": parsed.fgos_classes,
                    "fgos_exam_class": 11 if exam_type == "ege" else 9,
                    "fipi_content_code": parsed.fipi_content_code,
                    "requirement_code": parsed.requirement_code,
                    "skill": skill_code,
                    "skill_name": _skill_name(skill_code, parsed.skill_text),
                    "competency": parsed.skill_text,
                    "difficulty": infer_difficulty(task_number, exam_part, part_boundary),
                    "exam_part": exam_part,
                    "max_score": None,
                    "related_tasks": [],
                    "previous_topics": [],
                    "next_topics": [],
                    "teaching_hours": None,
                    "recommended_practice_hours": None,
                    "recommended_control": "",
                    "expected_growth": None,
                    "source_document": source,
                    "document_version": str(document_year),
                    "confidence": confidence,
                    "raw_payload": meta,
                }
            )
        return records

    def _apply_trajectory(self, records: list[dict]) -> None:
        topics_by_task = {r["task_number"]: r["topic"] for r in records}
        sections_by_task = {
            r["task_number"]: (r.get("section") or "", r.get("subsection") or "") for r in records
        }
        skills_by_task = {r["task_number"]: r["skill"] for r in records if r.get("skill")}

        for record in records:
            task_num = record["task_number"]
            skill = record.get("skill")
            _section, subsection = sections_by_task.get(task_num, ("", ""))

            related = {n for n, s in skills_by_task.items() if s and s == skill and n != task_num}
            for n, (sec, sub) in sections_by_task.items():
                if n != task_num and subsection and sub == subsection:
                    related.add(n)
                elif n != task_num and sec and sec == _section and not subsection:
                    related.add(n)
            record["related_tasks"] = sorted(related)[:12]

            prev_topics: list[str] = []
            if subsection:
                for n in range(1, task_num):
                    if sections_by_task.get(n, ("", ""))[1] == subsection and is_usable_catalog_topic(
                        topics_by_task.get(n, "")
                    ):
                        prev_topics.append(topics_by_task[n])
            if not prev_topics:
                for n in range(1, task_num):
                    if is_usable_catalog_topic(topics_by_task.get(n, "")):
                        prev_topics.append(topics_by_task[n])
            record["previous_topics"] = list(dict.fromkeys(prev_topics))[-4:]

            next_topics = []
            for n in range(task_num + 1, task_num + 8):
                topic = topics_by_task.get(n, "")
                if is_usable_catalog_topic(topic):
                    next_topics.append(topic)
            record["next_topics"] = next_topics[:4]


class TaskKnowledgeService:
    def __init__(self, document_year: int = 2026):
        self.document_year = document_year

    @staticmethod
    def _cache_key(exam_type: str, subject_key_value: str, task_number: int, year: int) -> str:
        return f"task_knowledge:v1:{exam_type}:{subject_key_value}:{task_number}:{year}"

    def get(
        self,
        subject_name: str,
        task_number: int,
        exam_type: str = "ege",
    ) -> TaskKnowledge | None:
        sk = subject_key(subject_name, exam_type)
        candidates = subject_key_candidates(subject_name, exam_type) or [sk]

        for candidate in candidates:
            cached = cache.get(self._cache_key(exam_type, candidate, task_number, self.document_year))
            if cached:
                return cached

            row = (
                TaskKnowledge.objects.filter(
                    exam_type=exam_type,
                    subject_key=candidate,
                    task_number=task_number,
                    document_year=self.document_year,
                )
                .first()
            )
            if row:
                cache.set(
                    self._cache_key(exam_type, candidate, task_number, self.document_year),
                    row,
                    CACHE_TTL,
                )
                return row
        return None

    def get_or_index(
        self,
        subject_name: str,
        task_number: int,
        exam_type: str = "ege",
    ) -> TaskKnowledge | None:
        row = self.get(subject_name, task_number, exam_type)
        if row:
            return row
        if not TaskKnowledge.objects.exists():
            TaskKnowledgeIndexer().index_all(self.document_year)
        return self.get(subject_name, task_number, exam_type)


def get_task_knowledge(subject_name: str, task_number: int, exam_type: str = "ege") -> TaskKnowledge | None:
    return TaskKnowledgeService().get_or_index(subject_name, task_number, exam_type)
