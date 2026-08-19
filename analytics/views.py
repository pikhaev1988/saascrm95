from django.shortcuts import render
from rest_framework import permissions, views
from rest_framework.response import Response

from analytics.serializers import AnalyticsFilterSerializer
from analytics.services import exam_overview


def _scope_for_user(user, district_id=None, school_id=None):
    if user.role == "school":
        return {"student__school_id": user.school_id}
    if user.role == "district":
        return {"student__school__district_id": user.district_id}
    if school_id:
        return {"student__school_id": school_id}
    if district_id:
        return {"student__school__district_id": district_id}
    return {}


class AnalyticsAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        year = serializer.validated_data.get("year")
        district_id = serializer.validated_data.get("district_id")
        school_id = serializer.validated_data.get("school_id")
        scope = _scope_for_user(request.user, district_id=district_id, school_id=school_id)
        data = exam_overview(scope, year)
        return Response(data)


def dashboard_view(request):
    if not request.user.is_authenticated:
        return render(request, "registration/login.html")
    scope = _scope_for_user(request.user)
    data = exam_overview(scope)
    return render(request, "dashboard.html", {"metrics": data})
from django.shortcuts import render

# Create your views here.
