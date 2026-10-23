"""
Turn form JSON into database rows (and reject bad input).

A serializer is the checklist: required fields, email format, max length.
The views below only accept POST (create), never GET lists.
"""
from rest_framework import serializers

from .models import AcademyInterest, InquiryMessage, WaitlistSignup


class InquiryMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquiryMessage
        fields = [
            "name",
            "email",
            "phone",
            "company",
            "country",
            "budget_range",
            "message",
        ]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


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
