"""Resolve VPR Excel fixtures across Windows/Linux deploy encodings."""

from __future__ import annotations

from pathlib import Path


def fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures"


def resolve_f1_fixture() -> Path:
    """
    Prefer canonical F1 name; fall back to ASCII sample copy.
    Beget sync sometimes mangles Cyrillic filenames.
    """
    base = fixtures_dir()
    preferred = base / "Ф1_Индивидуальные_результаты.xlsx"
    if preferred.exists():
        return preferred
    sample = base / "vpr_f1_sample.xlsx"
    if sample.exists():
        return sample
    # Last resort: any xlsx that parses as f1 (by name heuristics)
    for p in sorted(base.glob("*.xlsx")):
        name = p.name.lower()
        if "f1" in name or "sample" in name:
            return p
    raise FileNotFoundError(f"No F1 VPR fixture under {base}")
