"""Сериализация школьного аналитического профиля ВПР."""

from __future__ import annotations

from typing import Any

from apps.vpr.school_analysis.schemas import SchoolAnalysisResult


def serialize_school_analysis(result: SchoolAnalysisResult) -> dict[str, Any]:
    return result.to_dict()
