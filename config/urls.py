from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("accounts.urls")),
    path("chat/", include("chat.urls")),
    path("payments/", include("payments.urls")),
]

# NOTE: django.conf.urls.static.static() returns [] when DEBUG is off, so
# it can't be used to serve uploads in production — hence the explicit
# re_path + serve view below.
from django.urls import re_path

_media_prefix = settings.MEDIA_URL.lstrip("/")

if settings.MEDIA_IN_DB:
    # Production on Render's free plan: photos live in the database
    # (accounts/storage.py) so redeploys can't wipe them.
    from accounts.storage import serve_media

    urlpatterns += [re_path(r"^%s(?P<path>.+)$" % _media_prefix, serve_media)]
else:
    # Local development, or a host with a real persistent disk.
    from django.views.static import serve

    urlpatterns += [re_path(r"^%s(?P<path>.*)$" % _media_prefix, serve, {"document_root": settings.MEDIA_ROOT})]
