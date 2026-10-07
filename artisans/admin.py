from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import Artisan
from .services import (
    MAX_ARTISAN_SERVICES,
    approve_artisan,
    recalculate_artisan_price_range,
    reject_artisan,
)


class ArtisanAdminForm(forms.ModelForm):
    class Meta:
        model = Artisan
        fields = "__all__"

    def clean_services(self):
        services = self.cleaned_data["services"]
        if not 1 <= len(services) <= MAX_ARTISAN_SERVICES:
            raise forms.ValidationError(
                f"An artisan must offer between 1 and {MAX_ARTISAN_SERVICES} services."
            )
        if any(not service.is_active for service in services):
            raise forms.ValidationError("Inactive services can't be assigned.")
        return services


@admin.register(Artisan)
class ArtisanAdmin(admin.ModelAdmin):
    form = ArtisanAdminForm
    # Prices are derived from services; verification goes through the
    # approve/reject actions so the pending-only rule still applies.
    readonly_fields = (
        "starting_price",
        "maximum_price",
        "verification_status",
    )
    actions = ("approve_selected", "reject_selected")

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

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        recalculate_artisan_price_range(form.instance)

    def _decide(self, request, queryset, decide, verb):
        done = 0
        for artisan in queryset:
            try:
                decide(artisan)
                done += 1
            except ValidationError as e:
                self.message_user(
                    request, f"{artisan}: {e.messages[0]}", messages.WARNING
                )
        if done:
            self.message_user(request, f"{verb} {done} artisan(s).")

    @admin.action(description="Approve selected pending artisans")
    def approve_selected(self, request, queryset):
        self._decide(request, queryset, approve_artisan, "Approved")

    @admin.action(description="Reject selected pending artisans")
    def reject_selected(self, request, queryset):
        self._decide(request, queryset, reject_artisan, "Rejected")
