from django.urls import path

from .views import NoteListView, PageListView, ProjectDetailView, ProjectListView, SiteSettingsView

urlpatterns = [
    path("site/", SiteSettingsView.as_view(), name="content-site"),
    path("pages/", PageListView.as_view(), name="content-pages"),
    path("projects/", ProjectListView.as_view(), name="content-projects"),
    path("projects/<slug:slug>/", ProjectDetailView.as_view(), name="content-project"),
    path("notes/", NoteListView.as_view(), name="content-notes"),
]
