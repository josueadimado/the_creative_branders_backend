"""
Turn form JSON into database rows (and reject bad input).

A serializer is the checklist: required fields, email format, max length.
The views below only accept POST (create), never GET lists.
"""
from urllib.parse import urlparse

from django.utils import timezone
from rest_framework import serializers

from .botcheck import BotCheckMixin
from .models import (
    BUDGET_OPTIONS_GHS,
    BUDGET_OPTIONS_USD,
    CURRENCY_OPTIONS,
    LEGACY_NEED_OPTIONS,
    NEED_OPTIONS,
    TIMELINE_OPTIONS,
    AcademyInterest,
    InquiryMessage,
    NewsletterSignup,
    WaitlistSignup,
)


class ConsentRecordMixin(serializers.Serializer):
    """The visitor must tick the privacy box. We store the time on the server."""

    consent = serializers.BooleanField(write_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.pop("consent", False) is not True:
            raise serializers.ValidationError(
                {"consent": "Please agree that we may use these details to reply to you."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["consent_at"] = timezone.now()
        return super().create(validated_data)


class VisitFieldsMixin(serializers.Serializer):
    """Optional campaign tags and the first page of the visit. Blank is fine."""

    utm_source = serializers.CharField(required=False, allow_blank=True, max_length=120)
    utm_medium = serializers.CharField(required=False, allow_blank=True, max_length=120)
    utm_campaign = serializers.CharField(required=False, allow_blank=True, max_length=160)
    utm_content = serializers.CharField(required=False, allow_blank=True, max_length=160)
    landing_page = serializers.CharField(required=False, allow_blank=True, max_length=300)
    referrer = serializers.CharField(required=False, allow_blank=True, max_length=300)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        limits = {
            "utm_source": 120,
            "utm_medium": 120,
            "utm_campaign": 160,
            "utm_content": 160,
            "landing_page": 300,
            "referrer": 300,
        }
        for name, limit in limits.items():
            if name in attrs:
                attrs[name] = str(attrs.get(name) or "").strip()[:limit]
        return attrs


VISIT_FIELDS = [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "landing_page",
    "referrer",
]


class InquiryMessageSerializer(VisitFieldsMixin, ConsentRecordMixin, BotCheckMixin, serializers.ModelSerializer):
    class Meta:
        model = InquiryMessage
        fields = [
            "name",
            "email",
            "phone",
            "company",
            "country",
            "needs",
            "timeline",
            "budget_range",
            "budget_currency",
            "brief_link",
            "message",
            "consent",
            *VISIT_FIELDS,
            # Not saved. The bot check reads these, then removes them.
            "website",
            "form_started",
        ]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_timeline(self, value: str) -> str:
        if value and value not in TIMELINE_OPTIONS:
            raise serializers.ValidationError("Choose a listed timeline.")
        return value

    def validate_budget_range(self, value: str) -> str:
        if value and value not in BUDGET_OPTIONS_GHS and value not in BUDGET_OPTIONS_USD:
            raise serializers.ValidationError("Choose a listed budget range.")
        return value

    def validate_budget_currency(self, value: str) -> str:
        if value and value not in CURRENCY_OPTIONS:
            raise serializers.ValidationError("Choose cedis or dollars.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        budget = attrs.get("budget_range") or ""
        currency = attrs.get("budget_currency") or ""
        # A cedi band must be saved as GHS, and a dollar band as USD.
        if budget in BUDGET_OPTIONS_GHS and currency != "GHS":
            raise serializers.ValidationError({"budget_currency": "Choose cedis for that budget range."})
        if budget in BUDGET_OPTIONS_USD and currency != "USD":
            raise serializers.ValidationError({"budget_currency": "Choose dollars for that budget range."})
        return attrs

    def validate_needs(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("Choose what you need.")
        allowed = set(NEED_OPTIONS) | set(LEGACY_NEED_OPTIONS)
        # One of each listed choice is enough. A long repeated list is not a person.
        if len(value) > len(allowed):
            raise serializers.ValidationError("Choose what you need from the list.")
        unknown = [item for item in value if item not in allowed]
        if unknown:
            raise serializers.ValidationError("Choose what you need from the list.")
        return value

    def validate_message(self, value: str) -> str:
        return _limited_text(value, 4000, "Tell us about the project in 4,000 characters or less.")

    def validate_brief_link(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            return ""
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise serializers.ValidationError("Enter a full web address, starting with https://")
        return value


class WaitlistSignupSerializer(VisitFieldsMixin, ConsentRecordMixin, BotCheckMixin, serializers.ModelSerializer):
    class Meta:
        model = WaitlistSignup
        fields = ["email", "name", "consent", "website", "form_started", *VISIT_FIELDS]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class NewsletterSignupSerializer(VisitFieldsMixin, ConsentRecordMixin, BotCheckMixin, serializers.ModelSerializer):
    """There is no public newsletter form yet. When one is added, it must send consent."""
    class Meta:
        model = NewsletterSignup
        fields = ["email", "consent", "website", "form_started", *VISIT_FIELDS]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


def _limited_text(value: str, limit: int, message: str) -> str:
    """Keep a written answer inside a fixed size so a script cannot send a huge page."""
    text = (value or "").strip()
    if len(text) > limit:
        raise serializers.ValidationError(message)
    return text


class AcademyInterestSerializer(VisitFieldsMixin, ConsentRecordMixin, BotCheckMixin, serializers.ModelSerializer):
    class Meta:
        model = AcademyInterest
        fields = ["name", "email", "message", "consent", "website", "form_started", *VISIT_FIELDS]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_message(self, value: str) -> str:
        return _limited_text(value, 4000, "Keep the note to 4,000 characters or less.")
