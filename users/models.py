from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    MINISTRY = "ministry", "Министерство"
    DISTRICT = "district", "Район"
    SCHOOL = "school", "Школа"


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices)
    ministry = models.ForeignKey(
        "organizations.Ministry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    district = models.ForeignKey(
        "organizations.District",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    school = models.ForeignKey(
        "organizations.School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
