"""Allowed studio-log event names and helpers for the public ingest endpoint."""

# Business actions + journey signals (page timing, errors). All require analytics consent.
ALLOWED_EVENT_NAMES = frozenset(
    {
        "start_project_click",
        "audit_cta_click",
        "case_study_view",
        "work_filter",
        "whatsapp_click",
        "email_click",
        "phone_click",
        "brief_submit",
        "waitlist_signup",
        # Visitor journey (Desk Journeys)
        "page_view",
        "page_leave",
        "js_error",
        "form_error",
    }
)

CONTACT_EVENT_NAMES = frozenset(
    {
        "start_project_click",
        "audit_cta_click",
        "whatsapp_click",
        "email_click",
        "phone_click",
    }
)

CONVERSION_EVENT_NAMES = frozenset(
    {
        "brief_submit",
        "waitlist_signup",
        *CONTACT_EVENT_NAMES,
    }
)

# Friendly labels for the Desk activity feed and journey timeline.
EVENT_LABELS = {
    "start_project_click": "Start a project",
    "audit_cta_click": "Audit request clicked",
    "case_study_view": "Case study view",
    "work_filter": "Work filter",
    "whatsapp_click": "WhatsApp",
    "email_click": "Email",
    "phone_click": "Call",
    "brief_submit": "Brief submitted",
    "waitlist_signup": "Waitlist signup",
    "page_view": "Opened page",
    "page_leave": "Left page",
    "js_error": "Page error",
    "form_error": "Form error",
}
