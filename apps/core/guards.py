"""
Extra locks for the public site.

The staff sign-in page is the one door that opens the whole admin.
This slows a program that keeps guessing the password.
"""
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

# Wrong passwords allowed from one address before we pause that address.
MAX_TRIES = 8
# How long the pause lasts, in seconds.
WINDOW_SECONDS = 15 * 60


def client_ip(request) -> str:
    """
    The visitor's address.

    In production the site sits behind one proxy (Caddy). That proxy adds
    the real address at the end of X-Forwarded-For. We use that last
    address, so a stranger cannot invent a new one and skip the limit.
    On a laptop there is no proxy, so we use the direct address.
    """
    remote = request.META.get("REMOTE_ADDR", "") or "unknown"
    if not getattr(settings, "TRUST_ONE_PROXY", False):
        return remote
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not forwarded:
        return remote
    return forwarded.split(",")[-1].strip() or remote


class AdminLoginGuardMiddleware:
    """Pause an address that keeps failing the staff sign-in."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not _is_admin_login(request):
            return self.get_response(request)

        key = f"admin-login-fails:{client_ip(request)}"
        if request.method == "POST" and _tries(key) >= MAX_TRIES:
            return HttpResponse(
                "Too many sign-in attempts. Wait 15 minutes and try again.",
                status=429,
                content_type="text/plain; charset=utf-8",
            )

        response = self.get_response(request)
        if request.method != "POST":
            return response

        # A wrong password redisplays the form (status 200).
        # A correct password sends the browser onward (status 302).
        if response.status_code == 200:
            _add_try(key)
        elif response.status_code in (302, 303):
            cache.delete(key)
        return response


def _is_admin_login(request) -> bool:
    path = request.path.rstrip("/") or "/"
    return path == "/admin/login"


def _tries(key: str) -> int:
    try:
        return int(cache.get(key, 0) or 0)
    except Exception:
        # If the counter store is down, still let a real person sign in.
        return 0


def _add_try(key: str) -> None:
    try:
        cache.set(key, _tries(key) + 1, WINDOW_SECONDS)
    except Exception:
        return


def login_blocked(kind: str, request) -> bool:
    """True when this address has guessed the password too many times."""
    return _tries(f"{kind}-login-fails:{client_ip(request)}") >= MAX_TRIES


def note_login_failure(kind: str, request) -> None:
    """Count one wrong password for the studio desk or the Django screen."""
    _add_try(f"{kind}-login-fails:{client_ip(request)}")


def clear_login_failures(kind: str, request) -> None:
    """A correct password wipes the counter for that address."""
    cache.delete(f"{kind}-login-fails:{client_ip(request)}")
