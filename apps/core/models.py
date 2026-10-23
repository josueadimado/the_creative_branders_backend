"""
Database tables for the three public forms on the website.

Each row is created when a visitor submits a form. Staff review them
in Django admin — there is no public "list" API.
"""
from django.db import models


class InquiryMessage(models.Model):
    """Contact page: name, email, optional phone/company, country, budget, message."""

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=160, blank=True)
    country = models.CharField(max_length=80)
    budget_range = models.CharField(max_length=40)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"

    def __str__(self) -> str:
        return f"{self.name} — {self.email} ({self.created_at:%Y-%m-%d})"


class WaitlistSignup(models.Model):
    """SmartCRM landing page waitlist."""

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Waitlist signup"
        verbose_name_plural = "Waitlist signups"

    def __str__(self) -> str:
        return self.email


class AcademyInterest(models.Model):
    """Academy expression-of-interest form."""

    name = models.CharField(max_length=120)
    email = models.EmailField()
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Academy interest"
        verbose_name_plural = "Academy interest"

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"
