from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "recipient", "text", "created_at")
    search_fields = ("sender__username", "recipient__username", "text")
