"""Show form submissions in Django admin so they can be triaged without extra tools."""
from django.contrib import admin

from .models import AcademyInterest, InquiryMessage, NewsletterSignup, WaitlistSignup


@admin.register(InquiryMessage)
class InquiryMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "country", "timeline", "budget_range", "created_at")
    list_filter = ("timeline", "budget_range", "country", "created_at")
    search_fields = ("name", "email", "company", "country", "phone", "message")
    readonly_fields = ("consent_at", "created_at")


@admin.register(WaitlistSignup)
class WaitlistSignupAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "created_at")
    search_fields = ("email", "name")
    readonly_fields = ("consent_at", "created_at")


@admin.register(NewsletterSignup)
class NewsletterSignupAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at")
    search_fields = ("email",)
    readonly_fields = ("consent_at", "created_at")


@admin.register(AcademyInterest)
class AcademyInterestAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at")
    search_fields = ("name", "email", "message")
    readonly_fields = ("consent_at", "created_at")
