"""Evidence envelope — обязательная обёртка аналитического вывода."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from apps.vpr.evidence.statuses import AnalyticalOrigin, EvidenceStatus
from apps.vpr.fioko_2026.sample import GROUP_SAMPLE_MIN, group_sample_flags


@dataclass(slots=True)
class EvidenceEnvelope:
    evidence_status: str
    analytical_origin: str
    source_metrics: list[str] = field(default_factory=list)
    source_tasks: list[str] = field(default_factory=list)
    sample_size: int | None = None
    confidence_note: str = ""
    limitations: str = ""
    allow_management_conclusion: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_evidence(
    *,
    status: EvidenceStatus | str,
    origin: AnalyticalOrigin | str,
    source_metrics: list[str] | None = None,
    source_tasks: list[str] | None = None,
    sample_size: int | None = None,
    confidence_note: str = "",
    limitations: str = "",
    allow_management_conclusion: bool | None = None,
) -> EvidenceEnvelope:
    st = str(status)
    # Sample gate: N<10 → LIMITED_SAMPLE, no managerial conclusion
    if sample_size is not None and int(sample_size) < GROUP_SAMPLE_MIN:
        flags = group_sample_flags(int(sample_size))
        st = EvidenceStatus.LIMITED_SAMPLE
        if not limitations:
            limitations = (
                f"Выборка N={sample_size} < {GROUP_SAMPLE_MIN}: "
                "только диагностическая информация."
            )
        if allow_management_conclusion is None:
            allow_management_conclusion = False
    elif allow_management_conclusion is None:
        allow_management_conclusion = st in {
            EvidenceStatus.ESTABLISHED,
            EvidenceStatus.INFORMATIVE,
        }

    if st in {
        EvidenceStatus.INSUFFICIENT_DATA,
        EvidenceStatus.NOT_AVAILABLE,
        EvidenceStatus.HYPOTHESIS,
        EvidenceStatus.LIMITED_SAMPLE,
    }:
        allow_management_conclusion = False

    return EvidenceEnvelope(
        evidence_status=st,
        analytical_origin=str(origin),
        source_metrics=list(source_metrics or []),
        source_tasks=list(source_tasks or []),
        sample_size=sample_size,
        confidence_note=confidence_note,
        limitations=limitations,
        allow_management_conclusion=bool(allow_management_conclusion),
    )


def hypothesis_wording(claim: str) -> str:
    """Обернуть причинную гипотезу в нейтральную формулировку."""
    text = (claim or "").strip()
    if not text:
        return (
            "Возможная причина требует дополнительной проверки; "
            "по данным ВПР непосредственно не устанавливается."
        )
    low = text.lower()
    if low.startswith("возможн") or "требует дополнительной проверки" in low:
        return text
    return (
        f"Возможная причина: {text} "
        "Требует дополнительной проверки; по данным ВПР непосредственно не устанавливается."
    )
