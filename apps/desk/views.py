"""
The studio desk API.

The public website can read published pages. Only a staff sign-in can
change them, or read the form messages, through these addresses.
"""
from django.contrib.auth import authenticate
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.models import Note, Page, Project, ProjectShot, SiteSettings
from apps.core.guards import clear_login_failures, login_blocked, note_login_failure
from apps.core.models import AcademyInterest, InquiryMessage, NewsletterSignup, WaitlistSignup

from .serializers import (
    AcademyDeskSerializer,
    InquiryDeskSerializer,
    NewsletterDeskSerializer,
    NoteDeskSerializer,
    PageDeskSerializer,
    ProjectDeskSerializer,
    SettingsDeskSerializer,
    ShotDeskSerializer,
    WaitlistDeskSerializer,
)


class DeskAPIView(APIView):
    """Every desk screen except sign-in. A staff token is required."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]
    # Staff are signed in, so the public form limits do not apply here.
    throttle_classes = []


class DeskLoginView(APIView):
    """Check the staff username and password, then hand back a token."""

    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        if login_blocked("desk", request):
            return Response(
                {"detail": "Too many sign-in attempts. Wait 15 minutes and try again."},
                status=429,
            )
        username = str(request.data.get("username", "")).strip()
        password = str(request.data.get("password", ""))
        user = authenticate(request, username=username, password=password)
        # Same sentence for a wrong password and for someone who is not staff,
        # so the form does not reveal which usernames exist.
        if user is None or not user.is_active or not user.is_staff:
            note_login_failure("desk", request)
            return Response({"detail": "That username or password is not right."}, status=400)
        clear_login_failures("desk", request)
        token, _created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "username": user.username})


class DeskLogoutView(DeskAPIView):
    """Throw away the token so the next visit has to sign in again."""

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=204)


class DeskMeView(DeskAPIView):
    def get(self, request):
        return Response({"username": request.user.username})


def _project_card(project: Project) -> dict:
    """The few fields the dashboard needs. The full editor loads the rest."""

    return {
        "id": project.id,
        "public_name": project.public_name,
        "published": project.published,
        "featured": project.featured,
        "family": project.family,
    }


class OverviewView(DeskAPIView):
    """The desk home: what is waiting, and what is already on the website."""

    def get(self, request):
        projects = Project.objects.all()
        notes = Note.objects.all()
        # Site order, so the dashboard matches the work page.
        drafts = projects.filter(published=False)[:5]
        leading = projects.filter(published=True)[:4]
        latest = InquiryMessage.objects.all()[:5]
        return Response(
            {
                "pages": Page.objects.count(),
                "projects": projects.count(),
                "published_projects": projects.filter(published=True).count(),
                "notes": notes.count(),
                "published_notes": notes.filter(published=True).count(),
                "inquiries": InquiryMessage.objects.count(),
                "unread_inquiries": InquiryMessage.objects.filter(reviewed=False).count(),
                "waitlist": WaitlistSignup.objects.count(),
                "newsletter": NewsletterSignup.objects.count(),
                "academy": AcademyInterest.objects.count(),
                "latest_inquiries": InquiryDeskSerializer(latest, many=True).data,
                "draft_projects": [_project_card(project) for project in drafts],
                "leading_projects": [_project_card(project) for project in leading],
            }
        )


class PageListView(DeskAPIView):
    def get(self, request):
        pages = Page.objects.all()
        return Response(PageDeskSerializer(pages, many=True).data)


class PageDetailView(DeskAPIView):
    def get(self, request, slug):
        page = get_object_or_404(Page, slug=slug)
        return Response(PageDeskSerializer(page).data)

    def patch(self, request, slug):
        page = get_object_or_404(Page, slug=slug)
        serializer = PageDeskSerializer(page, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProjectListView(DeskAPIView):
    def get(self, request):
        projects = Project.objects.all().prefetch_related("shots")
        return Response(ProjectDeskSerializer(projects, many=True, context={"request": request}).data)

    def post(self, request):
        payload = dict(request.data)
        # A blank "New project" still needs a name and a service so the row can be saved.
        payload.setdefault("public_name", "Untitled project")
        payload.setdefault("family", "brand-websites")
        serializer = ProjectDeskSerializer(data=payload, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)


class ProjectDetailView(DeskAPIView):
    def get(self, request, pk):
        project = get_object_or_404(Project.objects.prefetch_related("shots"), pk=pk)
        return Response(ProjectDeskSerializer(project, context={"request": request}).data)

    def patch(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        serializer = ProjectDeskSerializer(project, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        project = Project.objects.prefetch_related("shots").get(pk=project.pk)
        return Response(ProjectDeskSerializer(project, context={"request": request}).data)

    def delete(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        for shot in project.shots.all():
            if shot.upload:
                shot.upload.delete(save=False)
        if project.logo_upload:
            project.logo_upload.delete(save=False)
        project.delete()
        return Response(status=204)


class ProjectLogoView(DeskAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        upload = request.FILES.get("upload")
        if upload is None:
            return Response({"detail": "Choose a logo file."}, status=400)
        if project.logo_upload:
            project.logo_upload.delete(save=False)
        project.logo_upload = upload
        project.save(update_fields=["logo_upload"])
        return Response(ProjectDeskSerializer(project, context={"request": request}).data)


class ShotListView(DeskAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        upload = request.FILES.get("upload")
        existing = str(request.data.get("existing_path", "")).strip()
        if upload is None and not existing:
            return Response(
                {"detail": "Choose a picture, or paste a picture path that is already on the site."},
                status=400,
            )
        try:
            sort_order = int(request.data.get("sort_order") or 0)
        except (TypeError, ValueError):
            sort_order = 0
        shot = ProjectShot(
            project=project,
            existing_path="" if upload is not None else existing,
            alt=str(request.data.get("alt", "")).strip(),
            sort_order=sort_order,
        )
        if upload is not None:
            shot.upload = upload
        shot.save()
        return Response(ShotDeskSerializer(shot, context={"request": request}).data, status=201)


class ShotDetailView(DeskAPIView):
    def patch(self, request, pk):
        shot = get_object_or_404(ProjectShot, pk=pk)
        serializer = ShotDeskSerializer(shot, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        shot = get_object_or_404(ProjectShot, pk=pk)
        if shot.upload:
            shot.upload.delete(save=False)
        shot.delete()
        return Response(status=204)


class NoteListView(DeskAPIView):
    def get(self, request):
        return Response(NoteDeskSerializer(Note.objects.all(), many=True).data)

    def post(self, request):
        payload = dict(request.data)
        payload.setdefault("title", "Untitled note")
        payload.setdefault("family", "brand-websites")
        serializer = NoteDeskSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)


class NoteDetailView(DeskAPIView):
    def get(self, request, pk):
        note = get_object_or_404(Note, pk=pk)
        return Response(NoteDeskSerializer(note).data)

    def patch(self, request, pk):
        note = get_object_or_404(Note, pk=pk)
        serializer = NoteDeskSerializer(note, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        note = get_object_or_404(Note, pk=pk)
        note.delete()
        return Response(status=204)


class SettingsView(DeskAPIView):
    def get(self, request):
        row = SiteSettings.objects.first()
        if row is None:
            row = SiteSettings.objects.create(description="")
        return Response(SettingsDeskSerializer(row).data)

    def patch(self, request):
        row = SiteSettings.objects.first()
        if row is None:
            row = SiteSettings.objects.create(description="")
        serializer = SettingsDeskSerializer(row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


def _search(queryset, request, *fields: str):
    text = request.query_params.get("q", "").strip()
    if not text:
        return queryset
    query = Q()
    for field in fields:
        query |= Q(**{f"{field}__icontains": text})
    return queryset.filter(query)


class InquiryListView(DeskAPIView):
    def get(self, request):
        rows = _search(InquiryMessage.objects.all(), request, "name", "email", "company", "message")
        return Response(InquiryDeskSerializer(rows, many=True).data)


class InquiryDetailView(DeskAPIView):
    def get(self, request, pk):
        row = get_object_or_404(InquiryMessage, pk=pk)
        return Response(InquiryDeskSerializer(row).data)

    def post(self, request, pk):
        """Mark the brief as seen. The page calls this after it has drawn the New badge."""

        row = get_object_or_404(InquiryMessage, pk=pk)
        if not row.reviewed:
            row.reviewed = True
            row.save(update_fields=["reviewed"])
        return Response(status=204)

    def delete(self, request, pk):
        row = get_object_or_404(InquiryMessage, pk=pk)
        row.delete()
        return Response(status=204)


class WaitlistListView(DeskAPIView):
    def get(self, request, pk=None):
        rows = _search(WaitlistSignup.objects.all(), request, "email", "name")
        return Response(WaitlistDeskSerializer(rows, many=True).data)

    def delete(self, request, pk):
        row = get_object_or_404(WaitlistSignup, pk=pk)
        row.delete()
        return Response(status=204)


class NewsletterListView(DeskAPIView):
    def get(self, request, pk=None):
        rows = _search(NewsletterSignup.objects.all(), request, "email")
        return Response(NewsletterDeskSerializer(rows, many=True).data)

    def delete(self, request, pk):
        row = get_object_or_404(NewsletterSignup, pk=pk)
        row.delete()
        return Response(status=204)


class AcademyListView(DeskAPIView):
    def get(self, request, pk=None):
        rows = _search(AcademyInterest.objects.all(), request, "name", "email", "message")
        return Response(AcademyDeskSerializer(rows, many=True).data)

    def delete(self, request, pk):
        row = get_object_or_404(AcademyInterest, pk=pk)
        row.delete()
        return Response(status=204)
