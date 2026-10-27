from django.urls import path
from .views import start_payment_view, payment_success_view, payment_cancelled_view, payfast_itn_view

urlpatterns = [
    path("start/", start_payment_view, name="start_payment"),
    path("success/", payment_success_view, name="payment_success"),
    path("cancelled/", payment_cancelled_view, name="payment_cancelled"),
    path("itn/", payfast_itn_view, name="payfast_itn"),
]
