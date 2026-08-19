from rest_framework import serializers

from exams.models import Exam, ExamResult, Student, TaskResult


class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ("id", "exam_type", "code", "subject", "exam_date", "year")


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ("id", "school", "external_id", "full_name", "grade")


class ExamResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamResult
        fields = (
            "id",
            "student",
            "exam",
            "school_code",
            "student_name",
            "short_answer_tasks",
            "long_answer_tasks",
            "primary_score",
            "score",
            "total_score",
            "passed",
            "short_answer_raw",
            "source_row",
        )


class TaskResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResult
        fields = ("id", "student", "exam", "task_number", "value")
