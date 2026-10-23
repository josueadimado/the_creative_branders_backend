"""
Root URL map for the project.

/admin/  — Django admin (triage inquiries, waitlist, academy interest)
/api/    — public create-only form endpoints
"""
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "The Creative Branders"
admin.site.site_title = "TCB Admin"
admin.site.index_title = "Inquiries & signups"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
]
