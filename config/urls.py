from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("accounts.urls")),
    path("chat/", include("chat.urls")),
    path("payments/", include("payments.urls")),
]

# Always served by Django, not gated to DEBUG — this MVP has no CDN
# or S3 in front of it (see README's "deliberately left out" list),
# so Render's persistent disk + this is how uploaded profile photos
# stay reachable in production too, same as everywhere else.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
