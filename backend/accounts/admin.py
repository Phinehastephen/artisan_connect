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

    # The app uses full_name, not Django's first/last name.
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("full_name", "email", "profile_picture")}),
        ("Artisan Connect", {"fields": ("role", "email_verified")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    # Email is required (unique) and full_name/role are app fields the stock
    # add form doesn't know about.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "full_name",
                    "role",
                    "email_verified",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None and "role" in form.base_fields:
            # Customers and artisans need a profile row, which only
            # registration creates; admin can only add other admins.
            form.base_fields["role"].choices = [(User.Role.ADMIN, "Admin")]
            form.base_fields["role"].initial = User.Role.ADMIN
        return form
