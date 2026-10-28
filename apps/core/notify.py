"""
Send studio lead notifications (and inquiry confirmations) after a form saves.

Email failures are logged only — they must never block the API response
or roll back the saved submission.

Outgoing mail uses DEFAULT_FROM_EMAIL (The Creative Branders <hello@…>).
Visitor mail replies to the studio. Studio alerts Reply-To the lead.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse

from .email_layout import escape, rows_html, wrap_html
from .models import AcademyInterest, InquiryMessage, WaitlistSignup
from .site_settings import (
    BRAND_NAME,
    EMAIL,
    LEGAL_NAME,
    PHONE_DISPLAY,
    SITE_URL,
    WHATSAPP_DISPLAY,
    WHATSAPP_NUMBER,
)

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


def _blank(value: str | None, fallback: str = "Not provided") -> str:
    text = (value or "").strip()
    return text if text else fallback


def _safe_send(
    *,
    subject: str,
    text: str,
    html: str,
    recipients: list[str],
    reply_to: str | None = None,
) -> None:
    if not recipients:
        logger.warning("Skipping email %r — no recipients configured.", subject)
        return
    message = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        # Studio mail replies to the lead. Mail sent to a visitor replies to the studio.
        reply_to=[_reply_address(reply_to)],
    )
    message.attach_alternative(html, "text/html")
    try:
        message.send(fail_silently=False)
    except Exception:
        logger.exception("Failed to send email %r to %s", subject, recipients)


def _visit_pairs(record) -> list[tuple[str, str]]:
    rows = [
        ("Source", record.utm_source),
        ("Medium", record.utm_medium),
        ("Campaign", record.utm_campaign),
        ("Content", record.utm_content),
        ("Landing page", record.landing_page),
        ("Referrer", record.referrer),
    ]
    found = [(label, value) for label, value in rows if (value or "").strip()]
    if not found:
        return [("How they arrived", "Direct / not tagged")]
    return found


def _visit_text(record) -> list[str]:
    pairs = _visit_pairs(record)
    if len(pairs) == 1 and pairs[0][0] == "How they arrived":
        return [f"How they arrived: {pairs[0][1]}"]
    return ["How they arrived:"] + [f"{label}: {value}" for label, value in pairs]


def notify_inquiry(inquiry: InquiryMessage) -> None:
    studio = (getattr(settings, "STUDIO_NOTIFY_EMAIL", "") or "").strip()
    admin_url = _admin_change_url(inquiry)
    service = _service_label(inquiry)
    budget = _budget_label(inquiry)
    visitor_wa = _whatsapp(inquiry.phone)
    if studio:
        _send_studio_brief(inquiry, studio, admin_url, service, budget, visitor_wa)
    _send_visitor_confirmation(inquiry, service, budget)


def _send_studio_brief(
    inquiry: InquiryMessage,
    studio: str,
    admin_url: str,
    service: str,
    budget: str,
    visitor_wa: str,
) -> None:
    subject = _one_line(f"New brief · {inquiry.name} · {service}")
    facts = [
        ("Name", inquiry.name),
        ("Email", inquiry.email),
        ("WhatsApp / phone", _blank(inquiry.phone)),
        ("Company", _blank(inquiry.company)),
        ("Country", _blank(inquiry.country)),
        ("Needs", service if inquiry.needs else "Not provided"),
        ("Timeline", _blank(inquiry.timeline)),
        ("Budget", budget),
        ("Link", _blank(inquiry.brief_link)),
    ]
    text_lines = (
        [f"{label}: {value}" for label, value in facts]
        + ["", "Message:", inquiry.message or "(empty)", ""]
        + _visit_text(inquiry)
        + ["", f"WhatsApp them: {visitor_wa or '(no number given)'}", f"Open in admin: {admin_url}"]
    )
    cta = ""
    if visitor_wa:
        cta += (
            f'<p style="margin:18px 0 0;"><a href="{escape(visitor_wa)}" '
            'style="display:inline-block;padding:10px 16px;background:#0E1E2B;color:#ffffff;'
            'text-decoration:none;border-radius:999px;font-size:13px;font-weight:600;">'
            "WhatsApp this lead</a></p>"
        )
    cta += (
        f'<p style="margin:12px 0 0;"><a href="{escape(admin_url)}" '
        'style="color:#2F6FED;font-size:13px;">Open in admin →</a></p>'
    )
    body_html = (
        f"{rows_html(facts)}"
        f'<p style="margin:20px 0 8px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:#5B6B7A;">Message</p>'
        f'<p style="margin:0;padding:14px 16px;background:#F7F5F1;border-radius:8px;'
        f'font-size:14px;line-height:1.55;color:#0E1E2B;white-space:pre-wrap;">'
        f"{escape(inquiry.message or '(empty)')}</p>"
        f'<p style="margin:20px 0 8px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:#5B6B7A;">Attribution</p>'
        f"{rows_html(_visit_pairs(inquiry))}"
        f"{cta}"
    )
    html = wrap_html(
        title="New project brief",
        intro=f"{inquiry.name} just submitted a brief on the website.",
        body_html=body_html,
    )
    _safe_send(
        subject=subject,
        text="\n".join(text_lines),
        html=html,
        recipients=[studio],
        reply_to=inquiry.email,
    )


def _send_visitor_confirmation(inquiry: InquiryMessage, service: str, budget: str) -> None:
    first_name = _one_line(inquiry.name).split(" ")[0] or "there"
    studio_wa = _whatsapp(WHATSAPP_NUMBER)
    privacy = f"{SITE_URL.rstrip('/')}/privacy"
    facts = [
        ("Name", inquiry.name),
        ("Email", inquiry.email),
        ("WhatsApp / phone", _blank(inquiry.phone)),
        ("Company", _blank(inquiry.company)),
        ("Country", _blank(inquiry.country)),
        ("What you need", service),
        ("When to start", _blank(inquiry.timeline)),
        ("Budget", budget),
        ("Link", _blank(inquiry.brief_link)),
    ]
    text = "\n".join(
        [
            f"Hi {first_name},",
            "",
            "Thank you for your brief. We have received it and will reply within one business day.",
            "",
            "Here is a copy of what you sent:",
            *[f"{label}: {value}" for label, value in facts],
            "Message:",
            inquiry.message or "",
            "",
            "Want to talk sooner?",
            f"Call: {PHONE_DISPLAY}",
            f"WhatsApp: {WHATSAPP_DISPLAY}",
            studio_wa or "",
            "",
            f"— {BRAND_NAME}",
            LEGAL_NAME,
            "Registered in Ghana",
            f"Privacy: {privacy}",
        ]
    )
    wa_button = ""
    if studio_wa:
        wa_button = (
            f'<p style="margin:20px 0 0;"><a href="{escape(studio_wa)}" '
            'style="display:inline-block;padding:11px 18px;background:#0E1E2B;color:#ffffff;'
            'text-decoration:none;border-radius:999px;font-size:14px;font-weight:600;">'
            "Message us on WhatsApp</a></p>"
        )
    body_html = (
        f'<p style="margin:0 0 8px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:#5B6B7A;">Your brief</p>'
        f"{rows_html(facts)}"
        f'<p style="margin:18px 0 8px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:#5B6B7A;">Message</p>'
        f'<p style="margin:0;padding:14px 16px;background:#F7F5F1;border-radius:8px;'
        f'font-size:14px;line-height:1.55;color:#0E1E2B;white-space:pre-wrap;">'
        f"{escape(inquiry.message or '')}</p>"
        f'<p style="margin:22px 0 0;font-size:15px;line-height:1.55;color:#0E1E2B;">'
        f"<strong>What happens next</strong><br />"
        f"We reply within one business day. If you would rather talk now, call or WhatsApp us.</p>"
        f"{wa_button}"
    )
    html = wrap_html(
        title="We received your brief",
        intro=f"Hi {first_name},\n\nThank you for writing to {BRAND_NAME}. Here is a copy of what you sent.",
        body_html=body_html,
        closing=f"Warm regards,\n{BRAND_NAME}",
    )
    _safe_send(
        subject=f"We received your brief — {BRAND_NAME}",
        text=text,
        html=html,
        recipients=[inquiry.email],
        reply_to=EMAIL,
    )


def notify_waitlist(signup: WaitlistSignup) -> None:
    studio = (getattr(settings, "STUDIO_NOTIFY_EMAIL", "") or "").strip()
    if not studio:
        return
    admin_url = _admin_change_url(signup)
    name = _blank(signup.name)
    facts = [("Name", name), ("Email", signup.email)]
    text = "\n".join(
        [f"{label}: {value}" for label, value in facts]
        + [""]
        + _visit_text(signup)
        + ["", f"Open in admin: {admin_url}"]
    )
    body_html = (
        f"{rows_html(facts)}"
        f'<p style="margin:20px 0 8px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:#5B6B7A;">Attribution</p>'
        f"{rows_html(_visit_pairs(signup))}"
        f'<p style="margin:16px 0 0;"><a href="{escape(admin_url)}" style="color:#2F6FED;font-size:13px;">'
        f"Open in admin →</a></p>"
    )
    html = wrap_html(
        title="SmartCRM waitlist",
        intro=f"{name} joined the SmartCRM waitlist.",
        body_html=body_html,
    )
    _safe_send(
        subject=_one_line(f"SmartCRM waitlist · {signup.email}"),
        text=text,
        html=html,
        recipients=[studio],
        reply_to=signup.email,
    )


def notify_newsletter(signup) -> None:
    studio = (getattr(settings, "STUDIO_NOTIFY_EMAIL", "") or "").strip()
    if not studio:
        return
    admin_url = _admin_change_url(signup)
    facts = [("Email", signup.email)]
    text = "\n".join(
        [f"Email: {signup.email}", ""] + _visit_text(signup) + ["", f"Open in admin: {admin_url}"]
    )
    body_html = (
        f"{rows_html(facts)}"
        f'<p style="margin:20px 0 8px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:#5B6B7A;">Attribution</p>'
        f"{rows_html(_visit_pairs(signup))}"
        f'<p style="margin:16px 0 0;"><a href="{escape(admin_url)}" style="color:#2F6FED;font-size:13px;">'
        f"Open in admin →</a></p>"
    )
    html = wrap_html(
        title="Newsletter signup",
        intro="Someone joined the newsletter list.",
        body_html=body_html,
    )
    _safe_send(
        subject=_one_line(f"Newsletter · {signup.email}"),
        text=text,
        html=html,
        recipients=[studio],
        reply_to=signup.email,
    )


def notify_academy(interest: AcademyInterest) -> None:
    studio = (getattr(settings, "STUDIO_NOTIFY_EMAIL", "") or "").strip()
    if not studio:
        return
    admin_url = _admin_change_url(interest)
    facts = [
        ("Name", interest.name),
        ("Email", interest.email),
        ("Message", _blank(interest.message)),
    ]
    text = "\n".join(
        [f"{label}: {value}" for label, value in facts]
        + [""]
        + _visit_text(interest)
        + ["", f"Open in admin: {admin_url}"]
    )
    body_html = (
        f"{rows_html(facts)}"
        f'<p style="margin:20px 0 8px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:#5B6B7A;">Attribution</p>'
        f"{rows_html(_visit_pairs(interest))}"
        f'<p style="margin:16px 0 0;"><a href="{escape(admin_url)}" style="color:#2F6FED;font-size:13px;">'
        f"Open in admin →</a></p>"
    )
    html = wrap_html(
        title="Academy interest",
        intro=f"{interest.name} asked about the Academy.",
        body_html=body_html,
    )
    _safe_send(
        subject=_one_line(f"Academy interest · {interest.name}"),
        text=text,
        html=html,
        recipients=[studio],
        reply_to=interest.email,
    )
