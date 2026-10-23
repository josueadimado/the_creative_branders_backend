"""URL paths under /api/ — each one only accepts POST."""
from django.urls import path

from .views import AcademyInterestCreateView, InquiryCreateView, WaitlistCreateView

urlpatterns = [
    path("inquiries/", InquiryCreateView.as_view(), name="inquiry-create"),
    path("waitlist/", WaitlistCreateView.as_view(), name="waitlist-create"),
    path("academy-interest/", AcademyInterestCreateView.as_view(), name="academy-interest-create"),
]
