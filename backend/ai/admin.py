from django.contrib import admin

from .models import SearchLog


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    # Filter on "No match" / "Unsure" to find words customers use that need
    # adding as service keywords.
    list_display = ("query", "confidence", "matched_service", "customer", "created_at")
    list_filter = ("confidence", "matched_service")
    list_select_related = ("matched_service", "customer__user")
    search_fields = ("query",)
    readonly_fields = ("customer", "query", "matched_service", "confidence", "created_at")

    def has_add_permission(self, request):
        return False
