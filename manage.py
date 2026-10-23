#!/usr/bin/env python
"""
Django's command-line utility (migrate, runserver, createsuperuser, etc.).

Local work uses config.settings.development. Production sets
DJANGO_SETTINGS_MODULE=config.settings.production in the Docker image.
"""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
