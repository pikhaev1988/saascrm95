from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from organizations.models import Ministry
from uploads.models import UploadSession
from uploads.serializers import UploadSessionSerializer
from uploads.services import import_organizations_from_excel
from uploads.tasks import process_upload


class UploadSessionViewSet(viewsets.ModelViewSet):
    serializer_class = UploadSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        user = self.request.user
        qs = UploadSession.objects.select_related("uploaded_by").order_by("-created_at")
        if user.role == "ministry":
            return qs
        return qs.filter(uploaded_by=user)

    def perform_create(self, serializer):
        session = serializer.save(uploaded_by=self.request.user)
        process_upload.delay(session.id)

    @action(detail=False, methods=["post"], url_path="import-organizations")
    def import_organizations(self, request):
        if request.user.role != "ministry":
            return Response({"detail": "Недостаточно прав"}, status=status.HTTP_403_FORBIDDEN)
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "Файл не передан"}, status=status.HTTP_400_BAD_REQUEST)
        ministry = request.user.ministry or Ministry.objects.first()
        if not ministry:
            return Response({"detail": "Создайте министерство"}, status=status.HTTP_400_BAD_REQUEST)
        stats = import_organizations_from_excel(file_obj, ministry)
        return Response({"status": "ok", **stats})
