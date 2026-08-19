"""Реестр протоколов ВПР: фильтры, сортировка, пагинация."""

from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Q, QuerySet

from apps.vpr.access import scoped_protocols_qs
from apps.vpr.models import VprProtocol, VprUploadStatus

SORT_FIELDS = {
    "year": "academic_year",
    "subject": "subject",
    "class": "parallel",
    "exam_date": "exam_date",
    "org": "organization_name",
    "participants": "participants_count",
    "max_score": "max_primary_score",
    "uploaded": "upload__created_at",
    "status": "upload__status",
}

DEFAULT_SORT = "-uploaded"
PAGE_SIZE = 20


def filter_protocols(qs: QuerySet[VprProtocol], params) -> QuerySet[VprProtocol]:
    q = (params.get("q") or "").strip()
    subject = (params.get("subject") or "").strip()
    parallel = (params.get("parallel") or "").strip()
    year = (params.get("year") or "").strip()
    organization = (params.get("organization") or "").strip()
    status = (params.get("status") or "").strip()

    if q:
        q_filter = (
            Q(subject__icontains=q)
            | Q(organization_name__icontains=q)
            | Q(organization_code__icontains=q)
            | Q(source_title__icontains=q)
        )
        if q.isdigit():
            q_filter |= Q(parallel=int(q)) | Q(academic_year=int(q))
        qs = qs.filter(q_filter)

    if subject:
        qs = qs.filter(subject__icontains=subject)
    if parallel.isdigit():
        qs = qs.filter(parallel=int(parallel))
    if year.isdigit():
        qs = qs.filter(academic_year=int(year))
    if organization:
        qs = qs.filter(
            Q(organization_name__icontains=organization)
            | Q(organization_code__icontains=organization)
        )
    if status and status in {c.value for c in VprUploadStatus}:
        qs = qs.filter(upload__status=status)

    return qs


def sort_protocols(qs: QuerySet[VprProtocol], sort: str | None) -> QuerySet[VprProtocol]:
    raw = (sort or DEFAULT_SORT).strip() or DEFAULT_SORT
    descending = raw.startswith("-")
    key = raw[1:] if descending else raw
    field = SORT_FIELDS.get(key, SORT_FIELDS["uploaded"])
    order = f"-{field}" if descending else field
    return qs.order_by(order, "-id")


def paginate_protocols(qs: QuerySet[VprProtocol], page: str | int | None, *, per_page: int = PAGE_SIZE):
    paginator = Paginator(qs, per_page)
    return paginator.get_page(page)


def registry_filter_choices(user) -> dict:
    base = scoped_protocols_qs(user)
    subjects = list(
        base.order_by("subject").values_list("subject", flat=True).distinct()
    )
    years = list(
        base.order_by("-academic_year").values_list("academic_year", flat=True).distinct()
    )
    parallels = list(
        base.order_by("parallel").values_list("parallel", flat=True).distinct()
    )
    organizations = list(
        base.exclude(organization_name="")
        .order_by("organization_name")
        .values_list("organization_name", flat=True)
        .distinct()[:100]
    )
    return {
        "subjects": subjects,
        "years": years,
        "parallels": parallels,
        "organizations": organizations,
        "statuses": list(VprUploadStatus.choices),
    }


def build_registry(user, params) -> dict:
    qs = scoped_protocols_qs(user)
    qs = filter_protocols(qs, params)
    sort = (params.get("sort") or DEFAULT_SORT).strip() or DEFAULT_SORT
    qs = sort_protocols(qs, sort)
    page_obj = paginate_protocols(qs, params.get("page"))
    return {
        "page_obj": page_obj,
        "protocols": page_obj.object_list,
        "total_count": page_obj.paginator.count,
        "sort": sort,
        "filters": {
            "q": (params.get("q") or "").strip(),
            "subject": (params.get("subject") or "").strip(),
            "parallel": (params.get("parallel") or "").strip(),
            "year": (params.get("year") or "").strip(),
            "organization": (params.get("organization") or "").strip(),
            "status": (params.get("status") or "").strip(),
        },
        "choices": registry_filter_choices(user),
    }
