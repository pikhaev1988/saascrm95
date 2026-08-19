from django.db import models


class TaskKnowledge(models.Model):
    """Единая база знаний ФИПИ: метаданные задания КИМ."""

    exam_type = models.CharField(max_length=8, db_index=True, verbose_name="Тип экзамена")
    subject_key = models.CharField(max_length=64, db_index=True, verbose_name="Ключ предмета")
    task_number = models.PositiveIntegerField(verbose_name="Номер задания")
    document_year = models.PositiveIntegerField(default=2026, db_index=True, verbose_name="Год документа")

    official_task_name = models.CharField(max_length=255, blank=True, verbose_name="Официальное название")
    section = models.CharField(max_length=512, blank=True, verbose_name="Раздел")
    subsection = models.CharField(max_length=512, blank=True, verbose_name="Подраздел")
    topic = models.CharField(max_length=512, verbose_name="Тема")
    subtopic = models.CharField(max_length=512, blank=True, verbose_name="Подтема")

    fgos_class_start = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Класс изучения")
    fgos_class_repeat = models.JSONField(default=list, blank=True, verbose_name="Классы повторения")
    fgos_classes = models.JSONField(default=list, blank=True, verbose_name="Классы ФГОС")
    fgos_exam_class = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Класс проверки")

    fipi_content_code = models.CharField(max_length=64, blank=True, verbose_name="Код элемента содержания")
    requirement_code = models.CharField(max_length=64, blank=True, verbose_name="Код требования")
    skill = models.CharField(max_length=64, blank=True, verbose_name="Код умения")
    skill_name = models.CharField(max_length=512, blank=True, verbose_name="Проверяемое умение")
    competency = models.CharField(max_length=512, blank=True, verbose_name="Компетенция")

    difficulty = models.CharField(max_length=32, blank=True, verbose_name="Сложность")
    exam_part = models.PositiveSmallIntegerField(default=1, verbose_name="Часть экзамена")
    max_score = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Макс. балл")

    related_tasks = models.JSONField(default=list, blank=True, verbose_name="Связанные задания")
    previous_topics = models.JSONField(default=list, blank=True, verbose_name="Предыдущие темы")
    next_topics = models.JSONField(default=list, blank=True, verbose_name="Последующие темы")

    teaching_hours = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Часы изучения")
    recommended_practice_hours = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Часы практики")
    recommended_control = models.CharField(max_length=512, blank=True, verbose_name="Контроль")
    expected_growth = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Ожидаемый прирост, %")

    source_document = models.CharField(max_length=255, verbose_name="Источник")
    document_version = models.CharField(max_length=64, blank=True, verbose_name="Версия документа")
    confidence = models.DecimalField(max_digits=4, decimal_places=3, default=0.5, verbose_name="Достоверность")
    raw_payload = models.JSONField(default=dict, blank=True, verbose_name="Сырые данные")
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("exam_type", "subject_key", "task_number", "document_year")
        ordering = ("exam_type", "subject_key", "task_number")
        verbose_name = "Знание о задании (ФИПИ)"
        verbose_name_plural = "База знаний ФИПИ (задания)"
        indexes = [
            models.Index(fields=("exam_type", "subject_key", "task_number")),
            models.Index(fields=("skill",)),
            models.Index(fields=("fipi_content_code",)),
        ]

    def __str__(self):
        return f"{self.exam_type} {self.subject_key} №{self.task_number}: {self.topic[:60]}"
