"""URL paths under /api/ — each one only accepts POST."""
from django.urls import path

from .views import (
    AcademyInterestCreateView,
    InquiryCreateView,
    NewsletterCreateView,
    StudioEventCreateView,
    WaitlistCreateView,
)

urlpatterns = [
    path("inquiries/", InquiryCreateView.as_view(), name="inquiry-create"),
    path("waitlist/", WaitlistCreateView.as_view(), name="waitlist-create"),
    path("newsletter/", NewsletterCreateView.as_view(), name="newsletter-create"),
    path("academy-interest/", AcademyInterestCreateView.as_view(), name="academy-interest-create"),
    path("analytics/events/", StudioEventCreateView.as_view(), name="studio-event-create"),
]
