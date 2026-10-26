"""Show form submissions in Django admin so they can be triaged without extra tools."""
from django.contrib import admin

from .models import AcademyInterest, InquiryMessage, NewsletterSignup, WaitlistSignup

VISIT_FIELDS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "landing_page",
    "referrer",
)


@admin.register(InquiryMessage)
class InquiryMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "country", "timeline", "budget_currency", "budget_range", "utm_source", "created_at")
    list_filter = ("timeline", "budget_currency", "budget_range", "country", "created_at")
    search_fields = ("name", "email", "company", "country", "phone", "message", "utm_source", "utm_campaign")
    readonly_fields = ("consent_at", "created_at", *VISIT_FIELDS)


@admin.register(WaitlistSignup)
class WaitlistSignupAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "utm_source", "created_at")
    search_fields = ("email", "name", "utm_source", "utm_campaign")
    readonly_fields = ("consent_at", "created_at", *VISIT_FIELDS)


@admin.register(NewsletterSignup)
class NewsletterSignupAdmin(admin.ModelAdmin):
    list_display = ("email", "utm_source", "created_at")
    search_fields = ("email", "utm_source", "utm_campaign")
    readonly_fields = ("consent_at", "created_at", *VISIT_FIELDS)


@admin.register(AcademyInterest)
class AcademyInterestAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "utm_source", "created_at")
    search_fields = ("name", "email", "message", "utm_source", "utm_campaign")
    readonly_fields = ("consent_at", "created_at", *VISIT_FIELDS)
