from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "type", "created_at", "read_at")
    list_filter = ("type", "read_at", "created_at")
    search_fields = ("recipient__email",
                     "recipient__username", "title", "message")
    readonly_fields = ("created_at",)
