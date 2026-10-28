"""
Shared look for studio and visitor emails.

Plain text is always included. HTML is a simple, email-safe layout that
matches the site palette (navy / paper) without heavy images or fonts.
"""
from __future__ import annotations

import html
from typing import Iterable

from .site_settings import BRAND_NAME, EMAIL, LEGAL_NAME, PHONE_DISPLAY, SITE_URL, WHATSAPP_DISPLAY


NAVY = "#0E1E2B"
SLATE = "#5B6B7A"
PAPER = "#F7F5F1"
MIST = "#E4E0D8"
SIGNAL = "#2F6FED"


def escape(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def rows_html(pairs: Iterable[tuple[str, str]]) -> str:
    """A compact definition list for email clients."""
    items = []
    for label, value in pairs:
        text = (value or "").strip() or "—"
        items.append(
            "<tr>"
            f'<td style="padding:6px 12px 6px 0;color:{SLATE};font-size:13px;'
            f'vertical-align:top;white-space:nowrap;">{escape(label)}</td>'
            f'<td style="padding:6px 0;color:{NAVY};font-size:14px;'
            f'vertical-align:top;">{escape(text).replace(chr(10), "<br>")}</td>'
            "</tr>"
        )
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" '
        f'style="width:100%;border-collapse:collapse;">{"".join(items)}</table>'
    )


def wrap_html(*, title: str, intro: str, body_html: str, closing: str = "") -> str:
    """Full HTML document with a branded header and footer."""
    site = escape(SITE_URL.rstrip("/"))
    privacy = f"{site}/privacy"
    brand = escape(BRAND_NAME)
    legal = escape(LEGAL_NAME)
    title_safe = escape(title)
    intro_safe = escape(intro).replace("\n", "<br>")
    closing_block = ""
    if closing:
        closing_block = (
            f'<p style="margin:24px 0 0;color:{NAVY};font-size:14px;line-height:1.55;">'
            f"{escape(closing).replace(chr(10), '<br>')}</p>"
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title_safe}</title>
</head>
<body style="margin:0;padding:0;background:{PAPER};">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:{PAPER};">
    <tr>
      <td align="center" style="padding:28px 16px;">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:560px;background:#ffffff;border:1px solid {MIST};border-radius:12px;overflow:hidden;">
          <tr>
            <td style="background:{NAVY};padding:22px 28px;">
              <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:rgba(255,255,255,0.65);">
                {brand}
              </p>
              <h1 style="margin:8px 0 0;font-family:Arial,Helvetica,sans-serif;font-size:22px;line-height:1.25;font-weight:700;color:#ffffff;">
                {title_safe}
              </h1>
            </td>
          </tr>
          <tr>
            <td style="padding:28px;font-family:Arial,Helvetica,sans-serif;color:{NAVY};">
              <p style="margin:0 0 18px;font-size:15px;line-height:1.6;color:{NAVY};">{intro_safe}</p>
              {body_html}
              {closing_block}
              <hr style="border:none;border-top:1px solid {MIST};margin:28px 0;" />
              <p style="margin:0;font-size:13px;line-height:1.55;color:{SLATE};">
                {escape(EMAIL)} · {escape(PHONE_DISPLAY)} · WhatsApp {escape(WHATSAPP_DISPLAY)}<br />
                <a href="{site}" style="color:{SIGNAL};text-decoration:none;">{site}</a>
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:14px 28px 20px;background:{PAPER};font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:1.5;color:{SLATE};">
              {legal} · Registered in Ghana<br />
              <a href="{privacy}" style="color:{SLATE};">Privacy</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
