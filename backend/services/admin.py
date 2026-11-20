from django import forms
from django.contrib import admin
from .models import (
    Service,
    ServiceKeyword,
    ServiceScopeOption,
    ServiceScopeQuestion,
)
from .services import recalculate_price_ranges_for_service
from .text import normalize_text


class ServiceKeywordForm(forms.ModelForm):
    class Meta:
        model = ServiceKeyword
        fields = ["keyword"]

    def clean_keyword(self):
        # Normalize before the duplicate checks, so "Leak" next to "leak" is a
        # form error instead of a database IntegrityError when saving.
        keyword = normalize_text(self.cleaned_data["keyword"])
        if not keyword:
            raise forms.ValidationError("Keyword must contain letters or numbers.")
        return keyword


class ServiceKeywordInline(admin.TabularInline):
    model = ServiceKeyword
    form = ServiceKeywordForm
    extra = 3


class ServiceScopeOptionInline(admin.TabularInline):
    model = ServiceScopeOption
    extra = 2


@admin.register(ServiceScopeQuestion)
class ServiceScopeQuestionAdmin(admin.ModelAdmin):
    inlines = [ServiceScopeOptionInline]
    list_display = ("label", "service", "position", "is_active")
    list_filter = ("service", "is_active")
    search_fields = ("label", "service__name", "key")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    inlines = [ServiceKeywordInline]
    list_display = (
        "name",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "description",
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            recalculate_price_ranges_for_service(obj)