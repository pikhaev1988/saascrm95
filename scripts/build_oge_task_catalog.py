"""
Генерация OГЭ-каталогов из data/ege_2026_enriched.json.

Создает:
- data/oge_json/oge_2026_enriched.json (агрегированный файл по всем предметам)
- data/oge_json/subjects/<subject>.json (отдельный файл по предмету)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from pypdf import PdfReader

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "ege_2026_enriched.json"
OGE_DIR = ROOT / "data" / "oge_json"
OGE_SUBJECTS_DIR = OGE_DIR / "subjects"
OGE_SPECS_DIR = ROOT / "fipi" / "oge"


SPEC_PREFIX_TO_SUBJECTS = {
    "БИ": ["biology"],
    "ГГ": ["geography"],
    "ИНФ": ["informatics"],
    "ИНЯЗ": ["english", "german", "french", "spanish", "chinese"],
    "ИС": ["history"],
    "ЛИ": ["literature"],
    "МА": ["math_basic"],
    "ОБ": ["social_studies"],
    "РУ": ["russian"],
    "ФИ": ["physics"],
    "ХИ": ["chemistry"],
}


def norm(value: Any) -> str:
    text = str(value or "").replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip(" ;,.")
    return text


def strip_codes(topic: str) -> str:
    text = norm(topic)
    text = re.sub(r"\b\d{1,2}\s*кл\.,?\s*п\.\s*[\d.]+\s*", "", text, flags=re.I)
    text = re.sub(r"\bп\.\s*[\d.]+\s*", "", text, flags=re.I)
    text = re.sub(r"\b\d+\.\d+\.\d+\.?\d*\b", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ;,.:-")
    return text


def parse_grades(raw: Any) -> list[int]:
    out: set[int] = set()
    if isinstance(raw, list):
        for item in raw:
            try:
                g = int(item)
            except (TypeError, ValueError):
                continue
            if 1 <= g <= 11:
                out.add(g)
    return sorted(out)


def oge_grades(task: dict[str, Any]) -> list[int]:
    direct = [g for g in parse_grades(task.get("grade_range_oge")) if 5 <= g <= 9]
    if direct:
        return direct
    filtered = [g for g in parse_grades(task.get("grade_range")) if 5 <= g <= 9]
    if filtered:
        return filtered
    return [9]


def oge_topic(task: dict[str, Any]) -> str:
    topic_oge = strip_codes(task.get("topic_oge"))
    if topic_oge:
        return topic_oge
    topic = strip_codes(task.get("topic"))
    if topic:
        return topic
    return "Тематический блок ОГЭ по спецификации"


def _spec_prefix_from_name(name: str) -> str:
    m = re.match(r"([А-ЯA-Z]+)-9", name.upper())
    return m.group(1) if m else ""


def _extract_total_tasks_from_pdf(pdf_path: Path) -> int | None:
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return None
    text = " ".join((page.extract_text() or "") for page in reader.pages)
    text = re.sub(r"\s+", " ", text)
    patterns = [
        r"Всего заданий\s*[–-]\s*(\d+)",
        r"Всего\s+в\s+работе\s+(\d+)\s+задан",
        r"Итого\s*[:–-]?\s*(\d+)\s*задан",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I)
        if m:
            try:
                value = int(m.group(1))
            except (TypeError, ValueError):
                continue
            if 1 <= value <= 200:
                return value
    return None


def load_spec_task_limits() -> dict[str, int]:
    limits: dict[str, int] = {}
    if not OGE_SPECS_DIR.exists():
        return limits
    for pdf in OGE_SPECS_DIR.glob("*.pdf"):
        prefix = _spec_prefix_from_name(pdf.name)
        if not prefix:
            continue
        total_tasks = _extract_total_tasks_from_pdf(pdf)
        if not total_tasks:
            continue
        for subject in SPEC_PREFIX_TO_SUBJECTS.get(prefix, []):
            limits[subject] = total_tasks
    return limits


def build_subject(subject_payload: dict[str, Any], task_limit: int | None) -> dict[str, Any]:
    subject = str(subject_payload.get("subject", "")).strip()
    tasks_out: list[dict[str, Any]] = []
    for task in subject_payload.get("tasks", []):
        try:
            task_num = int(task.get("task"))
        except (TypeError, ValueError):
            continue
        item: dict[str, Any] = {
            "task": task_num,
            "topic": oge_topic(task),
            "grade_range": oge_grades(task),
            "source": "oge_from_ege_enriched",
        }
        skill = task.get("skill")
        if skill:
            item["skill"] = skill
        tasks_out.append(item)
    tasks_out.sort(key=lambda x: x["task"])
    if task_limit:
        tasks_out = [x for x in tasks_out if 1 <= x["task"] <= task_limit]
        present = {x["task"] for x in tasks_out}
        for missing in range(1, task_limit + 1):
            if missing in present:
                continue
            tasks_out.append(
                {
                    "task": missing,
                    "topic": "Тема по спецификации ОГЭ (требуется методическая верификация)",
                    "grade_range": [9],
                    "source": "oge_spec_placeholder",
                    "needs_review": True,
                }
            )
        tasks_out.sort(key=lambda x: x["task"])
    return {
        "exam": "OGE_2026",
        "subject": subject,
        "tasks": tasks_out,
    }


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Не найден исходный файл: {SRC}")
    data = json.loads(SRC.read_text(encoding="utf-8"))
    subjects = data.get("subjects", [])
    if not isinstance(subjects, list) or not subjects:
        raise SystemExit("В исходном JSON отсутствует список subjects.")
    task_limits = load_spec_task_limits()

    OGE_SUBJECTS_DIR.mkdir(parents=True, exist_ok=True)
    for old in OGE_SUBJECTS_DIR.glob("*.json"):
        old.unlink()
    out_subjects: list[dict[str, Any]] = []
    total_tasks = 0

    for subject_payload in subjects:
        subject_code = str(subject_payload.get("subject", "")).strip()
        # Для ОГЭ нет отдельного предмета "math_profile".
        if subject_code == "math_profile":
            continue
        built = build_subject(subject_payload, task_limits.get(subject_code))
        out_subjects.append(built)
        total_tasks += len(built["tasks"])
        subject_file = OGE_SUBJECTS_DIR / f"{(built['subject'] or 'unknown_subject')}.json"
        subject_file.write_text(json.dumps(built, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    aggregate = {
        "exam": "OGE_2026",
        "provider": "FIPI",
        "source": "derived_from_ege_2026_enriched",
        "subjects": out_subjects,
    }
    (OGE_DIR / "oge_2026_enriched.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"OK: создано предметных файлов: {len(out_subjects)}")
    print(f"OK: всего заданий в OГЭ-каталоге: {total_tasks}")
    print(f"OK: применены лимиты из спецификаций для предметов: {', '.join(sorted(task_limits)) or 'нет'}")
    print(f"Папка: {OGE_DIR}")


if __name__ == "__main__":
    main()

