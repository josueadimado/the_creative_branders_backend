"""
Database tables for the public forms on the website.

Each row is created when a visitor submits a form. Staff review them
in Django admin — there is no public "list" API.
"""
from django.db import models


# Stored as the words the visitor saw, so the admin screen matches the form.
# These must stay the same as the choices in frontend/src/content/contact.ts.
NEED_OPTIONS = [
    "Brand and websites",
    "Web applications",
    "Mobile apps",
    "Automation and reporting",
    "Not sure yet",
]
# Words from the earlier form. Still accepted so an old page can send them.
LEGACY_NEED_OPTIONS = [
    "Website",
    "Web app",
    "Mobile app",
    "Brand and design",
    "Automation and AI",
    "Data and reporting",
]
TIMELINE_OPTIONS = [
    "As soon as possible",
    "In the next 1 to 3 months",
    "In 3 to 6 months",
    "Just exploring",
]
BUDGET_OPTIONS_GHS = [
    "Under 25,000",
    "25,000–75,000",
    "75,000–200,000",
    "200,000–500,000",
    "Over 500,000",
]
BUDGET_OPTIONS_USD = [
    "Under $2,000",
    "$2,000 to $5,000",
    "$5,000 to $15,000",
    "$15,000 to $40,000",
    "Over $40,000",
    "I'd rather discuss it",
]
# Both lists together, so an old dollar range and a new cedi range are both allowed.
BUDGET_OPTIONS = BUDGET_OPTIONS_GHS + BUDGET_OPTIONS_USD
CURRENCY_OPTIONS = ["GHS", "USD"]


class VisitRecord(models.Model):
    """How this visitor arrived. Shared by every public form."""

    utm_source = models.CharField(max_length=120, blank=True)
    utm_medium = models.CharField(max_length=120, blank=True)
    utm_campaign = models.CharField(max_length=160, blank=True)
    utm_content = models.CharField(max_length=160, blank=True)
    landing_page = models.CharField(max_length=300, blank=True)
    referrer = models.CharField(max_length=300, blank=True)

    class Meta:
        abstract = True


class InquiryMessage(VisitRecord):
    """A project brief from the contact page."""

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=160, blank=True)
    country = models.CharField(max_length=80, blank=True)
    needs = models.JSONField(default=list, blank=True)
    timeline = models.CharField(max_length=80, blank=True)
    budget_range = models.CharField(max_length=80, blank=True)
    # GHS or USD. Blank on briefs saved before the currency switch existed.
    budget_currency = models.CharField(max_length=3, blank=True)
    brief_link = models.CharField(max_length=300, blank=True)
    message = models.TextField()
    reviewed = models.BooleanField(default=False)
    # Empty on older rows that were saved before the privacy box existed.
    consent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the visitor agreed we may use these details to reply.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"

    def __str__(self) -> str:
        return f"{self.name} — {self.email} ({self.created_at:%Y-%m-%d})"


class WaitlistSignup(VisitRecord):
    """SmartCRM landing page waitlist."""

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120, blank=True)
    consent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the visitor agreed we may use these details to reply.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Waitlist signup"
        verbose_name_plural = "Waitlist signups"

    def __str__(self) -> str:
        return self.email


class NewsletterSignup(VisitRecord):
    """Footer signup for studio news and updates."""

    email = models.EmailField(unique=True)
    consent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the visitor agreed we may use these details to reply.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Newsletter signup"
        verbose_name_plural = "Newsletter signups"

    def __str__(self) -> str:
        return self.email


class AcademyInterest(VisitRecord):
    """Academy expression-of-interest form."""

    name = models.CharField(max_length=120)
    email = models.EmailField()
    message = models.TextField(blank=True)
    consent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the visitor agreed we may use these details to reply.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Academy interest"
        verbose_name_plural = "Academy interest"

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"


class StudioEvent(models.Model):
    """
    A meaningful site action, stored after analytics consent.
    Page views stay in GA4. This table is for contact CTAs, case opens, and form success.
    """

    name = models.CharField(max_length=64, db_index=True)
    page_path = models.CharField(max_length=300, blank=True, db_index=True)
    # Small key/value bag for location, button, case_study, filter, budget, and so on.
    props = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Studio event"
        verbose_name_plural = "Studio events"
        indexes = [
            models.Index(fields=["name", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} @ {self.page_path or '/'} ({self.created_at:%Y-%m-%d %H:%M})"
