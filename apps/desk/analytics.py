"""
Build the Desk Analytics payload from the studio event log and form rows.

GA4 traffic stays empty until a measurement connection is added.
The frontend can still show sample GA numbers while ga_connected is false.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from django.db.models import Count
from django.utils import timezone

from apps.core.analytics_events import CONTACT_EVENT_NAMES, EVENT_LABELS
from apps.core.models import InquiryMessage, StudioEvent

from .ga4 import fetch_ga_traffic


def _range_start(range_key: str) -> datetime:
    now = timezone.now()
    if range_key == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if range_key == "30d":
        return now - timedelta(days=30)
    # Default: last 7 days including today.
    return now - timedelta(days=6)


def _prop(event: StudioEvent, key: str) -> str:
    value = (event.props or {}).get(key)
    return str(value).strip() if value is not None else ""


def _activity_detail(event: StudioEvent) -> str:
    props = event.props or {}
    parts: list[str] = []
    for key in ("button", "location", "case_study", "filter", "which", "service", "budget_band", "currency"):
        value = props.get(key)
        if value:
            parts.append(str(value))
    campaign = _prop(event, "utm_campaign")
    source = _prop(event, "utm_source")
    if campaign or source:
        parts.append(f"via {source or 'campaign'}/{campaign or '—'}")
    if event.page_path and event.name not in {"case_study_view"}:
        parts.append(event.page_path)
    elif event.name == "case_study_view" and not parts:
        parts.append(_prop(event, "case_study") or event.page_path)
    return " · ".join(parts) if parts else (event.page_path or "—")


def _campaign_tuple(source: str, medium: str, campaign: str) -> tuple[str, str, str]:
    return (
        (source or "").strip() or "(direct)",
        (medium or "").strip() or "(none)",
        (campaign or "").strip() or "(none)",
    )


def build_analytics(range_key: str = "7d") -> dict[str, Any]:
    start = _range_start(range_key)
    events = list(StudioEvent.objects.filter(created_at__gte=start).order_by("-created_at")[:2000])
    briefs = list(
        InquiryMessage.objects.filter(created_at__gte=start).order_by("-created_at")[:200]
    )

    by_name = Counter(event.name for event in events)
    contact_total = sum(by_name[name] for name in CONTACT_EVENT_NAMES)
    whatsapp = by_name["whatsapp_click"]
    start_project = by_name["start_project_click"]
    email = by_name["email_click"]
    phone = by_name["phone_click"]
    audit = by_name["audit_cta_click"]
    other_contact = max(0, contact_total - whatsapp - start_project - email - phone)
    case_opens = by_name["case_study_view"]
    brief_count = len(briefs)
    unread = InquiryMessage.objects.filter(reviewed=False).count()

    case_counter: Counter[str] = Counter()
    for event in events:
        if event.name != "case_study_view":
            continue
        slug = _prop(event, "case_study")
        if not slug and event.page_path.startswith("/work/"):
            slug = event.page_path.removeprefix("/work/").strip("/")
        if slug:
            case_counter[slug] += 1

    briefs_by_landing: Counter[str] = Counter()
    briefs_by_campaign: dict[tuple[str, str, str], int] = defaultdict(int)
    for brief in briefs:
        landing = (brief.landing_page or "").strip() or "/"
        briefs_by_landing[landing] += 1
        key = _campaign_tuple(brief.utm_source or "", brief.utm_medium or "", brief.utm_campaign or "")
        if brief.utm_source or brief.utm_campaign:
            briefs_by_campaign[key] += 1

    # Contact CTAs tagged with the same visit UTMs (even when no brief was sent).
    contacts_by_campaign: dict[tuple[str, str, str], int] = defaultdict(int)
    for event in events:
        if event.name not in CONTACT_EVENT_NAMES:
            continue
        source = _prop(event, "utm_source")
        campaign = _prop(event, "utm_campaign")
        if not source and not campaign:
            continue
        key = _campaign_tuple(source, _prop(event, "utm_medium"), campaign)
        contacts_by_campaign[key] += 1

    # Daily contact actions for the studio chart.
    day_counts: Counter[str] = Counter()
    for event in events:
        if event.name in CONTACT_EVENT_NAMES:
            day_counts[timezone.localtime(event.created_at).strftime("%Y-%m-%d")] += 1
    days = sorted(day_counts.keys())
    def _day_label(day: str, with_month: bool) -> str:
        parsed = datetime.strptime(day, "%Y-%m-%d")
        text = parsed.strftime("%d %b" if with_month else "%d")
        return text.lstrip("0")

    contact_daily = [
        {"label": _day_label(day, i == 0), "value": day_counts[day]}
        for i, day in enumerate(days[-7:])
    ]

    activity = []
    for event in events[:40]:
        local = timezone.localtime(event.created_at)
        day_text = local.strftime("%A · %d %b").replace(" 0", " ")
        activity.append(
            {
                "day": day_text,
                "time": local.strftime("%H:%M"),
                "action": EVENT_LABELS.get(event.name, event.name),
                "name": event.name,
                "detail": _activity_detail(event),
                "created_at": event.created_at.isoformat(),
            }
        )
    # Briefs are already in Inbox; include them in the feed even if the click event was missed.
    for brief in briefs[:20]:
        local = timezone.localtime(brief.created_at)
        needs = ", ".join(str(item) for item in (brief.needs or [])[:2]) or "Project brief"
        activity.append(
            {
                "day": local.strftime("%A · %d %b").replace(" 0", " "),
                "time": local.strftime("%H:%M"),
                "action": "Brief submitted",
                "name": "brief_submit",
                "detail": f"{needs} · {(brief.budget_currency or '').strip()} · {(brief.utm_campaign or brief.landing_page or '/').strip()}".strip(" ·"),
                "created_at": brief.created_at.isoformat(),
            }
        )
    activity.sort(key=lambda row: row["created_at"], reverse=True)
    activity = activity[:40]

    work_opens = [
        {"slug": slug, "opens": count, "briefs": briefs_by_landing.get(f"/work/{slug}", 0), "gaViews": 0}
        for slug, count in case_counter.most_common(8)
    ]

    page_rows = []
    for path, count in briefs_by_landing.most_common(12):
        opens = 0
        studio_label = "landing briefs"
        if path.startswith("/work/") and path.count("/") >= 2:
            slug = path.removeprefix("/work/").split("/")[0]
            opens = case_counter.get(slug, 0)
            studio_label = "case study opens"
        page_rows.append(
            {
                "path": path,
                "views": 0,
                "studioCount": opens or count,
                "studioLabel": studio_label,
                "briefs": count,
                "kind": "case" if path.startswith("/work/") and path != "/work" else "marketing",
            }
        )

    campaign_keys = set(briefs_by_campaign) | set(contacts_by_campaign)
    campaigns = [
        {
            "source": source,
            "medium": medium,
            "campaign": campaign,
            "sessions": 0,
            "contacts": contacts_by_campaign.get((source, medium, campaign), 0),
            "briefs": briefs_by_campaign.get((source, medium, campaign), 0),
        }
        for source, medium, campaign in campaign_keys
    ]
    campaigns.sort(
        key=lambda row: (row["briefs"], row["contacts"], row["sessions"]),
        reverse=True,
    )
    campaigns = campaigns[:12]

    top_cta = "WhatsApp" if whatsapp >= start_project else "Start a project"
    top_cta_count = max(whatsapp, start_project, email, phone, audit)

    ga = fetch_ga_traffic(range_key)
    if ga.connected:
        # Attach brief counts onto GA page and channel rows where paths match.
        for row in ga.top_pages:
            row["briefs"] = briefs_by_landing.get(row["path"], 0)
        # Prefer GA campaign sessions, then overlay studio contacts + briefs.
        studio_lookup = {
            (item["source"].lower(), item["campaign"].lower()): item for item in campaigns
        }
        merged_campaigns = []
        seen: set[tuple[str, str]] = set()
        for row in ga.campaign_sessions:
            key = (row["source"].lower(), row["campaign"].lower())
            seen.add(key)
            match = studio_lookup.get(key, {})
            merged_campaigns.append(
                {
                    **row,
                    "medium": row.get("medium") or match.get("medium") or "(none)",
                    "contacts": match.get("contacts", 0),
                    "briefs": match.get("briefs", 0),
                }
            )
        for item in campaigns:
            key = (item["source"].lower(), item["campaign"].lower())
            if key in seen:
                continue
            merged_campaigns.append(item)
        if not merged_campaigns:
            merged_campaigns = campaigns
        merged_campaigns.sort(
            key=lambda row: (row.get("briefs", 0), row.get("contacts", 0), row.get("sessions", 0)),
            reverse=True,
        )
        campaigns = merged_campaigns[:12]
        # Fill work_opens gaViews from top pages when the path matches.
        views_by_path = {row["path"]: row["views"] for row in ga.top_pages}
        for row in work_opens:
            row["gaViews"] = views_by_path.get(f"/work/{row['slug']}", 0)
        # Enrich page_rows with GA views when we only had brief landings.
        views_for_rows = {row["path"]: row["views"] for row in ga.top_pages}
        for row in page_rows:
            if not row["views"]:
                row["views"] = views_for_rows.get(row["path"], 0)
        if not page_rows and ga.top_pages:
            for row in ga.top_pages:
                path = row["path"]
                page_rows.append(
                    {
                        "path": path,
                        "views": row["views"],
                        "studioCount": case_counter.get(path.removeprefix("/work/").split("/")[0], 0)
                        if path.startswith("/work/")
                        else 0,
                        "studioLabel": "case study opens" if path.startswith("/work/") else "studio actions",
                        "briefs": row.get("briefs", 0),
                        "kind": "case" if path.startswith("/work/") and path != "/work" else "marketing",
                    }
                )

    return {
        "range": range_key,
        "ga_connected": ga.connected,
        "sample_traffic": not ga.connected,
        "ga_error": ga.error if not ga.connected else "",
        "updated_at": timezone.now().isoformat(),
        "studio": {
            "contact_actions": contact_total,
            "contact_breakdown": {
                "whatsapp": whatsapp,
                "start_project": start_project,
                "email": email,
                "call": phone,
                "audit": audit,
                "other": other_contact,
            },
            "briefs": brief_count,
            "unread_briefs": unread,
            "case_opens": case_opens,
            "contact_or_brief": contact_total + brief_count,
            "contact_daily": contact_daily,
            "top_cta": f"{top_cta} · {top_cta_count}" if top_cta_count else "No contact actions yet",
            "work_opens": work_opens,
            "page_rows": page_rows,
            "campaigns": campaigns,
            "activity": activity,
            "funnel_steps_studio": [
                {
                    "title": "Clicked a contact CTA",
                    "source": "studio",
                    "count": contact_total,
                    "detail": "WhatsApp + Start a project + email + call",
                },
                {
                    "title": "Opened contact or sent brief",
                    "source": "studio",
                    "count": contact_total + brief_count,
                    "detail": "Contact CTAs + submitted briefs (combined studio signal)",
                },
            ],
        },
        "ga": {
            "visitors": ga.visitors if ga.connected else 0,
            "sessions": ga.sessions if ga.connected else 0,
            "page_views": ga.page_views if ga.connected else 0,
            "visitor_daily": ga.visitor_daily if ga.connected else [],
            "top_pages": ga.top_pages if ga.connected else [],
            "channels": ga.channels if ga.connected else [],
            "work_service_sessions": ga.work_service_sessions if ga.connected else 0,
            "campaign_session_total": sum(row["sessions"] for row in ga.campaign_sessions)
            if ga.connected
            else 0,
        },
    }
