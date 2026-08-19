"""Исключения модуля ВПР."""


class VprError(Exception):
    """Базовая ошибка модуля ВПР."""


class VprValidationError(VprError):
    """Файл не прошёл проверку структуры."""

    def __init__(self, message: str, *, details: list[str] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class VprParseError(VprError):
    """Ошибка разбора файла ВПР."""


class VprImportError(VprError):
    """Ошибка сохранения данных ВПР."""


class VprCatalogError(VprError):
    """Ошибка справочника заданий ВПР."""


class VprCatalogImportError(VprCatalogError):
    """Ошибка импорта справочника заданий."""
