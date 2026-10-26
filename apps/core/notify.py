"""
Send studio lead notifications (and inquiry confirmations) after a form saves.

Email failures are logged only — they must never block the API response
or roll back the saved submission.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse

from .models import AcademyInterest, InquiryMessage, WaitlistSignup
from .site_settings import EMAIL, LEGAL_NAME, SITE_URL, WHATSAPP_NUMBER

logger = logging.getLogger(__name__)


def _admin_change_url(obj: Any) -> str:
    """Absolute link to the Django admin change page for this row."""
    opts = obj._meta
    path = reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk])
    base = getattr(settings, "BACKEND_PUBLIC_URL", "").rstrip("/")
    if base:
        return f"{base}{path}"
    return path


def _one_line(value: str, limit: int = 180) -> str:
    """
    A subject line must stay one line.
    A name with a line break in it could otherwise add extra mail headers.
    """
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    return text[:limit] or "someone"


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _whatsapp(number: str, message: str = "") -> str:
    """A wa.me link. The number is digits only, with the country code already included."""
    digits = _digits(number)
    if len(digits) < 8:
        return ""
    url = f"https://wa.me/{digits}"
    if message:
        return f"{url}?text={quote(message)}"
    return url


def _budget_label(inquiry: InquiryMessage) -> str:
    band = (inquiry.budget_range or "").strip()
    if not band:
        return "not set"
    if inquiry.budget_currency == "GHS":
        return f"GHS {band}"
    return band


def _service_label(inquiry: InquiryMessage) -> str:
    needs = [str(item).strip() for item in (inquiry.needs or []) if str(item).strip()]
    return ", ".join(needs) or "Not specified"


def _reply_address(address: str | None) -> str:
    """A visitor address when we have one. Otherwise the studio inbox."""
    cleaned = " ".join(str(address or "").split())
    return cleaned or EMAIL


def _safe_send(subject: str, body: str, recipients: list[str], reply_to: str | None = None) -> None:
    if not recipients:
        logger.warning("Skipping email %r — no recipients configured.", subject)
        return
    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        # Studio mail replies to the lead. Mail sent to a visitor replies to the studio.
        reply_to=[_reply_address(reply_to)],
    )
    try:
        message.send(fail_silently=False)
    except Exception:
        logger.exception("Failed to send email %r to %s", subject, recipients)


def notify_inquiry(inquiry: InquiryMessage) -> None:
    studio = (getattr(settings, "STUDIO_NOTIFY_EMAIL", "") or "").strip()
    admin_url = _admin_change_url(inquiry)
    service = _service_label(inquiry)
    budget = _budget_label(inquiry)
    visitor_wa = _whatsapp(inquiry.phone)
    fields = [
        f"Name: {inquiry.name}",
        f"Email: {inquiry.email}",
        f"WhatsApp / phone: {inquiry.phone or '(not provided)'}",
        f"WhatsApp them: {visitor_wa or '(no number given)'}",
        f"Company: {inquiry.company or '(not provided)'}",
        f"Country: {inquiry.country or '(not provided)'}",
        f"Needs: {service if inquiry.needs else '(not provided)'}",
        f"Timeline: {inquiry.timeline or '(not provided)'}",
        f"Budget: {budget}",
        f"Link: {inquiry.brief_link or '(not provided)'}",
        f"Message:\n{inquiry.message}",
        f"\nAdmin: {admin_url}",
    ]
    if studio:
        _safe_send(
            subject=_one_line(f"New brief: {inquiry.name} — {service} — {budget}"),
            body="\n".join(fields),
            recipients=[studio],
            reply_to=inquiry.email,
        )
    # This copy goes to the visitor, so a reply comes back to the studio.
    _safe_send(
        subject="We've received your brief",
        body=_visitor_confirmation(inquiry, service, budget),
        recipients=[inquiry.email],
    )


def _visitor_confirmation(inquiry: InquiryMessage, service: str, budget: str) -> str:
    """The note the visitor gets. It repeats what they sent and the next step."""
    first_name = _one_line(inquiry.name).split(" ")[0] or "there"
    privacy = f"{SITE_URL.rstrip('/')}/privacy"
    lines = [
        f"Hi {first_name},",
        "",
        "Thanks for your brief. Here is what you sent us.",
        "",
        f"Name: {inquiry.name}",
        f"Email: {inquiry.email}",
        f"WhatsApp / phone: {inquiry.phone or '(not provided)'}",
        f"Company: {inquiry.company or '(not provided)'}",
        f"Country: {inquiry.country or '(not provided)'}",
        f"What you need: {service}",
        f"When to start: {inquiry.timeline or '(not provided)'}",
        f"Budget: {budget}",
        f"Link: {inquiry.brief_link or '(not provided)'}",
        "Message:",
        inquiry.message,
        "",
        "What happens next",
        "We reply within one business day.",
        "",
        "Want to talk sooner? Message us on WhatsApp",
        _whatsapp(WHATSAPP_NUMBER),
        "",
        LEGAL_NAME,
        "Registered in Ghana",
        f"Privacy: {privacy}",
    ]
    return "\n".join(lines)


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
        reply_to=signup.email,
    )


def notify_newsletter(signup) -> None:
    studio = (getattr(settings, "STUDIO_NOTIFY_EMAIL", "") or "").strip()
    if not studio:
        return
    admin_url = _admin_change_url(signup)
    _safe_send(
        subject=f"Newsletter signup: {signup.email}",
        body=f"Email: {signup.email}\n\nAdmin: {admin_url}",
        recipients=[studio],
        reply_to=signup.email,
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
        subject=f"Academy interest from {_one_line(interest.name)}",
        body=body,
        recipients=[studio],
        reply_to=interest.email,
    )
