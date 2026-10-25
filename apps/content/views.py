"""
Public read-only pages.

Anyone can read published content. Nothing here accepts a form post.
Editing happens in /admin/, behind the staff login.
"""
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Note, Page, Project, SiteSettings
from .serializers import NoteSerializer, PageSerializer, ProjectSerializer, SiteSettingsSerializer


class ContentReadMixin:
    # Reading the site must not share the tight limit used by the contact form.
    throttle_classes = []


class ProjectListView(ContentReadMixin, ListAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.filter(published=True).prefetch_related("shots")


class ProjectDetailView(ContentReadMixin, RetrieveAPIView):
    serializer_class = ProjectSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Project.objects.filter(published=True).prefetch_related("shots")


class PageListView(ContentReadMixin, ListAPIView):
    serializer_class = PageSerializer
    queryset = Page.objects.all()


class NoteListView(ContentReadMixin, ListAPIView):
    serializer_class = NoteSerializer

    def get_queryset(self):
        return Note.objects.filter(published=True)


class SiteSettingsView(ContentReadMixin, APIView):
    def get(self, request):
        settings_row = SiteSettings.objects.first()
        if settings_row is None:
            return Response({})
        return Response(SiteSettingsSerializer(settings_row).data)
