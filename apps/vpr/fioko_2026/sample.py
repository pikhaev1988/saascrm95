"""Утилиты выборки и границ отметок для FIOKO 2026 (Stage 7.1)."""

from __future__ import annotations

from typing import Any

from apps.vpr.analytics.thresholds import VPR_THRESHOLDS

GROUP_SAMPLE_MIN = 10


def group_sample_flags(sample_size: int) -> dict[str, Any]:
    """
    FIOKO 2026 §7: информативный групповой анализ при N >= 10.

    Возвращает:
      sample_status: INFORMATIVE | LIMITED_SAMPLE
      informative: bool
      sample_warning / informational_only — aliases для совместимости
    """
    n = int(sample_size or 0)
    cfg = (VPR_THRESHOLDS.get("fioko_2026") or {}).get("sample") or {}
    min_n = int(cfg.get("groups_informative_min") or GROUP_SAMPLE_MIN)
    informative = n >= min_n
    status = "INFORMATIVE" if informative else "LIMITED_SAMPLE"
    return {
        "sample_size": n,
        "sample_status": status,
        "informative": informative,
        "sample_warning": not informative,
        "informational_only": not informative,
        "threshold_min": min_n,
        "source": "FIOKO_2026",
    }


def limited_sample_wording(*, title: str, count: int) -> str:
    return (
        f"{title} — {count} обучающихся. "
        "Выборка недостаточна для информативного группового анализа "
        "по рекомендациям ФИОКО (менее 10 участников). "
        "Показатели приведены как дополнительная диагностическая информация "
        "и не используются как самостоятельное основание для управленческих выводов."
    )


def resolve_official_mark_boundaries(
    *,
    subject: str = "",
    parallel: int | None = None,
    academic_year: int | None = None,
    protocol=None,
) -> dict[str, float] | None:
    """
    Официальные границы перевода первичный балл → отметка.

    Источник: метаданные протокола / КИМ (если загружены).
    НЕ выводит границы из min(primary|mark) — это угадывание.

    Ожидаемый формат в protocol.extra / catalog:
      mark_boundaries: {"2->3": 7, "3->4": 12, "4->5": 18}
    или mark_scale: {"3_min": 7, "4_min": 12, "5_min": 18}
    """
    candidates: list[Any] = []
    if protocol is not None:
        for attr in ("extra", "metadata", "kim_meta", "source_meta"):
            val = getattr(protocol, attr, None)
            if isinstance(val, dict):
                candidates.append(val)
        upload = getattr(protocol, "upload", None)
        if upload is not None:
            extra = getattr(upload, "extra", None) or getattr(upload, "metadata", None)
            if isinstance(extra, dict):
                candidates.append(extra)

    for meta in candidates:
        bounds = _parse_boundaries(meta)
        if bounds:
            return bounds
    return None


def _parse_boundaries(meta: dict[str, Any]) -> dict[str, float] | None:
    raw = meta.get("mark_boundaries") or meta.get("score_boundaries") or meta.get("fioko_mark_boundaries")
    if isinstance(raw, dict):
        out: dict[str, float] = {}
        for key in ("2->3", "3->4", "4->5"):
            if key in raw and raw[key] is not None:
                try:
                    out[key] = float(raw[key])
                except (TypeError, ValueError):
                    return None
        if len(out) == 3:
            return out

    scale = meta.get("mark_scale") or meta.get("primary_to_mark")
    if isinstance(scale, dict):
        try:
            m3 = scale.get("3_min") or scale.get("mark_3_min") or scale.get("3")
            m4 = scale.get("4_min") or scale.get("mark_4_min") or scale.get("4")
            m5 = scale.get("5_min") or scale.get("mark_5_min") or scale.get("5")
            if m3 is None or m4 is None or m5 is None:
                return None
            return {"2->3": float(m3), "3->4": float(m4), "4->5": float(m5)}
        except (TypeError, ValueError):
            return None
    return None
