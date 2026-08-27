from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "full_name",
        "role",
        "email_verified",
        "is_active",
    )

    list_filter = (
        "role",
        "email_verified",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "full_name",
    )