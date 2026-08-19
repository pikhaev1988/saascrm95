from rest_framework import permissions, viewsets

from exams.models import Exam, ExamResult, Student, TaskResult
from exams.serializers import ExamResultSerializer, ExamSerializer, StudentSerializer, TaskResultSerializer


class ScopedQueryMixin:
    def apply_scope(self, qs):
        user = self.request.user
        if user.role == "school":
            return qs.filter(student__school_id=user.school_id)
        if user.role == "district":
            return qs.filter(student__school__district_id=user.district_id)
        return qs


class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExamSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Exam.objects.all()
    filterset_fields = ("exam_type", "year", "subject")


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ("school", "grade")
    search_fields = ("full_name", "external_id")

    def get_queryset(self):
        user = self.request.user
        qs = Student.objects.select_related("school", "school__district")
        if user.role == "school":
            return qs.filter(school_id=user.school_id)
        if user.role == "district":
            return qs.filter(school__district_id=user.district_id)
        return qs


class ExamResultViewSet(ScopedQueryMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ExamResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ("exam", "student")

    def get_queryset(self):
        qs = ExamResult.objects.select_related("student", "exam", "student__school")
        return self.apply_scope(qs)


class TaskResultViewSet(ScopedQueryMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = TaskResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ("exam", "student", "task_number", "value")

    def get_queryset(self):
        qs = TaskResult.objects.select_related("student", "exam")
        return self.apply_scope(qs)
from django.shortcuts import render

# Create your views here.
