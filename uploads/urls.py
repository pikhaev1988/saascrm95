from rest_framework.routers import DefaultRouter

from uploads.views import UploadSessionViewSet

router = DefaultRouter()
router.register(r"uploads", UploadSessionViewSet, basename="uploads")

urlpatterns = router.urls
