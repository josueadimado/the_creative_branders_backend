"""Company details for emails and other server-side text.

Keep this file in step with frontend/src/content/site.ts.
Text in [square brackets] is still waiting for the owner. Do not invent those values.
"""

BRAND_NAME = "The Creative Branders"
LEGAL_NAME = "The Creative Branders LTD"
JURISDICTION = "Ghana"
REGISTRATION_AUTHORITY = "Office of the Registrar of Companies (ORC), Ghana"
# Leave blank and the legal pages skip this line.
REGISTRATION_NUMBER = ""
# Street or GhanaPost address. Leave blank and the legal pages show only Accra, Ghana.
STREET_ADDRESS = ""

ADDRESS = {
    "city": "Accra",
    "region": "Greater Accra",
    "country": "Ghana",
    "country_code": "GH",
}

EMAIL = "hello@thecreativebranders.com"
PHONE_E164 = "+233206783693"
PHONE_DISPLAY = "+233 20 678 3693"
WHATSAPP_NUMBER = "233206783693"
WHATSAPP_DEFAULT_MESSAGE = "Hello The Creative Branders, I'd like to talk about a project."
# A real booking page. Leave this blank and the audit button opens WhatsApp.
BOOKING_URL = ""
SITE_URL = "https://thecreativebranders.com"

SOCIAL = {
    "linkedin": "https://www.linkedin.com/company/thecreativebranders",
    "instagram": "https://www.instagram.com/thecreativebranders",
    "facebook": "https://www.facebook.com/thecreativebranders",
}


def from_address() -> str:
    """Sender line on outgoing mail, for example: The Creative Branders <hello@...>."""
    return f"{BRAND_NAME} <{EMAIL}>"
