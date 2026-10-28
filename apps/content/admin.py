"""
The content desk.

Sign in at /admin/ to change page text, projects, screenshots, and notes.
Inquiries and signups stay in the Studio intake section.
"""
from django import forms
from django.contrib import admin

from .models import FAMILY_CHOICES, Note, Page, Project, ProjectShot, SiteSettings


class ProjectAdminForm(forms.ModelForm):
    """Turns lists into plain text boxes, so nobody has to edit raw JSON."""

    also_listed_under = forms.MultipleChoiceField(
        required=False,
        choices=FAMILY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Also listed under",
        help_text="Extra services. The project still keeps the main service above.",
    )
    tools = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 6}),
        label="Tools",
        help_text="One tool per line. These become the pills under the screenshots.",
    )
    benefits = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
        label="The benefit",
        help_text="One benefit per block. The first line is the short line. The next line explains it. Leave a blank line between benefits.",
    )
    delivery = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
        label="The delivery",
        help_text="The closing paragraph. A blank line starts another paragraph.",
    )

    class Meta:
        model = Project
        exclude = ("secondary_families", "stack", "built", "results")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project = self.instance
        if project.pk:
            self.fields["also_listed_under"].initial = project.secondary_families or []
            self.fields["tools"].initial = "\n".join(project.stack or [])
            self.fields["delivery"].initial = "\n\n".join(project.built or [])
            self.fields["benefits"].initial = "\n\n".join(
                f"{item.get('value', '')}\n{item.get('label', '')}".strip()
                for item in (project.results or [])
                if isinstance(item, dict)
            )

    def save(self, commit=True):
        project = super().save(commit=False)
        project.secondary_families = self.cleaned_data["also_listed_under"]
        project.stack = [line.strip() for line in self.cleaned_data["tools"].splitlines() if line.strip()]
        chunks = [chunk.strip() for chunk in self.cleaned_data["delivery"].split("\n\n")]
        project.built = [chunk for chunk in chunks if chunk]
        benefits = []
        for chunk in self.cleaned_data["benefits"].split("\n\n"):
            lines = [line.strip() for line in chunk.splitlines() if line.strip()]
            if not lines:
                continue
            benefits.append({"value": lines[0], "label": " ".join(lines[1:])})
        project.results = benefits
        if commit:
            project.save()
        return project


class ProjectShotInline(admin.TabularInline):
    model = ProjectShot
    extra = 1
    fields = ("sort_order", "existing_path", "upload", "alt")


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Studio", {"fields": ("name", "tagline", "description", "email")}),
        ("Social links", {"fields": ("linkedin_url", "instagram_url", "facebook_url", "x_url")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("slug", "headline", "seo_title")
    search_fields = ("slug", "headline", "seo_title")
    fieldsets = (
        ("Which page", {"fields": ("slug",)}),
        ("Search", {"fields": ("seo_title", "seo_description")}),
        ("Opening", {"fields": ("kicker", "headline", "lede")}),
        (
            "Story",
            {
                "fields": ("section_title", "paragraph_1", "paragraph_2", "paragraph_3"),
                "description": "Used on the About page. The first paragraph is the opening story.",
            },
        ),
        (
            "Numbers",
            {
                "fields": (
                    ("stat_1_value", "stat_1_label"),
                    ("stat_2_value", "stat_2_label"),
                    ("stat_3_value", "stat_3_label"),
                    ("stat_4_value", "stat_4_label"),
                ),
                "description": "Used on the About page. Leave the project and country numbers blank. The website counts those from the published projects.",
            },
        ),
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    form = ProjectAdminForm
    inlines = [ProjectShotInline]
    list_display = ("public_name", "family", "country", "featured", "published", "position")
    list_filter = ("published", "featured", "family", "country")
    list_editable = ("published", "featured", "position")
    search_fields = ("public_name", "company", "slug", "summary")
    prepopulated_fields = {"slug": ("public_name",)}
    fieldsets = (
        ("Name", {"fields": ("public_name", "slug", "company", "anonymous_name", "name_approved")}),
        ("Where it appears", {"fields": ("published", "featured", "position", "family", "also_listed_under", "relationship")}),
        ("Labels", {"fields": ("sector", "country", "device")}),
        ("Visit site", {"fields": ("live_url", "link_approved", "logo_path", "logo_upload")}),
        ("The story", {"fields": ("summary", "challenge", "approach", "delivery", "benefits", "tools")}),
    )


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "family", "published", "published_on")
    list_filter = ("published", "family")
    search_fields = ("title", "description", "body")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (None, {"fields": ("title", "slug", "description", "family")}),
        ("Publishing", {"fields": ("published", "published_on")}),
        ("Note", {"fields": ("body",)}),
    )
