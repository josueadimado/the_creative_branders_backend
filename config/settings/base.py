"""
Shared Django settings for The Creative Branders API.

development.py and production.py import everything from here, then change
only what is different in that environment.

Environment variables are read with django-environ (see .env.example).
"""
from pathlib import Path

import environ

# Folder that contains manage.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

# Load a .env file if one exists next to manage.py.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-secret-key-change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.core.apps.CoreConfig",
    "apps.content.apps.ContentConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Slows repeated wrong passwords on /admin/login/.
    "apps.core.guards.AdminLoginGuardMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [],
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
ASGI_APPLICATION = "config.asgi.application"

# Prefer DATABASE_URL. If it is not set, build the connection from
# POSTGRES_HOST / POSTGRES_PORT / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD.
# If none of those are set either, use a local SQLite file so `manage.py check`
# and `makemigrations` work on a laptop without Docker/Postgres.
if env("DATABASE_URL", default=""):
    DATABASES = {"default": env.db("DATABASE_URL")}
elif env("POSTGRES_HOST", default=""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", default="tcb"),
            "USER": env("POSTGRES_USER", default="tcb"),
            "PASSWORD": env("POSTGRES_PASSWORD", default="tcb"),
            "HOST": env("POSTGRES_HOST", default="db"),
            "PORT": env("POSTGRES_PORT", default="5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Pictures uploaded in the content desk. The site reads them from /media/.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Large enough for a project screenshot uploaded in the content desk.
# The public forms still reject long messages in their own checks.
DATA_UPLOAD_MAX_MEMORY_SIZE = 8_000_000
FILE_UPLOAD_MAX_MEMORY_SIZE = 8_000_000

# Browser origins allowed to call this API (the React frontend).
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])

# Hosts allowed to POST to the Django admin when it sits behind HTTPS.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Public intake forms are unauthenticated, so we throttle anonymous
# requests to slow down spam. Session auth is off so cross-origin
# POSTs from the website are not blocked by CSRF.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "tcb-throttles",
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/hour",
        "inquiry": "8/hour",
        "waitlist": "8/hour",
        "newsletter": "8/hour",
        "academy": "8/hour",
    },
}

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000").rstrip("/")

# Public URL of this API (used in admin links inside notification emails).
BACKEND_PUBLIC_URL = env("BACKEND_PUBLIC_URL", default="http://localhost:8000").rstrip("/")

# Studio inbox for new form submissions. Leave blank to skip studio emails.
STUDIO_NOTIFY_EMAIL = env("STUDIO_NOTIFY_EMAIL", default="")

# Outbound mail. Prefer Resend (RESEND_API_KEY → smtp.resend.com).
# Or set EMAIL_HOST / EMAIL_PORT / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD for any SMTP.
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="hello@thecreativebranders.com",
)
RESEND_API_KEY = env("RESEND_API_KEY", default="")

if RESEND_API_KEY:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.resend.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = "resend"
    EMAIL_HOST_PASSWORD = RESEND_API_KEY
elif env("EMAIL_HOST", default=""):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
    EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
else:
    # Local default: print emails to the Django console instead of sending.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
