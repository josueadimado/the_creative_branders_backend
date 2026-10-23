"""Settings used in production (Dokploy + Caddy on Hetzner)."""
from .base import *  # noqa: F401, F403

DEBUG = False

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Fail loudly if a real secret was not provided.
SECRET_KEY = env("SECRET_KEY")

# Caddy terminates HTTPS and talks HTTP to gunicorn. Trust the
# X-Forwarded-Proto header so Django knows the original request was HTTPS.
# Do NOT enable SECURE_SSL_REDIRECT here — the TCP healthcheck talks HTTP
# on port 8000 inside the container, and a redirect would break it.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
