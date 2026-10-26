"""
Turn studio-desk forms into the same database rows the public site reads.

The public site has its own read-only serializers. These ones are for staff,
so they include drafts, ids, and the fields a person edits.
"""
from django.utils.text import slugify
from rest_framework import serializers

from apps.content.models import (
    FAMILY_CHOICES,
    DEVICE_CHOICES,
    RELATIONSHIP_CHOICES,
    Note,
    Page,
    Project,
    ProjectShot,
    SiteSettings,
)
from apps.core.models import AcademyInterest, InquiryMessage, NewsletterSignup, WaitlistSignup

FAMILY_SLUGS = {slug for slug, _label in FAMILY_CHOICES}
DEVICE_SLUGS = {slug for slug, _label in DEVICE_CHOICES}
RELATIONSHIP_SLUGS = {slug for slug, _label in RELATIONSHIP_CHOICES}


def _picture_url(upload, existing_path: str, request) -> str:
    """A full address for an uploaded file, or the path already on the site."""
    if upload:
        url = upload.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url
    return existing_path or ""


def _string_list(value, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError(f"{label} should be a list of lines.")
    return [str(item).strip() for item in value if str(item).strip()]


class PageDeskSerializer(serializers.ModelSerializer):
    """One public page. The address (slug) stays fixed, because the site looks it up by name."""

    class Meta:
        model = Page
        fields = [
            "slug",
            "seo_title",
            "seo_description",
            "kicker",
            "headline",
            "lede",
            "section_title",
            "paragraph_1",
            "paragraph_2",
            "paragraph_3",
            "stat_1_value",
            "stat_1_label",
            "stat_2_value",
            "stat_2_label",
            "stat_3_value",
            "stat_3_label",
            "stat_4_value",
            "stat_4_label",
        ]
        read_only_fields = ["slug"]
        extra_kwargs = {name: {"allow_blank": True, "required": False} for name in fields if name != "slug"}


class ShotDeskSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectShot
        fields = ["id", "existing_path", "alt", "sort_order", "url"]
        read_only_fields = ["id", "url"]
        extra_kwargs = {
            "existing_path": {"allow_blank": True, "required": False},
            "alt": {"allow_blank": True, "required": False},
        }

    def get_url(self, shot) -> str:
        return _picture_url(shot.upload, shot.existing_path, self.context.get("request"))


class ProjectDeskSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    shots = ShotDeskSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "slug",
            "public_name",
            "company",
            "anonymous_name",
            "name_approved",
            "logo_path",
            "logo_url",
            "live_url",
            "link_approved",
            "relationship",
            "family",
            "secondary_families",
            "sector",
            "country",
            "featured",
            "published",
            "position",
            "summary",
            "challenge",
            "approach",
            "built",
            "stack",
            "results",
            "device",
            "shots",
        ]
        read_only_fields = ["id", "logo_url", "shots"]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "public_name": {"required": False, "allow_blank": True},
            "company": {"allow_blank": True, "required": False},
            "anonymous_name": {"allow_blank": True, "required": False},
            "logo_path": {"allow_blank": True, "required": False},
            "live_url": {"allow_blank": True, "required": False},
            "sector": {"allow_blank": True, "required": False},
            "country": {"allow_blank": True, "required": False},
            "summary": {"allow_blank": True, "required": False},
            "challenge": {"allow_blank": True, "required": False},
            "approach": {"allow_blank": True, "required": False},
        }

    def get_logo_url(self, project) -> str:
        return _picture_url(project.logo_upload, project.logo_path, self.context.get("request"))

    def validate_family(self, value: str) -> str:
        if value not in FAMILY_SLUGS:
            raise serializers.ValidationError("Choose a service from the list.")
        return value

    def validate_relationship(self, value: str) -> str:
        if value not in RELATIONSHIP_SLUGS:
            raise serializers.ValidationError("Choose client project or studio venture.")
        return value

    def validate_device(self, value: str) -> str:
        if value not in DEVICE_SLUGS:
            raise serializers.ValidationError("Choose a browser window or a phone.")
        return value

    def validate_secondary_families(self, value):
        if value is None:
            return []
        if not isinstance(value, list) or any(item not in FAMILY_SLUGS for item in value):
            raise serializers.ValidationError("Choose extra services from the list.")
        return value

    def validate_stack(self, value):
        return _string_list(value, "Tools")

    def validate_built(self, value):
        return _string_list(value, "Delivery")

    def validate_results(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Benefits should be a list.")
        cleaned = []
        for item in value:
            if not isinstance(item, dict):
                continue
            short = str(item.get("value", "")).strip()
            detail = str(item.get("label", "")).strip()
            if short or detail:
                cleaned.append({"value": short, "label": detail})
        return cleaned

    def _fill_slug(self, validated: dict, current: str = "") -> None:
        """Build a web address from the project name when the person left it blank."""
        slug = (validated.get("slug") or current or "").strip()
        if slug:
            validated["slug"] = slug
            return
        base = slugify(validated.get("public_name") or "project") or "project"
        candidate = base
        number = 2
        taken = Project.objects.all()
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        while taken.filter(slug=candidate).exists():
            candidate = f"{base}-{number}"
            number += 1
        validated["slug"] = candidate

    def create(self, validated_data):
        if not validated_data.get("public_name", "").strip():
            validated_data["public_name"] = "Untitled project"
        if not validated_data.get("anonymous_name", "").strip():
            validated_data["anonymous_name"] = validated_data["public_name"]
        self._fill_slug(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "public_name" in validated_data and not validated_data.get("anonymous_name") and not instance.anonymous_name:
            validated_data["anonymous_name"] = validated_data["public_name"]
        self._fill_slug(validated_data, instance.slug)
        return super().update(instance, validated_data)


class NoteDeskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ["id", "slug", "title", "description", "body", "family", "published", "published_on"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "title": {"required": False, "allow_blank": True},
            "description": {"allow_blank": True, "required": False},
            "body": {"allow_blank": True, "required": False},
            "published_on": {"required": False, "allow_null": True},
        }

    def validate_family(self, value: str) -> str:
        if value not in FAMILY_SLUGS:
            raise serializers.ValidationError("Choose a service from the list.")
        return value

    def _fill_slug(self, validated: dict, current: str = "") -> None:
        slug = (validated.get("slug") or current or "").strip()
        if slug:
            validated["slug"] = slug
            return
        base = slugify(validated.get("title") or "note") or "note"
        candidate = base
        number = 2
        taken = Note.objects.all()
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        while taken.filter(slug=candidate).exists():
            candidate = f"{base}-{number}"
            number += 1
        validated["slug"] = candidate

    def create(self, validated_data):
        if not validated_data.get("title", "").strip():
            validated_data["title"] = "Untitled note"
        self._fill_slug(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._fill_slug(validated_data, instance.slug)
        return super().update(instance, validated_data)


class SettingsDeskSerializer(serializers.ModelSerializer):
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
        extra_kwargs = {
            "description": {"allow_blank": True, "required": False},
            "linkedin_url": {"allow_blank": True, "required": False},
            "instagram_url": {"allow_blank": True, "required": False},
            "facebook_url": {"allow_blank": True, "required": False},
        }


class InquiryDeskSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquiryMessage
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "company",
            "country",
            "needs",
            "timeline",
            "budget_range",
            "budget_currency",
            "brief_link",
            "message",
            "reviewed",
            "consent_at",
            "created_at",
        ]


class WaitlistDeskSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistSignup
        fields = ["id", "email", "name", "consent_at", "created_at"]


class NewsletterDeskSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSignup
        fields = ["id", "email", "consent_at", "created_at"]


class AcademyDeskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademyInterest
        fields = ["id", "name", "email", "message", "consent_at", "created_at"]
