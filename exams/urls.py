from rest_framework.routers import DefaultRouter

from exams.views import ExamResultViewSet, ExamViewSet, StudentViewSet, TaskResultViewSet

router = DefaultRouter()
router.register(r"exams", ExamViewSet, basename="exams")
router.register(r"students", StudentViewSet, basename="students")
router.register(r"exam-results", ExamResultViewSet, basename="exam-results")
router.register(r"task-results", TaskResultViewSet, basename="task-results")

urlpatterns = router.urls
