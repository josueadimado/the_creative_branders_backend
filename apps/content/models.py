"""
The words and pictures the public website shows.

Staff edit these in Django admin. The website reads the published rows.
Form messages (inquiries, waitlist, newsletter, academy) stay in the intake app.
"""
from django.db import models

from apps.core.site_settings import BRAND_NAME, EMAIL


FAMILY_CHOICES = [
    ("brand-websites", "Brand and websites"),
    ("web-applications", "Web applications"),
    ("mobile-apps", "Mobile apps"),
    ("automation-reporting", "Automation and reporting"),
]

RELATIONSHIP_CHOICES = [
    ("client", "Client project"),
    ("venture", "Studio venture"),
]

DEVICE_CHOICES = [
    ("browser", "Browser window"),
    ("phone", "Phone"),
]


class SiteSettings(models.Model):
    """One row for the studio name, the search description, and the social links."""

    name = models.CharField(max_length=120, default=BRAND_NAME)
    tagline = models.CharField(max_length=160, default="Designed for intelligent growth.")
    description = models.TextField(
        help_text="The sentence search engines and the homepage use to describe the studio.",
    )
    email = models.EmailField(default=EMAIL)
    linkedin_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    # The X account is retired. The column stays so older databases do not lose a field.
    x_url = models.URLField(blank=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def save(self, *args, **kwargs):
        # Only one settings row. Saving always updates that same row.
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return "Site settings"


class Page(models.Model):
    """
    The editable words on one public page.

    The layout stays in the website. These fields are the sentences on that layout.
    Leave a field blank to keep the sentence that already ships with the site.
    """

    slug = models.SlugField(unique=True)
    seo_title = models.CharField(max_length=160, blank=True, verbose_name="Browser title")
    seo_description = models.TextField(blank=True, verbose_name="Search description")
    kicker = models.CharField(
        max_length=120,
        blank=True,
        help_text="The small line above the main title.",
    )
    headline = models.CharField(max_length=240, blank=True, verbose_name="Main title")
    lede = models.TextField(blank=True, verbose_name="Introduction")
    section_title = models.CharField(max_length=200, blank=True)
    paragraph_1 = models.TextField(blank=True)
    paragraph_2 = models.TextField(blank=True)
    paragraph_3 = models.TextField(blank=True)
    stat_1_value = models.CharField(max_length=20, blank=True)
    stat_1_label = models.CharField(max_length=80, blank=True)
    stat_2_value = models.CharField(max_length=20, blank=True)
    stat_2_label = models.CharField(max_length=80, blank=True)
    stat_3_value = models.CharField(max_length=20, blank=True)
    stat_3_label = models.CharField(max_length=80, blank=True)
    stat_4_value = models.CharField(max_length=20, blank=True)
    stat_4_label = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["slug"]
        verbose_name = "Page"
        verbose_name_plural = "Pages"

    def __str__(self) -> str:
        return self.slug


class Project(models.Model):
    """One case study on the work page."""

    slug = models.SlugField(unique=True, help_text="Used in the address, for example relief-chiropractic.")
    public_name = models.CharField(max_length=160, verbose_name="Public name")
    company = models.CharField(max_length=160, blank=True)
    anonymous_name = models.CharField(
        max_length=160,
        help_text="Shown instead of the public name until the name is approved.",
    )
    name_approved = models.BooleanField(default=False, verbose_name="Show the real name and logo")
    logo_path = models.CharField(
        max_length=300,
        blank=True,
        help_text="A path already on the site, such as /images/logos/come.png.",
    )
    logo_upload = models.ImageField(upload_to="logos/", blank=True, verbose_name="Or upload a logo")
    live_url = models.URLField(blank=True, verbose_name="Live site")
    link_approved = models.BooleanField(default=False, verbose_name="Show the Visit site button")
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, default="client")
    family = models.CharField(max_length=40, choices=FAMILY_CHOICES, verbose_name="Main service")
    secondary_families = models.JSONField(default=list, blank=True)
    sector = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, blank=True)
    featured = models.BooleanField(default=False, help_text="Featured projects can appear on the homepage.")
    published = models.BooleanField(default=False, help_text="Only published projects appear on the website.")
    position = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first.")
    summary = models.TextField()
    challenge = models.TextField(verbose_name="The problem")
    approach = models.TextField(verbose_name="The solution")
    built = models.JSONField(default=list, blank=True, help_text="Delivery paragraphs.")
    stack = models.JSONField(default=list, blank=True)
    results = models.JSONField(default=list, blank=True, help_text="Short benefits shown on the project page.")
    device = models.CharField(max_length=20, choices=DEVICE_CHOICES, default="browser")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "public_name"]
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self) -> str:
        return self.public_name


class ProjectShot(models.Model):
    """One screenshot on a project card and on the project page."""

    project = models.ForeignKey(Project, related_name="shots", on_delete=models.CASCADE)
    existing_path = models.CharField(
        max_length=300,
        blank=True,
        help_text="A picture already on the site, such as /images/work/come/homepage.jpg.",
    )
    upload = models.ImageField(upload_to="projects/", blank=True, verbose_name="Or upload a picture")
    alt = models.CharField(max_length=180, blank=True, verbose_name="Short description")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Screenshot"
        verbose_name_plural = "Screenshots"

    def __str__(self) -> str:
        return self.alt or self.existing_path or "Screenshot"


class Note(models.Model):
    """A studio note. The Insights menu stays closed until you publish notes and open that menu."""

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    body = models.TextField(help_text="Plain paragraphs. Leave a blank line between them.")
    family = models.CharField(max_length=40, choices=FAMILY_CHOICES, default="brand-websites")
    published = models.BooleanField(default=False)
    published_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-published_on", "title"]
        verbose_name = "Note"
        verbose_name_plural = "Notes"

    def __str__(self) -> str:
        return self.title
