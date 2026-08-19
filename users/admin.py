from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Role scope",
            {
                "fields": ("role", "ministry", "district", "school"),
            },
        ),
    )
    list_display = ("username", "email", "role", "district", "school", "is_active")
