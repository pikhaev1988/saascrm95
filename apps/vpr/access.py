"""Проверка доступа к данным модуля ВПР."""

from __future__ import annotations

from apps.vpr.models import VprProtocol, VprUpload
from organizations.models import School


def user_school(user) -> School | None:
    if getattr(user, "school_id", None):
        return user.school
    username = (getattr(user, "username", "") or "").strip()
    if username:
        return School.objects.filter(code=username).first()
    return None


def can_access_upload(user, upload: VprUpload) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, "role", None)
    if role == "school":
        school = user_school(user)
        return bool(school and upload.school_id == school.id)
    if role == "district":
        if upload.district_id and user.district_id == upload.district_id:
            return True
        if upload.school_id and upload.school and upload.school.district_id == user.district_id:
            return True
        return False
    return upload.uploaded_by_id == user.id


def can_access_protocol(user, protocol: VprProtocol) -> bool:
    return can_access_upload(user, protocol.upload)


def scoped_uploads_qs(user):
    """Загрузки ВПР в зоне ответственности пользователя."""
    from django.db.models import Q

    qs = VprUpload.objects.select_related(
        "protocol",
        "uploaded_by",
        "school",
        "district",
    )
    if user.is_superuser:
        return qs
    role = getattr(user, "role", None)
    if role == "school":
        school = user_school(user)
        if not school:
            return qs.none()
        return qs.filter(school=school)
    if role == "district" and user.district_id:
        return qs.filter(Q(district_id=user.district_id) | Q(school__district_id=user.district_id))
    return qs.filter(uploaded_by=user)


def scoped_protocols_qs(user):
    """Протоколы ВПР в зоне ответственности пользователя."""
    from django.db.models import Q

    qs = VprProtocol.objects.select_related(
        "upload",
        "upload__uploaded_by",
        "school",
    )
    if user.is_superuser:
        return qs
    role = getattr(user, "role", None)
    if role == "school":
        school = user_school(user)
        if not school:
            return qs.none()
        return qs.filter(school=school)
    if role == "district" and user.district_id:
        return qs.filter(Q(school__district_id=user.district_id) | Q(upload__district_id=user.district_id))
    return qs.filter(upload__uploaded_by=user)
