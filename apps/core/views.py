"""
Create-only API views. The website POSTs here; nothing is listed publicly.

Throttle scopes slow down spam. Authentication is off so the React app
can submit without a login cookie (CSRF does not block these POSTs).
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import AcademyInterest, InquiryMessage, WaitlistSignup
from .notify import notify_academy, notify_inquiry, notify_waitlist
from .serializers import (
    AcademyInterestSerializer,
    InquiryMessageSerializer,
    WaitlistSignupSerializer,
)


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


class AcademyInterestCreateView(generics.CreateAPIView):
    queryset = AcademyInterest.objects.all()
    serializer_class = AcademyInterestSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "academy"

    def perform_create(self, serializer):
        interest = serializer.save()
        notify_academy(interest)
