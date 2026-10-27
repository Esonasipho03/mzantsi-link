"""
Minimal PayFast helper: build the signed payload for a once-off
payment that unlocks the account for 12 months, and verify an ITN
(webhook) callback.
Reference: https://developers.payfast.co.za
"""
import hashlib
from urllib.parse import urlencode, quote_plus

from django.conf import settings


def _signature(data: dict, passphrase: str = "") -> str:
    pairs = [f"{k}={quote_plus(str(v))}" for k, v in data.items() if v not in (None, "")]
    param_string = "&".join(pairs)
    if passphrase:
        param_string += f"&passphrase={quote_plus(passphrase)}"
    return hashlib.md5(param_string.encode()).hexdigest()


def build_payment_fields(user, m_payment_id: str) -> dict:
    data = {
        "merchant_id": settings.PAYFAST_MERCHANT_ID,
        "merchant_key": settings.PAYFAST_MERCHANT_KEY,
        "return_url": settings.PAYFAST_RETURN_URL,
        "cancel_url": settings.PAYFAST_CANCEL_URL,
        "notify_url": settings.PAYFAST_NOTIFY_URL,
        "name_first": user.username,
        "email_address": user.email,
        "m_payment_id": m_payment_id,
        "amount": settings.UNLOCK_PRICE_ZAR,
        "item_name": "Mzansi Link — unlock (12 months)",
    }
    data["signature"] = _signature(data, settings.PAYFAST_PASSPHRASE)
    return data


def payment_redirect_url(fields: dict) -> str:
    return f"https://{settings.PAYFAST_HOST}/eng/process?{urlencode(fields)}"


def itn_signature_valid(post_data: dict) -> bool:
    data = post_data.copy()
    received_signature = data.pop("signature", "")
    expected_signature = _signature(data, settings.PAYFAST_PASSPHRASE)
    return received_signature == expected_signature
