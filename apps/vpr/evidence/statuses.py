"""Статусы доказательности и происхождения аналитики (глобальный контракт)."""

from __future__ import annotations

from enum import Enum


class EvidenceStatus(str, Enum):
    ESTABLISHED = "ESTABLISHED"
    INFORMATIVE = "INFORMATIVE"
    LIMITED_SAMPLE = "LIMITED_SAMPLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    HYPOTHESIS = "HYPOTHESIS"
    # Stage 10 aliases (TZ DIAGNOSTIC/CONFIRMED)
    DIAGNOSTIC = "DIAGNOSTIC"  # ≈ INFORMATIVE / single-task difficulty
    CONFIRMED = "CONFIRMED"  # ≈ ESTABLISHED multi-task deficit


# Mapping TZ wording → internal statuses
EVIDENCE_LEVEL_ALIASES = {
    "DIAGNOSTIC": EvidenceStatus.INFORMATIVE,
    "CONFIRMED": EvidenceStatus.ESTABLISHED,
}


class CauseType(str, Enum):
    FACT = "FACT"
    HYPOTHESIS = "HYPOTHESIS"


class AnalyticalOrigin(str, Enum):
    FIOKO = "FIOKO"
    FIOKO_2026 = "FIOKO_2026"
    SYSTEM_ANALYTICS = "SYSTEM_ANALYTICS"
    LOCAL_ANALYTICS = "LOCAL_ANALYTICS"


# Запрещённые автоматические причинно-следственные шаблоны из одного %
FORBIDDEN_AUTO_CAUSE_PHRASES = (
    "учитель недостаточно",
    "педагог недостаточно",
    "методика неэффективна",
    "система обучения не обеспечивает",
    "учитель не сформировал",
    "педагог не сформировал",
)
