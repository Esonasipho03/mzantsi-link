"""
Small formatting helpers for the chat UI — short relative times for the
inbox list ("4m", "1h", "2d") and day labels for the message thread
("Today", "Yesterday", "12 March"), in the style of a normal chat app.
No polling/live-update here (that's out of MVP scope per the brief) —
these just make the static, reload-to-refresh page look right.
"""
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def short_time(value):
    if not value:
        return ""
    now = timezone.now()
    delta = now - value
    seconds = delta.total_seconds()
    if seconds < 60:
        return "now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}h"
    days = int(hours // 24)
    if days < 7:
        return f"{days}d"
    return value.strftime("%d %b")


@register.filter
def day_label(value):
    if not value:
        return ""
    local = timezone.localtime(value)
    today = timezone.localtime(timezone.now()).date()
    value_date = local.date()
    if value_date == today:
        return "Today"
    if (today - value_date).days == 1:
        return "Yesterday"
    return local.strftime("%d %B %Y")
