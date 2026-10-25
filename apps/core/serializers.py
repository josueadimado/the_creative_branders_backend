"""
Turn form JSON into database rows (and reject bad input).

A serializer is the checklist: required fields, email format, max length.
The views below only accept POST (create), never GET lists.
"""
from urllib.parse import urlparse

from rest_framework import serializers

from .botcheck import BotCheckMixin
from .models import (
    BUDGET_OPTIONS,
    LEGACY_NEED_OPTIONS,
    NEED_OPTIONS,
    TIMELINE_OPTIONS,
    AcademyInterest,
    InquiryMessage,
    NewsletterSignup,
    WaitlistSignup,
)


class InquiryMessageSerializer(BotCheckMixin, serializers.ModelSerializer):
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
            "brief_link",
            "message",
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
        if value and value not in BUDGET_OPTIONS:
            raise serializers.ValidationError("Choose a listed budget range.")
        return value

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


class WaitlistSignupSerializer(BotCheckMixin, serializers.ModelSerializer):
    class Meta:
        model = WaitlistSignup
        fields = ["email", "name", "website", "form_started"]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class NewsletterSignupSerializer(BotCheckMixin, serializers.ModelSerializer):
    class Meta:
        model = NewsletterSignup
        fields = ["email", "website", "form_started"]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


def _limited_text(value: str, limit: int, message: str) -> str:
    """Keep a written answer inside a fixed size so a script cannot send a huge page."""
    text = (value or "").strip()
    if len(text) > limit:
        raise serializers.ValidationError(message)
    return text


class AcademyInterestSerializer(BotCheckMixin, serializers.ModelSerializer):
    class Meta:
        model = AcademyInterest
        fields = ["name", "email", "message", "website", "form_started"]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_message(self, value: str) -> str:
        return _limited_text(value, 4000, "Keep the note to 4,000 characters or less.")
