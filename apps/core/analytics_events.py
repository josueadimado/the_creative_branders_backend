"""Allowed studio-log event names and helpers for the public ingest endpoint."""

# Page views stay in GA4. Only business actions land in our database.
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

# Friendly labels for the Desk activity feed.
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
}
