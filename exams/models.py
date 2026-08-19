from django.db import models


class ExamType(models.TextChoices):
    EGE = "ege", "ЕГЭ"
    OGE = "oge", "ОГЭ"
    VPR = "vpr", "ВПР"


class EgeSubjectKey(models.TextChoices):
    RUSSIAN = "russian", "Русский язык"
    MATH_PROFILE = "math_profile", "Математика (профиль)"
    MATH_BASIC = "math_basic", "Математика (база)"
    SOCIAL = "social", "Обществознание"
    INFORMATICS = "informatics", "Информатика"
    PHYSICS = "physics", "Физика"
    CHEMISTRY = "chemistry", "Химия"
    BIOLOGY = "biology", "Биология"
    HISTORY = "history", "История"
    LITERATURE = "literature", "Литература"
    GEOGRAPHY = "geography", "География"
    FOREIGN_LANGUAGE = "foreign_language", "Иностранный язык"


class Exam(models.Model):
    exam_type = models.CharField(max_length=8, choices=ExamType.choices)
    code = models.CharField(max_length=8)
    subject = models.CharField(max_length=255)
    exam_date = models.DateField()
    year = models.PositiveIntegerField(db_index=True)

    class Meta:
        unique_together = ("exam_type", "code", "exam_date")
        ordering = ("-exam_date", "subject")
        indexes = [
            models.Index(fields=("exam_type", "exam_date")),
            models.Index(fields=("exam_type", "code")),
        ]
        verbose_name = "Экзамен"
        verbose_name_plural = "Экзамены"

    def __str__(self):
        return f"{self.get_exam_type_display()} {self.code} {self.subject} {self.exam_date}"


class Student(models.Model):
    school = models.ForeignKey("organizations.School", on_delete=models.CASCADE, related_name="students")
    external_id = models.CharField(max_length=128)
    full_name = models.CharField(max_length=255)
    grade = models.CharField(max_length=16, blank=True)

    class Meta:
        unique_together = ("school", "external_id")
        ordering = ("full_name",)
        verbose_name = "Ученик"
        verbose_name_plural = "Ученики"

    def __str__(self):
        return self.full_name


class ExamResult(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="exam_results",
        verbose_name="Ученик",
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name="Экзамен",
    )
    school_code = models.CharField(max_length=32, blank=True, verbose_name="Код ОО")
    student_name = models.CharField(max_length=255, blank=True, verbose_name="ФИО")
    short_answer_tasks = models.TextField(blank=True, verbose_name="Задания с кратким ответом")
    long_answer_tasks = models.TextField(blank=True, verbose_name="Задания с развернутым ответом")
    primary_score = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="Первичный балл")
    score = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="Балл")
    total_score = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="Итоговый балл")
    passed = models.BooleanField(default=False, verbose_name="Сдал")
    short_answer_raw = models.TextField(blank=True, verbose_name="Сырые краткие ответы")
    source_row = models.JSONField(default=dict, blank=True, verbose_name="Исходная строка")

    class Meta:
        unique_together = ("student", "exam")
        indexes = [
            models.Index(fields=("exam", "score")),
            models.Index(fields=("exam", "passed")),
        ]
        verbose_name = "Результат экзамена"
        verbose_name_plural = "Результаты экзаменов"

    def __str__(self):
        return f"{self.student_name or self.student.full_name} - {self.exam}"


class TaskResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="task_results")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="task_results")
    task_number = models.PositiveIntegerField()
    value = models.CharField(max_length=10)

    class Meta:
        unique_together = ("student", "exam", "task_number")
        indexes = [
            models.Index(fields=("exam", "task_number", "value")),
            models.Index(fields=("exam", "student")),
        ]
        verbose_name = "Результат задания"
        verbose_name_plural = "Результаты заданий"


class EgePassingThreshold(models.Model):
    year = models.PositiveIntegerField(db_index=True, verbose_name="Год")
    subject_key = models.CharField(
        max_length=32,
        choices=EgeSubjectKey.choices,
        db_index=True,
        verbose_name="Предмет",
    )
    minimum_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Минимальный балл",
    )
    minimum_grade = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Минимальная оценка",
    )

    class Meta:
        unique_together = ("year", "subject_key")
        ordering = ("-year", "subject_key")
        verbose_name = "Минимальный порог ЕГЭ"
        verbose_name_plural = "Минимальные пороги ЕГЭ"

    def __str__(self):
        return f"{self.year} - {self.get_subject_key_display()}"


class ExamTaskTopic(models.Model):
    exam_type = models.CharField(max_length=8, choices=ExamType.choices, verbose_name="Тип экзамена")
    subject_key = models.CharField(max_length=64, db_index=True, verbose_name="Ключ предмета")
    task_number = models.PositiveIntegerField(verbose_name="Номер задания")
    topic = models.CharField(max_length=512, verbose_name="Тема")
    grade_range = models.JSONField(default=list, blank=True, verbose_name="Классы")

    class Meta:
        unique_together = ("exam_type", "subject_key", "task_number")
        ordering = ("exam_type", "subject_key", "task_number")
        verbose_name = "Тема задания экзамена"
        verbose_name_plural = "Темы заданий экзаменов"

    def __str__(self):
        return f"{self.get_exam_type_display()} {self.subject_key} №{self.task_number}"
