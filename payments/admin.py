from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "status", "m_payment_id", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "m_payment_id", "pf_payment_id")
