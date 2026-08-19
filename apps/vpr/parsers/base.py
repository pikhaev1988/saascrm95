"""Базовый интерфейс парсеров ВПР."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from apps.vpr.parsers.dto import VprParseResult


class BaseVprParser(ABC):
    """Абстрактный парсер официального шаблона ВПР."""

    template_key: str = "base"
    display_name: str = "ВПР"

    @abstractmethod
    def can_parse(self, path: Path) -> bool:
        """Быстрая проверка: подходит ли файл под этот шаблон."""

    @abstractmethod
    def parse(self, path: Path) -> VprParseResult:
        """Полный разбор файла."""
