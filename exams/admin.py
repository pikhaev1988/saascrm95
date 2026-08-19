from django.contrib import admin

from exams.models import EgePassingThreshold, Exam, ExamResult, ExamTaskTopic, Student, TaskResult

admin.site.register(Exam)
admin.site.register(Student)


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = (
        "exam",
        "school_code",
        "student_name",
        "primary_score",
        "score",
        "passed",
    )
    search_fields = ("school_code", "student_name", "student__full_name", "student__external_id")
    list_filter = ("exam", "passed")

    def get_fields(self, request, obj=None):
        # For OGE we keep the form focused on grade workflow:
        # primary score + final grade only.
        if obj and obj.exam and obj.exam.exam_type == "oge":
            return (
                "student",
                "exam",
                "school_code",
                "student_name",
                "primary_score",
                "score",
                "passed",
            )
        return super().get_fields(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.exam and obj.exam.exam_type == "oge":
            return ("student", "exam", "school_code", "student_name")
        return super().get_readonly_fields(request, obj)


admin.site.register(TaskResult)


@admin.register(EgePassingThreshold)
class EgePassingThresholdAdmin(admin.ModelAdmin):
    list_display = ("year", "subject_key", "minimum_score", "minimum_grade")
    list_filter = ("year", "subject_key")
    search_fields = ("subject_key",)


@admin.register(ExamTaskTopic)
class ExamTaskTopicAdmin(admin.ModelAdmin):
    list_display = ("exam_type", "subject_key", "task_number", "topic")
    list_filter = ("exam_type", "subject_key")
    search_fields = ("subject_key", "topic")
