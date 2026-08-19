from rest_framework import viewsets

from users.models import User
from users.permissions import IsMinistry
from users.serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsMinistry]
    queryset = User.objects.select_related("ministry", "district", "school")
    filterset_fields = ("role", "district", "school")
    search_fields = ("username", "first_name", "last_name")
