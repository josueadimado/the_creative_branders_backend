"""Settings used in production (Dokploy + Caddy on Hetzner)."""
from .base import *  # noqa: F401, F403

DEBUG = False

# These have no safe default. A missing value stops the container at startup.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

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
# One proxy (Caddy) sits in front. Rate limits use the visitor's real address.
TRUST_ONE_PROXY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
# The site should not be placed inside another website's frame.
X_FRAME_OPTIONS = "DENY"

# Three gunicorn workers share this folder, so a limit set on one worker
# is seen by the others. The laptop settings keep the simpler memory cache.
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": str(CACHE_DIR),
    }
}

# JSON only. The browsable API page is useful on a laptop, not on the live server.
# NUM_PROXIES tells the rate limit to read the visitor address from the proxy.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "NUM_PROXIES": 1,
}
