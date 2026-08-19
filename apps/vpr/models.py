from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from organizations.models import District, School


class VprUploadStatus(models.TextChoices):
    UPLOADED = "uploaded", "Загружен"
    PREVIEW = "preview", "Предпросмотр"
    IMPORTED = "imported", "Импортирован"
    FAILED = "failed", "Ошибка"
    REVERTED = "reverted", "Отменён"


class VprUpload(models.Model):
    """Сессия загрузки файла протокола ВПР."""

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vpr_uploads",
        verbose_name="Кто загрузил",
    )
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vpr_uploads",
        verbose_name="ОО",
    )
    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vpr_uploads",
        verbose_name="Район",
    )
    file = models.FileField(upload_to="vpr/uploads/%Y/%m/%d/", verbose_name="Файл")
    original_filename = models.CharField(max_length=255, blank=True, verbose_name="Имя файла")
    template_key = models.CharField(max_length=64, blank=True, verbose_name="Шаблон парсера")
    status = models.CharField(
        max_length=16,
        choices=VprUploadStatus.choices,
        default=VprUploadStatus.UPLOADED,
        db_index=True,
        verbose_name="Статус",
    )
    error_message = models.TextField(blank=True, verbose_name="Ошибка")
    preview_payload = models.JSONField(default=dict, blank=True, verbose_name="Предпросмотр")
    students_imported = models.PositiveIntegerField(default=0, verbose_name="Учащихся")
    results_imported = models.PositiveIntegerField(default=0, verbose_name="Результатов")
    tasks_imported = models.PositiveIntegerField(default=0, verbose_name="Заданий")
    errors_count = models.PositiveIntegerField(default=0, verbose_name="Ошибок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Обработан")

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Загрузка ВПР"
        verbose_name_plural = "Загрузки ВПР"

    def __str__(self) -> str:
        return f"ВПР загрузка #{self.pk} ({self.status})"

    def mark_failed(self, message: str) -> None:
        self.status = VprUploadStatus.FAILED
        self.error_message = message
        self.processed_at = timezone.now()
        self.save(
            update_fields=["status", "error_message", "processed_at"],
        )


class VprProtocol(models.Model):
    """Протокол ВПР (один предмет / параллель / дата)."""

    upload = models.OneToOneField(
        VprUpload,
        on_delete=models.CASCADE,
        related_name="protocol",
        verbose_name="Загрузка",
    )
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vpr_protocols",
        verbose_name="ОО",
    )
    organization_code = models.CharField(max_length=64, blank=True, verbose_name="Код ОО (из файла)")
    organization_name = models.CharField(max_length=512, blank=True, verbose_name="Название ОО")
    municipality = models.CharField(max_length=255, blank=True, verbose_name="Муниципалитет")
    subject = models.CharField(max_length=255, verbose_name="Предмет")
    parallel = models.PositiveSmallIntegerField(verbose_name="Класс (параллель)")
    academic_year = models.PositiveIntegerField(verbose_name="Учебный год")
    exam_date = models.DateField(null=True, blank=True, verbose_name="Дата проведения")
    max_primary_score = models.PositiveIntegerField(default=0, verbose_name="Макс. первичный балл")
    participants_count = models.PositiveIntegerField(default=0, verbose_name="Участников")
    tasks_count = models.PositiveIntegerField(default=0, verbose_name="Заданий")
    source_title = models.CharField(max_length=512, blank=True, verbose_name="Заголовок источника")
    sheet_name = models.CharField(max_length=255, blank=True, verbose_name="Лист Excel")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-exam_date", "-created_at")
        verbose_name = "Протокол ВПР"
        verbose_name_plural = "Протоколы ВПР"
        indexes = [
            models.Index(fields=("subject", "parallel", "academic_year")),
            models.Index(fields=("organization_code", "academic_year")),
        ]

    def __str__(self) -> str:
        return f"{self.subject} · {self.parallel} кл. · {self.academic_year}"


class VprTask(models.Model):
    """Описание задания в протоколе ВПР."""

    protocol = models.ForeignKey(
        VprProtocol,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Протокол",
    )
    position = models.PositiveSmallIntegerField(verbose_name="Порядок")
    code = models.CharField(max_length=32, verbose_name="Код задания")
    title = models.CharField(max_length=64, verbose_name="Заголовок")
    max_score = models.PositiveSmallIntegerField(default=0, verbose_name="Макс. балл")
    difficulty = models.CharField(max_length=8, blank=True, verbose_name="Уровень сложности")

    class Meta:
        ordering = ("protocol_id", "position")
        unique_together = ("protocol", "code")
        verbose_name = "Задание ВПР"
        verbose_name_plural = "Задания ВПР"

    def __str__(self) -> str:
        return f"{self.code} ({self.max_score}б)"


class VprStudentResult(models.Model):
    """Результат участника ВПР (учащийся + итоги)."""

    protocol = models.ForeignKey(
        VprProtocol,
        on_delete=models.CASCADE,
        related_name="student_results",
        verbose_name="Протокол",
    )
    participant_code = models.CharField(max_length=64, verbose_name="Код участника")
    full_name = models.CharField(max_length=255, blank=True, verbose_name="ФИО")
    gender = models.CharField(max_length=16, blank=True, verbose_name="Пол")
    class_group = models.CharField(max_length=32, blank=True, verbose_name="Класс (группа)")
    variant = models.CharField(max_length=32, blank=True, verbose_name="Вариант")
    primary_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Первичный балл",
    )
    mark_vpr = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Отметка ВПР")
    mark_journal = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Отметка по журналу",
    )
    source_row = models.PositiveIntegerField(null=True, blank=True, verbose_name="Строка файла")

    class Meta:
        ordering = ("protocol_id", "participant_code")
        unique_together = ("protocol", "participant_code")
        verbose_name = "Результат участника ВПР"
        verbose_name_plural = "Результаты участников ВПР"

    def __str__(self) -> str:
        return f"{self.participant_code} · {self.primary_score}"


class VprTaskScore(models.Model):
    """Балл участника за конкретное задание."""

    result = models.ForeignKey(
        VprStudentResult,
        on_delete=models.CASCADE,
        related_name="task_scores",
        verbose_name="Результат",
    )
    task = models.ForeignKey(
        VprTask,
        on_delete=models.CASCADE,
        related_name="scores",
        verbose_name="Задание",
    )
    raw_value = models.CharField(max_length=32, blank=True, verbose_name="Сырое значение")
    score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Полученный балл",
    )
    max_score = models.PositiveSmallIntegerField(default=0, verbose_name="Макс. балл")

    class Meta:
        ordering = ("result_id", "task__position")
        unique_together = ("result", "task")
        verbose_name = "Балл за задание ВПР"
        verbose_name_plural = "Баллы за задания ВПР"

    def __str__(self) -> str:
        return f"{self.task_id}:{self.score}"


class VprImportLogLevel(models.TextChoices):
    INFO = "info", "Инфо"
    WARNING = "warning", "Предупреждение"
    ERROR = "error", "Ошибка"


class VprImportLog(models.Model):
    """Журнал импорта ВПР."""

    upload = models.ForeignKey(
        VprUpload,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="Загрузка",
    )
    level = models.CharField(
        max_length=16,
        choices=VprImportLogLevel.choices,
        default=VprImportLogLevel.INFO,
        verbose_name="Уровень",
    )
    message = models.TextField(verbose_name="Сообщение")
    details = models.JSONField(default=dict, blank=True, verbose_name="Детали")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        verbose_name = "Лог импорта ВПР"
        verbose_name_plural = "Логи импорта ВПР"

    def __str__(self) -> str:
        return f"[{self.level}] {self.message[:80]}"


class VprTaskDifficulty(models.TextChoices):
    BASIC = "basic", "Базовый"
    ADVANCED = "advanced", "Повышенный"
    HIGH = "high", "Высокий"
    UNKNOWN = "", "Не указан"


class VprTaskCatalogEntry(models.Model):
    """
    Справочник заданий ВПР — основа будущей аналитики.
    Результаты протоколов не изменяются; связь выполняется по ключам сопоставления.
    """

    academic_year = models.PositiveIntegerField(verbose_name="Учебный год", db_index=True)
    subject = models.CharField(max_length=255, verbose_name="Предмет", db_index=True)
    parallel = models.PositiveSmallIntegerField(verbose_name="Класс", db_index=True)
    task_number = models.PositiveSmallIntegerField(verbose_name="Номер задания")
    task_subnumber = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="Подномер задания",
        help_text="Например: 1, 2, К1, К2",
    )
    task_code = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Код задания",
        help_text="Канонический код как в протоколе: 7, 9.1, 4К1",
        db_index=True,
    )
    official_code = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Официальный код",
    )
    max_score = models.PositiveSmallIntegerField(default=0, verbose_name="Максимальный балл")
    checked_skill = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="Проверяемое умение",
    )
    fgos_result = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="Предметный результат ФГОС",
    )
    program_section = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="Раздел программы",
    )
    topic = models.CharField(max_length=512, blank=True, default="", verbose_name="Тема")
    topic_subsection = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="Подраздел темы",
    )
    difficulty = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="Уровень сложности",
        help_text="Б / П / Базовый / Повышенный и т.п.",
    )
    task_type = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="Тип задания",
    )
    short_description = models.TextField(
        blank=True,
        default="",
        verbose_name="Краткое описание задания",
    )
    normative_source = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="Нормативный источник",
    )
    extra = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Дополнительные поля",
        help_text="Расширяемые атрибуты без изменения схемы результатов",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("academic_year", "subject", "parallel", "task_number", "task_subnumber", "id")
        verbose_name = "Задание ВПР (справочник)"
        verbose_name_plural = "Справочник заданий ВПР"
        constraints = [
            models.UniqueConstraint(
                fields=("academic_year", "subject", "parallel", "task_number", "task_subnumber"),
                name="vpr_catalog_unique_task_key",
            ),
        ]
        indexes = [
            models.Index(fields=("academic_year", "subject", "parallel")),
            models.Index(fields=("subject", "parallel", "task_code")),
        ]

    def __str__(self) -> str:
        code = self.display_code
        return f"{self.subject} · {self.parallel} кл. · {self.academic_year} · №{code}"

    @property
    def display_code(self) -> str:
        if self.task_code:
            return self.task_code
        if self.task_subnumber:
            return f"{self.task_number}.{self.task_subnumber}"
        return str(self.task_number)

    def save(self, *args, **kwargs):
        if not self.task_code:
            self.task_code = self._build_task_code()
        self.task_subnumber = (self.task_subnumber or "").strip()
        self.subject = (self.subject or "").strip()
        super().save(*args, **kwargs)

    def _build_task_code(self) -> str:
        sub = (self.task_subnumber or "").strip()
        if not sub:
            return str(self.task_number)
        if sub.upper().startswith("К") or sub.upper().startswith("K"):
            return f"{self.task_number}{sub.upper().replace('K', 'К')}"
        return f"{self.task_number}.{sub}"


class VprTaskCatalogImportStatus(models.TextChoices):
    SUCCESS = "success", "Успешно"
    PARTIAL = "partial", "Частично"
    FAILED = "failed", "Ошибка"


class VprTaskCatalogImport(models.Model):
    """Журнал наполнения справочника заданий ВПР."""

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vpr_catalog_imports",
        verbose_name="Кто загрузил",
    )
    file = models.FileField(
        upload_to="vpr/catalog/%Y/%m/%d/",
        blank=True,
        verbose_name="Файл",
    )
    original_filename = models.CharField(max_length=255, blank=True, verbose_name="Имя файла")
    source_format = models.CharField(max_length=16, blank=True, verbose_name="Формат")
    status = models.CharField(
        max_length=16,
        choices=VprTaskCatalogImportStatus.choices,
        default=VprTaskCatalogImportStatus.SUCCESS,
        verbose_name="Статус",
    )
    created_count = models.PositiveIntegerField(default=0, verbose_name="Создано")
    updated_count = models.PositiveIntegerField(default=0, verbose_name="Обновлено")
    skipped_count = models.PositiveIntegerField(default=0, verbose_name="Пропущено")
    error_count = models.PositiveIntegerField(default=0, verbose_name="Ошибок")
    message = models.TextField(blank=True, verbose_name="Сообщение")
    details = models.JSONField(default=dict, blank=True, verbose_name="Детали")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Импорт справочника ВПР"
        verbose_name_plural = "Импорты справочника ВПР"

    def __str__(self) -> str:
        return f"Справочник ВПР #{self.pk} ({self.status})"
