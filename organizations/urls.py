from rest_framework.routers import DefaultRouter

from organizations.views import DistrictViewSet, MinistryViewSet, SchoolViewSet

router = DefaultRouter()
router.register(r"ministries", MinistryViewSet, basename="ministries")
router.register(r"districts", DistrictViewSet, basename="districts")
router.register(r"schools", SchoolViewSet, basename="schools")

urlpatterns = router.urls
