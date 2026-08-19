import json
import re
from pathlib import Path


SUBJECT_CODE_MAP = {
    "ая": "english",
    "би": "biology",
    "гг": "geography",
    "инф": "informatics",
    "иняз": "english",
    "ис": "history",
    "ия": "english",
    "кя": "chinese",
    "ли": "literature",
    "ма": "math_profile",
    "ня": "german",
    "об": "social_studies",
    "ру": "russian",
    "фи": "physics",
    "фя": "french",
    "хи": "chemistry",
}

TASK_ROW_RE = re.compile(r"(?m)^\s*(\d+(?:\s*[–-]\s*\d+)?)\s+")
GRADE_RE = re.compile(r"(\d{1,2})\s*кл", re.IGNORECASE)


def _subject_key_from_filename(filename: str) -> str | None:
    lowered = filename.lower().replace("ё", "е")
    if "ма" in lowered and "баз" in lowered:
        return "math_basic"
    if "ма" in lowered and "проф" in lowered:
        return "math_profile"
    match = re.search(r"(^|[_\-\s])(ая|би|гг|инф|иняз|ис|ия|кя|ли|ма|ня|об|ру|фи|фя|хи)(?=[_\-\s])", lowered)
    if not match:
        return None
    return SUBJECT_CODE_MAP.get(match.group(2))


def _extract_table_text(full_text: str) -> str:
    start_markers = [
        "Соответствие заданий КИМ ЕГЭ школьной программе",
        "№ \nзадания",
    ]
    end_markers = [
        "\n4. Подходы к отбору содержания",
        "\n5. Структура варианта КИМ ЕГЭ",
    ]

    start_idx = -1
    for marker in start_markers:
        idx = full_text.find(marker)
        if idx != -1:
            start_idx = idx
            break
    if start_idx == -1:
        return ""

    end_idx = len(full_text)
    for marker in end_markers:
        idx = full_text.find(marker, start_idx)
        if idx != -1:
            end_idx = min(end_idx, idx)
    return full_text[start_idx:end_idx]


def _expand_task_token(task_token: str) -> list[int]:
    cleaned = task_token.replace(" ", "")
    if "–" in cleaned:
        left, right = cleaned.split("–", 1)
        return list(range(int(left), int(right) + 1))
    if "-" in cleaned:
        left, right = cleaned.split("-", 1)
        return list(range(int(left), int(right) + 1))
    return [int(cleaned)]


def _extract_topic_from_row(row_text: str) -> str:
    text = row_text.replace("\u00a0", " ")
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    matches = re.findall(r"п\.\s*\d+(?:\.\d+)*\.\s*([А-Яа-яA-Za-zЁё][^.;]{3,140})", text)
    if matches:
        return matches[0].strip(" -")
    return "Элемент содержания по спецификации"


def extract_grade_ranges_by_subject(spec_dir: Path) -> dict[str, dict[int, dict[str, object]]]:
    by_subject: dict[str, dict[int, dict[str, object]]] = {}
    for path in sorted(spec_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        source_name = (payload.get("source", {}) or {}).get("filename", "")
        if "спец" not in source_name.lower():
            continue
        subject_key = _subject_key_from_filename(source_name)
        if not subject_key:
            continue
        text = (payload.get("document", {}) or {}).get("full_text", "")
        table_text = _extract_table_text(text)
        if not table_text:
            continue
        rows = list(TASK_ROW_RE.finditer(table_text))
        if not rows:
            continue

        by_subject.setdefault(subject_key, {})
        for idx, row in enumerate(rows):
            task_token = row.group(1)
            row_start = row.start()
            row_end = rows[idx + 1].start() if idx + 1 < len(rows) else len(table_text)
            row_text = table_text[row_start:row_end]
            grades = sorted({int(g) for g in GRADE_RE.findall(row_text)})
            topic = _extract_topic_from_row(row_text)
            for task_number in _expand_task_token(task_token):
                existing = by_subject[subject_key].setdefault(
                    task_number,
                    {"grade_range": set(), "topic": topic},
                )
                existing["grade_range"].update(grades)
                if existing.get("topic") == "Элемент содержания по спецификации" and topic:
                    existing["topic"] = topic

    normalized = {}
    for subject, tasks in sorted(by_subject.items()):
        normalized[subject] = {}
        for task, meta in sorted(tasks.items()):
            normalized[subject][task] = {
                "grade_range": sorted(meta["grade_range"]),
                "topic": meta.get("topic") or "Элемент содержания по спецификации",
            }
    return normalized


def build_enriched_catalog(base_catalog_path: Path, grade_map: dict[str, dict[int, dict[str, object]]]) -> dict:
    base_catalog = json.loads(base_catalog_path.read_text(encoding="utf-8"))
    for subject in base_catalog.get("subjects", []):
        subject_key = (subject.get("subject") or "").strip().lower()
        subject_grades = grade_map.get(subject_key, {})
        known_tasks = {item.get("task") for item in subject.get("tasks", []) if item.get("task") is not None}
        for task in subject.get("tasks", []):
            task_number = task.get("task")
            if not isinstance(task_number, int):
                continue
            inferred = subject_grades.get(task_number, {})
            if inferred:
                if inferred.get("grade_range"):
                    task["grade_range"] = inferred["grade_range"]
                if (not task.get("topic")) and inferred.get("topic"):
                    task["topic"] = inferred["topic"]
        for task_number, inferred in subject_grades.items():
            if task_number in known_tasks:
                continue
            subject.setdefault("tasks", []).append(
                {
                    "task": task_number,
                    "topic": inferred.get("topic") or "Элемент содержания по спецификации",
                    "grade_range": inferred.get("grade_range") or [],
                    "source": "fipi_spec",
                }
            )
        subject["tasks"] = sorted(subject.get("tasks", []), key=lambda item: item.get("task", 0))
    base_catalog["generated_from"] = "ege_2026_full + FIPI specs table"
    return base_catalog


def main():
    root = Path(__file__).resolve().parents[1]
    spec_dir = root / "data" / "fipi_json_clean"
    base_catalog_path = root / "data" / "ege_2026_full.json"
    grade_map_output = root / "data" / "task_grade_ranges_2026.json"
    enriched_output = root / "data" / "ege_2026_enriched.json"

    grade_map = extract_grade_ranges_by_subject(spec_dir)
    grade_map_output.write_text(json.dumps(grade_map, ensure_ascii=False, indent=2), encoding="utf-8")

    enriched = build_enriched_catalog(base_catalog_path, grade_map)
    enriched_output.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved grade map: {grade_map_output}")
    print(f"Saved enriched catalog: {enriched_output}")


if __name__ == "__main__":
    main()
