from django.conf import settings
from django.db import models

# How long a paid unlock lasts before a member has to pay again. Not a
# recurring PayFast subscription — each payment is its own once-off R99
# charge, it just now unlocks for a year instead of forever.
UNLOCK_VALID_DAYS = 365


class Payment(models.Model):
    """
    One row per PayFast attempt. Point 3 of the MVP: R99 per payment,
    valid for 12 months — not a recurring subscription token, so the
    member pays again (same flow) once their unlock lapses.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("complete", "Complete"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    m_payment_id = models.CharField(max_length=64, unique=True)
    pf_payment_id = models.CharField(max_length=64, blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} — R{self.amount} — {self.status}"
