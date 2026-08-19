"""Единый evidence-слой VPR analytics (глобальный для всех протоколов)."""

from __future__ import annotations

from apps.vpr.evidence.envelope import EvidenceEnvelope, build_evidence
from apps.vpr.evidence.statuses import EvidenceStatus, CauseType, AnalyticalOrigin

__all__ = [
    "EvidenceStatus",
    "CauseType",
    "AnalyticalOrigin",
    "EvidenceEnvelope",
    "build_evidence",
]
