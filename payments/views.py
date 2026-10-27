import uuid
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from .models import Payment, UNLOCK_VALID_DAYS
from .payfast import build_payment_fields, payment_redirect_url, itn_signature_valid


@login_required
@require_POST
def start_payment_view(request):
    """Point 3 of the MVP: kicks off the R99 PayFast payment that unlocks
    clear photos and chat for 12 months. Anyone whose unlock already
    expired lands here again, same as a first-time payer."""
    user = request.user
    if user.has_active_unlock():
        return redirect("home")

    m_payment_id = str(uuid.uuid4())
    Payment.objects.create(user=user, m_payment_id=m_payment_id, amount=99.00, status="pending")
    fields = build_payment_fields(user, m_payment_id)
    return redirect(payment_redirect_url(fields))


def payment_success_view(request):
    # This is just where the browser lands — it never unlocks anyone
    # by itself. See PayfastITNView for the actual unlock.
    return render(request, "payments/success.html")


def payment_cancelled_view(request):
    return render(request, "payments/cancelled.html")


@csrf_exempt
@require_POST
def payfast_itn_view(request):
    """
    PayFast calls this URL directly (server to server) once a payment
    completes. This is the ONLY place that unlocks a user — the
    browser's return_url is never trusted to unlock anything by itself.
    """
    data = request.POST.dict()

    if not itn_signature_valid(data):
        return HttpResponse(status=400)

    try:
        payment = Payment.objects.get(m_payment_id=data.get("m_payment_id"))
    except Payment.DoesNotExist:
        return HttpResponse(status=404)

    payment.pf_payment_id = data.get("pf_payment_id", "")

    if data.get("payment_status") == "COMPLETE":
        payment.status = "complete"
        payment.user.is_unlocked = True
        payment.user.unlock_expires_at = timezone.now() + timedelta(days=UNLOCK_VALID_DAYS)
        payment.user.save()
    else:
        payment.status = "failed"

    payment.save()
    return HttpResponse(status=200)
