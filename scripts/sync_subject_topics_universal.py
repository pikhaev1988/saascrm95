"""
Универсальное обогащение тем/классов по всем предметам в data/ege_2026_enriched.json.

Сценарий:
1) Находит задания с неполными данными (placeholder-тема, пустые классы, невалидные классы).
2) Запрашивает GigaChat для восстановления:
   - topic (10-11)
   - topic_oge (5-9, если применимо)
   - grade_range / grade_range_oge
3) Применяет только валидные ответы с порогом confidence.

Пример запуска:
  python scripts/sync_subject_topics_universal.py --subject english --apply
  python scripts/sync_subject_topics_universal.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
ENRICHED = ROOT / "data" / "ege_2026_enriched.json"
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

PLACEHOLDER_RE = re.compile(
    r"(элемент содержания по спецификации|тематический блок по спецификации|контент по спецификации)",
    flags=re.I,
)


def norm_text(value: Any) -> str:
    text = str(value or "").replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip(" ;,.")
    return text


def normalize_grades(raw: Any) -> list[int]:
    if not isinstance(raw, list):
        return []
    out: set[int] = set()
    for item in raw:
        try:
            grade = int(item)
        except (TypeError, ValueError):
            continue
        if 1 <= grade <= 11:
            out.add(grade)
    return sorted(out)


def needs_enrichment(task: dict[str, Any]) -> bool:
    topic = norm_text(task.get("topic"))
    grades = normalize_grades(task.get("grade_range"))
    if not topic or PLACEHOLDER_RE.search(topic):
        return True
    if not grades:
        return True
    # Часто шумно заполнено "1,2,9,11" для ЕГЭ: это явный индикатор некорректной привязки.
    if any(g < 5 for g in grades):
        return True
    return False


def build_prompt(subject: str, tasks: list[dict[str, Any]]) -> str:
    schema = {
        "updates": [
            {
                "task": 1,
                "topic": "Краткая тема ЕГЭ (10-11)",
                "topic_oge": "Краткая тема ОГЭ (5-9) или пусто",
                "grade_range": [10, 11],
                "grade_range_oge": [5, 6, 7, 8, 9],
                "confidence": 0.0,
            }
        ]
    }
    return (
        "Ты методист ЕГЭ/ОГЭ. Нужна точечная нормализация каталога заданий.\n"
        "Верни ТОЛЬКО JSON.\n"
        "Требования:\n"
        "- topic: короткая человеко-понятная тема уровня ЕГЭ.\n"
        "- topic_oge: только если для этого задания есть релевантная база 5-9 классов.\n"
        "- grade_range: обычно 10-11 для ЕГЭ (или уже обоснованно уже).\n"
        "- grade_range_oge: только 5-9.\n"
        "- Никаких кодов вида 'п. 19.6.3'.\n"
        "- Никаких общих фраз типа 'элемент содержания по спецификации'.\n"
        "- confidence от 0 до 1.\n\n"
        f"Предмет: {subject}\n"
        f"Схема ответа: {json.dumps(schema, ensure_ascii=False)}\n"
        f"Задания для обновления: {json.dumps(tasks, ensure_ascii=False)}"
    )


def call_gigachat(model: str, prompt: str) -> dict[str, Any]:
    from users.ai import chat_completion_json, gigachat_configured

    if not gigachat_configured():
        raise SystemExit(
            "GigaChat: задай GIGACHAT_AUTH_KEY или GIGACHAT_CLIENT_ID + GIGACHAT_CLIENT_SECRET в .env"
        )
    payload = chat_completion_json(
        system_prompt=(
            "Ты возвращаешь только валидный JSON без markdown. "
            "Никаких комментариев и префиксов."
        ),
        user_prompt=prompt,
        temperature=0.1,
        model=model,
    )
    if not payload:
        raise RuntimeError("GigaChat вернул пустой или невалидный ответ.")
    return payload


def validate_update(item: dict[str, Any]) -> dict[str, Any] | None:
    try:
        task_num = int(item.get("task"))
    except (TypeError, ValueError):
        return None
    topic = norm_text(item.get("topic"))
    if not topic or PLACEHOLDER_RE.search(topic):
        return None
    grade_range = normalize_grades(item.get("grade_range"))
    grade_range_oge = normalize_grades(item.get("grade_range_oge"))
    topic_oge = norm_text(item.get("topic_oge"))
    conf = float(item.get("confidence", 0))
    return {
        "task": task_num,
        "topic": topic,
        "topic_oge": topic_oge,
        "grade_range": grade_range,
        "grade_range_oge": grade_range_oge,
        "confidence": conf,
    }


def apply_updates_for_subject(
    subject_payload: dict[str, Any],
    updates: list[dict[str, Any]],
    confidence_threshold: float,
) -> tuple[int, int]:
    accepted = 0
    review = 0
    by_task = {int(t.get("task")): t for t in subject_payload.get("tasks", []) if t.get("task") is not None}
    for item in updates:
        valid = validate_update(item)
        if not valid:
            continue
        task_num = valid["task"]
        target = by_task.get(task_num)
        if not target:
            continue
        conf = valid["confidence"]
        if conf < confidence_threshold:
            target["needs_review"] = True
            target["source"] = target.get("source") or "gigachat_enriched_pending_review"
            review += 1
            continue
        target["topic"] = valid["topic"]
        if valid["grade_range"]:
            target["grade_range"] = valid["grade_range"]
        if valid["topic_oge"]:
            target["topic_oge"] = valid["topic_oge"]
        if valid["grade_range_oge"]:
            target["grade_range_oge"] = valid["grade_range_oge"]
        target["source"] = "gigachat_enriched_v1"
        target["confidence"] = round(conf, 3)
        target["needs_review"] = conf < 0.8
        accepted += 1
    return accepted, review


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default="all", help="Код предмета (например english) или all")
    parser.add_argument("--model", default=os.getenv("GIGACHAT_MODEL", "GigaChat"))
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--confidence-threshold", type=float, default=0.65)
    parser.add_argument("--apply", action="store_true", help="Сохранить изменения в JSON")
    args = parser.parse_args()

    data = json.loads(ENRICHED.read_text(encoding="utf-8"))
    subjects = data.get("subjects", [])
    selected = [
        s for s in subjects if args.subject == "all" or s.get("subject") == args.subject
    ]
    if not selected:
        raise SystemExit(f"Предмет '{args.subject}' не найден.")

    total_candidates = 0
    total_accepted = 0
    total_review = 0

    for subj in selected:
        subject_key = str(subj.get("subject"))
        tasks = subj.get("tasks", [])
        candidates = []
        for task in tasks:
            if needs_enrichment(task):
                candidates.append(
                    {
                        "task": task.get("task"),
                        "topic": norm_text(task.get("topic")),
                        "topic_oge": norm_text(task.get("topic_oge")),
                        "grade_range": normalize_grades(task.get("grade_range")),
                        "grade_range_oge": normalize_grades(task.get("grade_range_oge")),
                    }
                )
        if not candidates:
            print(f"[{subject_key}] пропуск: кандидатов нет")
            continue

        total_candidates += len(candidates)
        print(f"[{subject_key}] кандидатов к обогащению: {len(candidates)}")

        subject_updates: list[dict[str, Any]] = []
        for idx in range(0, len(candidates), args.batch_size):
            batch = candidates[idx: idx + args.batch_size]
            prompt = build_prompt(subject_key, batch)
            try:
                ai_payload = call_gigachat(args.model, prompt)
            except Exception as exc:
                print(f"[{subject_key}] batch {idx // args.batch_size + 1}: ошибка GigaChat: {exc}")
                continue
            updates = ai_payload.get("updates", []) if isinstance(ai_payload, dict) else []
            if not isinstance(updates, list):
                continue
            subject_updates.extend(updates)

        accepted, review = apply_updates_for_subject(
            subj,
            subject_updates,
            confidence_threshold=args.confidence_threshold,
        )
        total_accepted += accepted
        total_review += review
        print(f"[{subject_key}] принято: {accepted}, помечено на review: {review}")

    print(
        f"ИТОГО: кандидатов={total_candidates}, обновлено={total_accepted}, review={total_review}, apply={args.apply}"
    )
    if args.apply:
        ENRICHED.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Сохранено: {ENRICHED}")
    else:
        print("Dry-run: файл не изменён. Добавь --apply для записи.")


if __name__ == "__main__":
    main()

