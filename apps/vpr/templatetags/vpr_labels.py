"""Подписи для интерфейса ВПР: перевод внутренних кодов в русский текст."""

from __future__ import annotations

from django import template

from apps.vpr.labels import (
    label_mastery,
    label_priority,
    label_risk,
    label_school_risk,
    label_status,
    label_trend,
)

register = template.Library()


@register.filter(name="vpr_risk")
def vpr_risk(value) -> str:
    return label_risk(value)


@register.filter(name="vpr_school_risk")
def vpr_school_risk(value) -> str:
    return label_school_risk(value)


@register.filter(name="vpr_priority")
def vpr_priority(value) -> str:
    return label_priority(value)


@register.filter(name="vpr_trend")
def vpr_trend(value) -> str:
    return label_trend(value)


@register.filter(name="vpr_mastery")
def vpr_mastery(value) -> str:
    return label_mastery(value)


@register.filter(name="vpr_status")
def vpr_status(value) -> str:
    return label_status(value)
