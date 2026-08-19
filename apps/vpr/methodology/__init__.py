"""Methodology package — centralized FIOKO / SYSTEM / LOCAL rules."""

from apps.vpr.methodology.rules import (
    FIOKO_2026_RULES,
    SYSTEM_ANALYTICS_RULES,
    LOCAL_ANALYTICS_RULES,
    get_methodology_registry,
    rule_value,
)

__all__ = [
    "FIOKO_2026_RULES",
    "SYSTEM_ANALYTICS_RULES",
    "LOCAL_ANALYTICS_RULES",
    "get_methodology_registry",
    "rule_value",
]
