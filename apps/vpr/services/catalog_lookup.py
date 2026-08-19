"""Сопоставление результатов протоколов со справочником заданий ВПР."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

from apps.vpr.models import VprTaskCatalogEntry

TASK_CODE_RE = re.compile(
    r"^(?P<num>\d+)(?:\.(?P<sub>\d+))?(?P<crit>[КKk]\d+)?$",
)


@dataclass(frozen=True, slots=True)
class VprTaskLookupKey:
    academic_year: int
    subject: str
    parallel: int
    task_code: str


@dataclass(frozen=True, slots=True)
class VprTaskCatalogInfo:
    """Нормализованные сведения из справочника (без аналитики)."""

    entry_id: int
    academic_year: int
    subject: str
    parallel: int
    task_number: int
    task_subnumber: str
    task_code: str
    max_score: int
    checked_skill: str
    fgos_result: str
    program_section: str
    topic: str
    topic_subsection: str
    difficulty: str
    task_type: str
    short_description: str
    normative_source: str
    official_code: str
    extra: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_subject(subject: str) -> str:
    return re.sub(r"\s+", " ", (subject or "").strip().lower().replace("ё", "е"))


def parse_task_code(raw: str | int | None) -> tuple[int | None, str, str]:
    """
    Разобрать код задания из протокола.
    Возвращает (номер, подномер, канонический_код).

    Поддерживает: 3, 3.1, 4К1, 4K2, 10.2K1, 8K3.
    """
    text = str(raw or "").strip().replace(" ", "")
    if not text:
        return None, "", ""
    text = text.replace("k", "К").replace("K", "К")
    match = TASK_CODE_RE.match(text)
    if not match:
        return None, "", text
    number = int(match.group("num"))
    sub = match.group("sub") or ""
    crit = (match.group("crit") or "").upper().replace("K", "К")
    if sub and crit:
        subnumber = f"{sub}{crit}"
        code = f"{number}.{sub}{crit}"
    elif crit:
        subnumber = crit
        code = f"{number}{crit}"
    elif sub:
        subnumber = sub
        code = f"{number}.{sub}"
    else:
        subnumber = ""
        code = str(number)
    return number, subnumber, code


def entry_to_info(entry: VprTaskCatalogEntry) -> VprTaskCatalogInfo:
    return VprTaskCatalogInfo(
        entry_id=entry.pk,
        academic_year=entry.academic_year,
        subject=entry.subject,
        parallel=entry.parallel,
        task_number=entry.task_number,
        task_subnumber=entry.task_subnumber or "",
        task_code=entry.display_code,
        max_score=int(entry.max_score or 0),
        checked_skill=entry.checked_skill or "",
        fgos_result=entry.fgos_result or "",
        program_section=entry.program_section or "",
        topic=entry.topic or "",
        topic_subsection=entry.topic_subsection or "",
        difficulty=entry.difficulty or "",
        task_type=entry.task_type or "",
        short_description=entry.short_description or "",
        normative_source=entry.normative_source or "",
        official_code=entry.official_code or "",
        extra=dict(entry.extra or {}),
    )


class VprTaskCatalogLookup:
    """
    Поиск записи справочника для любого результата ученика:
    предмет → класс → номер задания → метаданные.
    """

    def resolve(
        self,
        *,
        subject: str,
        parallel: int,
        academic_year: int,
        task_code: str | int,
    ) -> VprTaskCatalogInfo | None:
        result = self._resolve_exact(
            subject=subject,
            parallel=parallel,
            academic_year=academic_year,
            task_code=task_code,
        )
        if result is not None:
            return result
        # Fallback: тот же предмет/класс/код, другой учебный год
        return self._resolve_any_year(
            subject=subject,
            parallel=parallel,
            task_code=task_code,
            preferred_year=academic_year,
        )

    def _resolve_exact(
        self,
        *,
        subject: str,
        parallel: int,
        academic_year: int,
        task_code: str | int,
    ) -> VprTaskCatalogInfo | None:
        number, sub, code = parse_task_code(task_code)
        subject_norm = normalize_subject(subject)

        qs = VprTaskCatalogEntry.objects.filter(
            is_active=True,
            academic_year=academic_year,
            parallel=parallel,
        )
        return self._match_in_qs(qs, subject_norm=subject_norm, code=code, number=number, sub=sub)

    def _resolve_any_year(
        self,
        *,
        subject: str,
        parallel: int,
        task_code: str | int,
        preferred_year: int,
    ) -> VprTaskCatalogInfo | None:
        number, sub, code = parse_task_code(task_code)
        subject_norm = normalize_subject(subject)
        qs = VprTaskCatalogEntry.objects.filter(is_active=True, parallel=parallel).order_by(
            "-academic_year"
        )
        candidates = self._match_in_qs(
            qs, subject_norm=subject_norm, code=code, number=number, sub=sub, return_all=True
        )
        if not candidates:
            return None
        # Предпочитаем ближайший год
        candidates.sort(key=lambda e: (abs(e.academic_year - preferred_year), -e.academic_year))
        return entry_to_info(candidates[0])

    @staticmethod
    def _match_in_qs(
        qs,
        *,
        subject_norm: str,
        code: str,
        number: int | None,
        sub: str,
        return_all: bool = False,
    ) -> VprTaskCatalogInfo | None | list:
        found: list = []
        if code:
            for entry in qs.filter(task_code__iexact=code):
                if normalize_subject(entry.subject) == subject_norm:
                    if return_all:
                        found.append(entry)
                    else:
                        return entry_to_info(entry)

        if number is not None:
            candidates = qs.filter(task_number=number, task_subnumber__iexact=sub)
            for entry in candidates:
                if normalize_subject(entry.subject) == subject_norm:
                    if return_all:
                        found.append(entry)
                    else:
                        return entry_to_info(entry)
            if sub:
                for entry in qs.filter(task_number=number):
                    if normalize_subject(entry.subject) != subject_norm:
                        continue
                    if (entry.task_subnumber or "").upper().replace("K", "К") == sub.upper().replace(
                        "K", "К"
                    ):
                        if return_all:
                            found.append(entry)
                        else:
                            return entry_to_info(entry)
        if return_all:
            return found
        return None

    def resolve_many(
        self,
        *,
        subject: str,
        parallel: int,
        academic_year: int,
        task_codes: list[str],
    ) -> dict[str, VprTaskCatalogInfo | None]:
        return {
            str(code): self.resolve(
                subject=subject,
                parallel=parallel,
                academic_year=academic_year,
                task_code=code,
            )
            for code in task_codes
        }


def lookup_task_catalog(
    *,
    subject: str,
    parallel: int,
    academic_year: int,
    task_code: str | int,
) -> VprTaskCatalogInfo | None:
    """Публичная точка входа для будущей аналитики."""
    return VprTaskCatalogLookup().resolve(
        subject=subject,
        parallel=parallel,
        academic_year=academic_year,
        task_code=task_code,
    )
