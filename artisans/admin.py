from django.contrib import admin
from .models import Artisan


@admin.register(Artisan)
class ArtisanAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "business_name",
        "verification_status",
        "starting_price",
        "maximum_price",
        "created_at",
    )

    list_filter = (
        "verification_status",
    )

    search_fields = (
        "user__username",
        "user__email",
        "user__full_name",
        "business_name",
        "phone_number",
    )