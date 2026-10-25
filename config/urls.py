"""
Root URL map for the project.

/admin/        — content desk and form messages
/api/          — public form posts
/api/content/  — public read of pages, projects, and notes
/media/        — pictures uploaded in the content desk
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

admin.site.site_header = "The Creative Branders"
admin.site.site_title = "TCB content desk"
admin.site.index_title = "Pages, projects, notes, and messages"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/content/", include("apps.content.urls")),
    path("api/", include("apps.core.urls")),
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
]
