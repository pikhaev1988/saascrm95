from rest_framework import permissions, viewsets

from organizations.models import District, Ministry, School
from organizations.serializers import DistrictSerializer, MinistrySerializer, SchoolSerializer
from users.permissions import IsDistrictOrHigher, IsMinistry


class MinistryViewSet(viewsets.ModelViewSet):
    queryset = Ministry.objects.all()
    serializer_class = MinistrySerializer
    permission_classes = [IsMinistry]


class DistrictViewSet(viewsets.ModelViewSet):
    serializer_class = DistrictSerializer
    permission_classes = [IsDistrictOrHigher]
    filterset_fields = ("ministry",)
    search_fields = ("code", "name")

    def get_queryset(self):
        user = self.request.user
        qs = District.objects.select_related("ministry")
        if user.role == "district":
            return qs.filter(id=user.district_id)
        return qs


class SchoolViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ("district",)
    search_fields = ("code", "name")

    def get_queryset(self):
        user = self.request.user
        qs = School.objects.select_related("district", "district__ministry")
        if user.role == "school":
            return qs.filter(id=user.school_id)
        if user.role == "district":
            return qs.filter(district_id=user.district_id)
        return qs
from django.shortcuts import render

# Create your views here.
