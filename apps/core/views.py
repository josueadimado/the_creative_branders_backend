"""
Create-only API views. The website POSTs here; nothing is listed publicly.

Throttle scopes slow down spam. Authentication is off so the React app
can submit without a login cookie (CSRF does not block these POSTs).
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .guards import client_ip
from .models import AcademyInterest, InquiryMessage, NewsletterSignup, StudioEvent, WaitlistSignup
from .notify import notify_academy, notify_inquiry, notify_newsletter, notify_waitlist
from .serializers import (
    AcademyInterestSerializer,
    InquiryMessageSerializer,
    NewsletterSignupSerializer,
    StudioEventSerializer,
    WaitlistSignupSerializer,
)
from .visit_context import device_from_user_agent, lookup_ip_location


class InquiryCreateView(generics.CreateAPIView):
    queryset = InquiryMessage.objects.all()
    serializer_class = InquiryMessageSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "inquiry"

    def perform_create(self, serializer):
        inquiry = serializer.save()
        notify_inquiry(inquiry)


class WaitlistCreateView(generics.CreateAPIView):
    queryset = WaitlistSignup.objects.all()
    serializer_class = WaitlistSignupSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "waitlist"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        existing = WaitlistSignup.objects.filter(email=email).first()
        if existing:
            # Duplicate email: treat as success so the visitor sees a calm message.
            return Response(
                {"detail": "already_on_list", "already_on_list": True},
                status=status.HTTP_200_OK,
            )
        signup = serializer.save()
        notify_waitlist(signup)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class NewsletterCreateView(generics.CreateAPIView):
    queryset = NewsletterSignup.objects.all()
    serializer_class = NewsletterSignupSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "newsletter"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        if NewsletterSignup.objects.filter(email=email).exists():
            return Response(
                {"detail": "already_subscribed", "already_subscribed": True},
                status=status.HTTP_200_OK,
            )
        signup = serializer.save()
        notify_newsletter(signup)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class AcademyInterestCreateView(generics.CreateAPIView):
    queryset = AcademyInterest.objects.all()
    serializer_class = AcademyInterestSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "academy"

    def perform_create(self, serializer):
        interest = serializer.save()
        notify_academy(interest)


class StudioEventCreateView(generics.CreateAPIView):
    """Store one consented studio action. No list is exposed publicly."""

    queryset = StudioEvent.objects.all()
    serializer_class = StudioEventSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "studio_event"

    def perform_create(self, serializer):
        request = self.request
        user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:400]
        device_hint = serializer.validated_data.get("device") or ""
        raw_ip = (client_ip(request) or "").strip()
        # GenericIPAddressField rejects placeholders like "unknown".
        saved_ip = raw_ip if raw_ip and raw_ip.lower() != "unknown" else None
        geo = lookup_ip_location(saved_ip or "")
        serializer.save(
            client_ip=saved_ip,
            user_agent=user_agent,
            device=device_from_user_agent(user_agent, device_hint),
            country_code=geo.get("country_code") or "",
            country=geo.get("country") or "",
            city=geo.get("city") or "",
            region=geo.get("region") or "",
        )
