from rest_framework.permissions import BasePermission


class IsMinistry(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "ministry"


class IsDistrictOrHigher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in {"ministry", "district"}
