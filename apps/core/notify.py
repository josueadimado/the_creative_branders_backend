"""
Send studio lead notifications (and inquiry confirmations) after a form saves.

Email failures are logged only — they must never block the API response
or roll back the saved submission.
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from .models import AcademyInterest, InquiryMessage, WaitlistSignup

logger = logging.getLogger(__name__)


def _admin_change_url(obj: Any) -> str:
    """Absolute link to the Django admin change page for this row."""
    opts = obj._meta
    path = reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk])
    base = getattr(settings, "BACKEND_PUBLIC_URL", "").rstrip("/")
    if base:
        return f"{base}{path}"
    return path


def _safe_send(subject: str, body: str, recipients: list[str]) -> None:
    if not recipients:
        logger.warning("Skipping email %r — no recipients configured.", subject)
        return
    from_email = settings.DEFAULT_FROM_EMAIL
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send email %r to %s", subject, recipients)


def notify_inquiry(inquiry: InquiryMessage) -> None:
    studio = (getattr(settings, "STUDIO_NOTIFY_EMAIL", "") or "").strip()
    admin_url = _admin_change_url(inquiry)
    fields = [
        f"Name: {inquiry.name}",
        f"Email: {inquiry.email}",
        f"WhatsApp / phone: {inquiry.phone or '(not provided)'}",
        f"Company: {inquiry.company or '(not provided)'}",
        f"Country: {inquiry.country}",
        f"Budget range: {inquiry.budget_range}",
        f"Message:\n{inquiry.message}",
        f"\nAdmin: {admin_url}",
    ]
    if studio:
        _safe_send(
            subject=f"New inquiry from {inquiry.name}",
            body="\n".join(fields),
            recipients=[studio],
        )
    # Visitor confirmation — inquiry form only.
    _safe_send(
        subject="We've received your inquiry",
        body=(
            "Thank you for reaching out to The Creative Branders. "
            "We've received your message and will reply within 48 hours.\n\n"
            "— The Creative Branders"
        ),
        recipients=[inquiry.email],
    )


def notify_waitlist(signup: WaitlistSignup) -> None:
    studio = (getattr(settings, "STUDIO_NOTIFY_EMAIL", "") or "").strip()
    if not studio:
        return
    admin_url = _admin_change_url(signup)
    body = "\n".join(
        [
            f"Name: {signup.name or '(not provided)'}",
            f"Email: {signup.email}",
            f"\nAdmin: {admin_url}",
        ]
    )
    _safe_send(
        subject=f"SmartCRM waitlist: {signup.email}",
        body=body,
        recipients=[studio],
    )


def notify_academy(interest: AcademyInterest) -> None:
    studio = (getattr(settings, "STUDIO_NOTIFY_EMAIL", "") or "").strip()
    if not studio:
        return
    admin_url = _admin_change_url(interest)
    body = "\n".join(
        [
            f"Name: {interest.name}",
            f"Email: {interest.email}",
            f"Message: {interest.message or '(not provided)'}",
            f"\nAdmin: {admin_url}",
        ]
    )
    _safe_send(
        subject=f"Academy interest from {interest.name}",
        body=body,
        recipients=[studio],
    )
