from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Like, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Point 6 of the MVP: admin approval, using Django's built-in admin
    instead of a custom-built screen.
    """

    list_display = ("username", "gender", "age", "town", "is_approved", "is_unlocked", "date_joined")
    list_filter = ("is_approved", "gender", "town", "is_unlocked")
    search_fields = ("username", "email")
    actions = ["approve_users", "reject_users"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Mzansi Link", {"fields": (
            "age", "gender", "town", "photo", "photo_blurred",
            "bio", "interests", "is_approved", "is_unlocked",
        )}),
    )

    @admin.action(description="Approve selected members")
    def approve_users(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description="Reject / suspend selected members")
    def reject_users(self, request, queryset):
        queryset.update(is_approved=False)


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("from_user", "action", "to_user", "created_at")
    list_filter = ("action",)
    search_fields = ("from_user__username", "to_user__username")
