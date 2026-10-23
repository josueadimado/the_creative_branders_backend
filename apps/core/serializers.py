"""
Turn form JSON into database rows (and reject bad input).

A serializer is the checklist: required fields, email format, max length.
The views below only accept POST (create), never GET lists.
"""
from rest_framework import serializers

from .models import (
    BUDGET_OPTIONS,
    NEED_OPTIONS,
    TIMELINE_OPTIONS,
    AcademyInterest,
    InquiryMessage,
    WaitlistSignup,
)


class InquiryMessageSerializer(serializers.ModelSerializer):
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
        ]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_needs(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("Choose what you need.")
        unknown = [item for item in value if item not in NEED_OPTIONS]
        if unknown:
            raise serializers.ValidationError("Choose a listed option.")
        return value

    def validate_timeline(self, value: str) -> str:
        if value and value not in TIMELINE_OPTIONS:
            raise serializers.ValidationError("Choose a listed timeline.")
        return value

    def validate_budget_range(self, value: str) -> str:
        if value and value not in BUDGET_OPTIONS:
            raise serializers.ValidationError("Choose a listed budget range.")
        return value


class WaitlistSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistSignup
        fields = ["email", "name"]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class AcademyInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademyInterest
        fields = ["name", "email", "message"]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()
