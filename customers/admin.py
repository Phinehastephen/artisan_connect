from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone_number",
        "default_location",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "user__full_name",
        "phone_number",
    )