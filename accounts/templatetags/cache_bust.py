"""
A static-file tag that appends the file's last-modified time as a
query string (?v=<timestamp>), so a browser that already cached an
old copy of e.g. style.css is forced to fetch the new one as soon as
the file on disk changes — no manual version bumping, no "hard
refresh your phone" every time a CSS/JS file is updated.
"""
import os

from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(path):
    url = static(path)
    try:
        full_path = os.path.join(settings.STATICFILES_DIRS[0], path)
        mtime = int(os.path.getmtime(full_path))
    except OSError:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={mtime}"
