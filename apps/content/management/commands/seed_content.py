"""
Fill the content desk with the pages and projects already on the site.

Run once:

    python manage.py seed_content

It leaves existing rows alone, so later edits in /admin/ are safe.
Pass --refresh only when you want those edits replaced by this starter copy.
"""
import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.content.models import Note, Page, Project, ProjectShot, SiteSettings
from apps.core.site_settings import BRAND_NAME, EMAIL, SOCIAL

SEED_DIR = Path(__file__).resolve().parents[2] / "seed"
REPO_ROOT = Path(__file__).resolve().parents[5]
INSIGHTS_DIR = REPO_ROOT / "frontend" / "src" / "content" / "insights"

FEATURED_ORDER = [
    "relief-chiropractic",
    "push-it",
    "come-clarity",
    "up2date-connect",
    "secure-counseling",
]


def _lines(value: str) -> tuple[str, str]:
    """Split a markdown front-matter line into a name and a value."""
    name, _, raw = value.partition(":")
    return name.strip(), raw.strip()


def _read_note(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        _, front, body = raw.split("---", 2)
        for line in front.strip().splitlines():
            key, value = _lines(line)
            if key:
                meta[key] = value
    return {
        "slug": path.stem,
        "title": meta.get("title", path.stem),
        "description": meta.get("description", ""),
        "family": meta.get("family", "brand-websites"),
        "published_on": meta.get("date") or None,
        "body": body.strip(),
    }


PAGES = [
    {
        "slug": "home",
        "seo_title": "Big ideas. Real products.",
        "seo_description": "We're the strategy and technology partner behind growing businesses. We take the pressure off your day, so you can focus on your customers and your next move.",
        "kicker": "Your business, running smarter",
        "headline": "Big ideas. Real products.",
        "lede": "We're the strategy and technology partner behind growing businesses. We take the pressure off your day, so you can focus on your customers and your next move.",
    },
    {
        "slug": "about",
        "seo_title": "About the studio",
        "seo_description": f"{BRAND_NAME} is a design and development studio for growing businesses. We design and build websites, apps and the systems behind them.",
        "kicker": "About the studio",
        "headline": "We're the strategy and technology partner behind your business.",
        "lede": "From the first idea to the systems you rely on every day, we stay with you as your business grows.",
        "section_title": "Why we exist",
        "paragraph_1": "A lot of growing businesses run on the same setup. A website someone built a few years ago. Bookings in a spreadsheet or a notebook. Customers in WhatsApp. Payments in a separate app. It works until the business grows, and then the owner spends their evenings holding it all together.",
        "paragraph_2": f"Fixing that properly used to mean hiring an agency built for much larger companies. We started {BRAND_NAME} so growing businesses could get the same standard of work at a size and price that fits them: the website, the apps and the systems behind them, planned together.",
        "paragraph_3": "One person leads your project from the first call to launch. If it needs a mobile developer, a payments specialist or a data analyst, we bring in people we've worked with before. Everything we do shows up in our client portal, so you always know what's been done and what's next.",
        "stat_1_value": "6+",
        "stat_1_label": "Years in technology",
        "stat_2_value": "10+",
        "stat_2_label": "Delivered projects",
        "stat_3_value": "15",
        "stat_3_label": "Specialists on our team",
        "stat_4_value": "95%",
        "stat_4_label": "Client retention",
    },
    {
        "slug": "work",
        "seo_title": "Our work",
        "seo_description": "Websites, web apps and platforms we've built for clinics, schools, nonprofits and startups in the US, Ghana, Nigeria and Togo.",
        "kicker": "Work",
        "headline": "Our work",
        "lede": "A selection of what we've designed and built. Each project page explains what the client needed, what we made and what it runs on.",
    },
    {
        "slug": "contact",
        "seo_title": "Start a project",
        "seo_description": "Tell us about your project. We'll reply within one business day.",
        "headline": "Start a project",
        "lede": "Tell us about your project. We'll reply within one business day.",
    },
]


class Command(BaseCommand):
    help = "Load the current website copy into the content desk."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Replace pages, projects, and notes with the starter copy.",
        )

    def handle(self, *args, **options):
        refresh = options["refresh"]
        if not refresh and (Project.objects.exists() or Page.objects.exists()):
            self.stdout.write("Content is already in the desk. Nothing was changed.")
            self.stdout.write("Use --refresh only if you want the starter copy to replace those edits.")
            return

        if refresh:
            ProjectShot.objects.all().delete()
            Project.objects.all().delete()
            Page.objects.all().delete()
            Note.objects.all().delete()

        self._settings()
        self._pages()
        self._projects()
        self._notes()
        self.stdout.write(self.style.SUCCESS("The content desk is ready at /admin/."))

    def _settings(self):
        SiteSettings.objects.update_or_create(
            pk=1,
            defaults={
                "name": BRAND_NAME,
                "tagline": "Designed for intelligent growth.",
                "description": PAGES[0]["seo_description"],
                "email": EMAIL,
                "linkedin_url": SOCIAL["linkedin"],
                "instagram_url": SOCIAL["instagram"],
                "facebook_url": SOCIAL["facebook"],
                "x_url": "",
            },
        )

    def _pages(self):
        for row in PAGES:
            Page.objects.update_or_create(slug=row["slug"], defaults=row)

    def _projects(self):
        path = SEED_DIR / "projects.json"
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"Missing {path.name}. Pages were loaded. Projects were not."))
            return
        studies = json.loads(path.read_text(encoding="utf-8"))
        for index, study in enumerate(studies):
            if not study.get("published"):
                continue
            slug = study["slug"]
            featured_at = FEATURED_ORDER.index(slug) if slug in FEATURED_ORDER else None
            project, _ = Project.objects.update_or_create(
                slug=slug,
                defaults={
                    "public_name": study.get("publicName") or slug,
                    "company": study.get("company") or "",
                    "anonymous_name": study.get("anonymousName") or study.get("publicName") or slug,
                    "name_approved": bool(study.get("nameApproved")),
                    "logo_path": study.get("logo") or "",
                    "live_url": study.get("liveUrl") or "",
                    "link_approved": bool(study.get("linkApproved")),
                    "relationship": study.get("relationship") or "client",
                    "family": study.get("family") or "web-applications",
                    "secondary_families": study.get("secondaryFamilies") or [],
                    "sector": study.get("sector") or "",
                    "country": study.get("country") or "",
                    "featured": bool(study.get("featured")),
                    "published": True,
                    "position": featured_at if featured_at is not None else 100 + index,
                    "summary": study.get("summary") or "",
                    "challenge": study.get("challenge") or "",
                    "approach": study.get("approach") or "",
                    "built": study.get("built") or [],
                    "stack": study.get("stack") or [],
                    "results": study.get("results") or [],
                    "device": study.get("device") or "browser",
                },
            )
            project.shots.all().delete()
            for order, image in enumerate(study.get("images") or []):
                if not image:
                    continue
                ProjectShot.objects.create(project=project, existing_path=image, sort_order=order)

    def _notes(self):
        if not INSIGHTS_DIR.exists():
            return
        for path in sorted(INSIGHTS_DIR.glob("*.md")):
            note = _read_note(path)
            published_on = None
            if note["published_on"]:
                published_on = date.fromisoformat(note["published_on"])
            # Drafts until the Insights menu is a real page.
            Note.objects.update_or_create(
                slug=note["slug"],
                defaults={
                    "title": note["title"],
                    "description": note["description"],
                    "body": note["body"],
                    "family": note["family"],
                    "published": False,
                    "published_on": published_on,
                },
            )
