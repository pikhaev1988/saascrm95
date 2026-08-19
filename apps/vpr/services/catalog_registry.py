"""Фильтры и пагинация списка справочника заданий ВПР."""

from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Q, QuerySet

from apps.vpr.models import VprTaskCatalogEntry

SORT_FIELDS = {
    "year": "academic_year",
    "subject": "subject",
    "class": "parallel",
    "number": "task_number",
    "topic": "topic",
    "skill": "checked_skill",
    "difficulty": "difficulty",
}
DEFAULT_SORT = "year"
PAGE_SIZE = 25


def filter_catalog(qs: QuerySet[VprTaskCatalogEntry], params) -> QuerySet[VprTaskCatalogEntry]:
    q = (params.get("q") or "").strip()
    subject = (params.get("subject") or "").strip()
    parallel = (params.get("parallel") or "").strip()
    year = (params.get("year") or "").strip()
    difficulty = (params.get("difficulty") or "").strip()

    qs = qs.filter(is_active=True)
    if q:
        q_filter = (
            Q(subject__icontains=q)
            | Q(topic__icontains=q)
            | Q(checked_skill__icontains=q)
            | Q(task_code__icontains=q)
            | Q(program_section__icontains=q)
            | Q(short_description__icontains=q)
        )
        if q.isdigit():
            q_filter |= Q(parallel=int(q)) | Q(academic_year=int(q)) | Q(task_number=int(q))
        qs = qs.filter(q_filter)
    if subject:
        qs = qs.filter(subject__icontains=subject)
    if parallel.isdigit():
        qs = qs.filter(parallel=int(parallel))
    if year.isdigit():
        qs = qs.filter(academic_year=int(year))
    if difficulty:
        qs = qs.filter(difficulty__icontains=difficulty)
    return qs


def sort_catalog(qs: QuerySet[VprTaskCatalogEntry], sort: str | None) -> QuerySet[VprTaskCatalogEntry]:
    raw = (sort or DEFAULT_SORT).strip() or DEFAULT_SORT
    descending = raw.startswith("-")
    key = raw[1:] if descending else raw
    field = SORT_FIELDS.get(key, "academic_year")
    order = f"-{field}" if descending else field
    return qs.order_by(order, "subject", "parallel", "task_number", "task_subnumber", "id")


def build_catalog_list(params) -> dict:
    qs = VprTaskCatalogEntry.objects.all()
    qs = filter_catalog(qs, params)
    sort = (params.get("sort") or DEFAULT_SORT).strip() or DEFAULT_SORT
    qs = sort_catalog(qs, sort)
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(params.get("page"))
    base = VprTaskCatalogEntry.objects.filter(is_active=True)
    return {
        "page_obj": page_obj,
        "entries": page_obj.object_list,
        "total_count": paginator.count,
        "sort": sort,
        "filters": {
            "q": (params.get("q") or "").strip(),
            "subject": (params.get("subject") or "").strip(),
            "parallel": (params.get("parallel") or "").strip(),
            "year": (params.get("year") or "").strip(),
            "difficulty": (params.get("difficulty") or "").strip(),
        },
        "choices": {
            "subjects": list(base.order_by("subject").values_list("subject", flat=True).distinct()),
            "years": list(base.order_by("-academic_year").values_list("academic_year", flat=True).distinct()),
            "parallels": list(base.order_by("parallel").values_list("parallel", flat=True).distinct()),
            "difficulties": list(
                base.exclude(difficulty="")
                .order_by("difficulty")
                .values_list("difficulty", flat=True)
                .distinct()
            ),
        },
    }
