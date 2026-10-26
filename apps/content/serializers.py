"""Turn database rows into the shape the website already understands."""
from rest_framework import serializers

from .models import Note, Page, Project, SiteSettings


def _shot_url(shot, request) -> str:
    if shot.upload:
        url = shot.upload.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url
    return shot.existing_path


def _logo_url(project, request) -> str:
    if project.logo_upload:
        url = project.logo_upload.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url
    return project.logo_path


class ProjectSerializer(serializers.ModelSerializer):
    """Matches the project object the work page already uses."""

    publicName = serializers.CharField(source="public_name")
    anonymousName = serializers.CharField(source="anonymous_name")
    nameApproved = serializers.BooleanField(source="name_approved")
    linkApproved = serializers.BooleanField(source="link_approved")
    liveUrl = serializers.CharField(source="live_url")
    secondaryFamilies = serializers.JSONField(source="secondary_families")
    logo = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    results = serializers.SerializerMethodField()
    updated = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "slug",
            "publicName",
            "company",
            "anonymousName",
            "nameApproved",
            "logo",
            "liveUrl",
            "linkApproved",
            "relationship",
            "family",
            "secondaryFamilies",
            "sector",
            "country",
            "featured",
            "published",
            "summary",
            "challenge",
            "approach",
            "built",
            "stack",
            "results",
            "images",
            "device",
            "updated",
        ]

    def get_logo(self, project) -> str:
        return _logo_url(project, self.context.get("request"))

    def get_results(self, project) -> list:
        return project.results or []

    def get_images(self, project) -> list[str]:
        request = self.context.get("request")
        return [_shot_url(shot, request) for shot in project.shots.all()]

    def get_updated(self, project) -> str:
        # The day the project was last saved. The sitemap uses this as lastmod.
        return project.updated_at.date().isoformat()


class PageSerializer(serializers.ModelSerializer):
    seoTitle = serializers.CharField(source="seo_title")
    seoDescription = serializers.CharField(source="seo_description")
    sectionTitle = serializers.CharField(source="section_title")
    paragraph1 = serializers.CharField(source="paragraph_1")
    paragraph2 = serializers.CharField(source="paragraph_2")
    paragraph3 = serializers.CharField(source="paragraph_3")
    stats = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            "slug",
            "seoTitle",
            "seoDescription",
            "kicker",
            "headline",
            "lede",
            "sectionTitle",
            "paragraph1",
            "paragraph2",
            "paragraph3",
            "stats",
        ]

    def get_stats(self, page) -> list[dict]:
        pairs = [
            (page.stat_1_value, page.stat_1_label),
            (page.stat_2_value, page.stat_2_label),
            (page.stat_3_value, page.stat_3_label),
            (page.stat_4_value, page.stat_4_label),
        ]
        return [{"value": value, "label": label} for value, label in pairs if value and label]


class NoteSerializer(serializers.ModelSerializer):
    publishedOn = serializers.DateField(source="published_on")

    class Meta:
        model = Note
        fields = ["slug", "title", "description", "body", "family", "publishedOn"]


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [
            "name",
            "tagline",
            "description",
            "email",
            "linkedin_url",
            "instagram_url",
            "facebook_url",
        ]
