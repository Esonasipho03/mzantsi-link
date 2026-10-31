import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,192.168.101.134").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "chat",
    "payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves static files directly from gunicorn in production (Render
    # has no separate nginx/CDN in front by default) — must sit right
    # after SecurityMiddleware. No-ops locally; `runserver` already
    # serves static files itself in DEBUG mode.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if os.getenv("USE_POSTGRES", "0") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "mzansilink"),
            "USER": os.getenv("DB_USER", "mzansilink"),
            "PASSWORD": os.getenv("DB_PASSWORD", "mzansilink"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
else:
    # Default for local development — no server, no password, no setup.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
]

LANGUAGE_CODE = "en-za"
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# `collectstatic` (run automatically by the build command below)
# gathers everything into here; WhiteNoise then serves straight from
# this folder in production. Doesn't exist/matter locally.
STATIC_ROOT = BASE_DIR / "staticfiles"
# MEDIA_IN_DB=1 (set in render.yaml) keeps uploaded photos in the
# database so Render's wiped-on-deploy filesystem can't lose them.
MEDIA_IN_DB = os.getenv("MEDIA_IN_DB", "0") == "1"
STORAGES = {
    "default": {
        "BACKEND": "accounts.storage.DatabaseStorage" if MEDIA_IN_DB
        else "django.core.files.storage.FileSystemStorage"
    },
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- Production hardening (no-ops locally, where DEBUG=1) ---
# Render terminates TLS at its edge and forwards plain HTTP to the
# app with this header set, so Django needs telling how to recognise
# an already-HTTPS request instead of redirect-looping forever.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Django 4+ requires the scheme here, not just the bare host — without
# this, a login/signup POST from the real domain is rejected as a
# cross-origin CSRF attempt. Comma-separated like ALLOWED_HOSTS.
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "post_login_redirect"
LOGOUT_REDIRECT_URL = "login"

# --- Mzansi Link business rules ---
MINIMUM_AGE = 21
UNLOCK_PRICE_ZAR = "99.00"

# --- PayFast ---
PAYFAST_MODE = os.getenv("PAYFAST_MODE", "sandbox")
PAYFAST_MERCHANT_ID = os.getenv("PAYFAST_MERCHANT_ID")
PAYFAST_MERCHANT_KEY = os.getenv("PAYFAST_MERCHANT_KEY")
PAYFAST_PASSPHRASE = os.getenv("PAYFAST_PASSPHRASE", "")
PAYFAST_RETURN_URL = os.getenv("PAYFAST_RETURN_URL")
PAYFAST_CANCEL_URL = os.getenv("PAYFAST_CANCEL_URL")
PAYFAST_NOTIFY_URL = os.getenv("PAYFAST_NOTIFY_URL")
PAYFAST_HOST = "sandbox.payfast.co.za" if PAYFAST_MODE == "sandbox" else "www.payfast.co.za"
