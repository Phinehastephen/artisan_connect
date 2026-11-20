from django.contrib import admin
from .models import SavedLocation


@admin.register(SavedLocation)
class SavedLocationAdmin(admin.ModelAdmin):
    list_display = (
        "customer", 
        "name", 
        "address", 
        "latitude", 
        "longitude", 
        "created_at",
    )
    
    search_fields = (
        "customer__user__username", 
        "customer__user__email", 
        "customer__user__full_name", 
        "name", 
        "address",
    )