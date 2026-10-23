"""Settings used on your computer / in docker compose (local)."""
from .base import *  # noqa: F401, F403

DEBUG = env.bool("DEBUG", default=True)

# Django's test client uses the host name "testserver".
if "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, "testserver"]
