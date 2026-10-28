"""
Build the Desk Analytics payload from the studio event log and form rows.

GA4 traffic stays empty until a measurement connection is added.
The frontend can still show sample GA numbers while ga_connected is false.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from django.db.models import Count
from django.utils import timezone

from apps.core.analytics_events import CONTACT_EVENT_NAMES, CONVERSION_EVENT_NAMES, EVENT_LABELS
from apps.core.models import InquiryMessage, StudioEvent
from apps.core.visit_context import format_location_label, lookup_ip_location

from .ga4 import fetch_ga_traffic

# High-volume page timing — keep out of the Activity feed so CTAs stay visible.
JOURNEY_NOISE = frozenset({"page_view", "page_leave"})

# Highest-ranked outcome wins for each visit.
_OUTCOME_RANK = {
    "brief_submit": 50,
    "waitlist_signup": 40,
    "whatsapp_click": 30,
    "start_project_click": 28,
    "email_click": 26,
    "phone_click": 26,
    "audit_cta_click": 24,
    "case_study_view": 10,
    "work_filter": 5,
}


def _parse_day(value: str | None) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _range_start(range_key: str) -> datetime:
    now = timezone.now()
    if range_key == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if range_key == "30d":
        return now - timedelta(days=30)
    # Default: last 7 days including today.
    return now - timedelta(days=6)


def _page_kind(path: str) -> str:
    if path.startswith("/work/") and path != "/work":
        return "case"
    if path.startswith("/insights"):
        return "insights"
    return "marketing"


def _prop(event: StudioEvent, key: str) -> str:
    value = (event.props or {}).get(key)
    return str(value).strip() if value is not None else ""


def _activity_detail(event: StudioEvent) -> str:
    props = event.props or {}
    if event.name == "js_error":
        return str(props.get("message") or props.get("source") or event.page_path or "error")[:160]
    if event.name == "form_error":
        return f"{props.get('form') or 'form'}: {props.get('reason') or 'error'}"
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


def _outcome_for(names: set[str]) -> tuple[str, str]:
    """Return (outcome_key, friendly_label) for the strongest event in a visit."""
    best = ""
    best_rank = -1
    for name in names:
        rank = _OUTCOME_RANK.get(name, 0)
        if rank > best_rank:
            best_rank = rank
            best = name
    if not best:
        return "browsed", "Browsed"
    if best in CONVERSION_EVENT_NAMES or best == "case_study_view":
        return best, EVENT_LABELS.get(best, best)
    return best, EVENT_LABELS.get(best, best)


def _step_detail(event: StudioEvent) -> str:
    props = event.props or {}
    if event.name == "page_leave":
        sec = props.get("duration_sec")
        return f"{sec}s on page" if sec else (event.page_path or "")
    if event.name == "js_error":
        return str(props.get("message") or props.get("source") or "error")[:160]
    if event.name == "form_error":
        form = props.get("form") or "form"
        reason = props.get("reason") or "error"
        return f"{form}: {reason}"
    return _activity_detail(event)


def build_journeys(events: list[StudioEvent]) -> dict[str, Any]:
    """
    Group studio events by visit_id into visitor journeys.
    Also builds simple “what to improve” tips from exits and errors.
    """
    by_visit: dict[str, list[StudioEvent]] = defaultdict(list)
    for event in events:
        vid = (event.visit_id or "").strip()
        if not vid:
            continue
        by_visit[vid].append(event)

    journeys: list[dict[str, Any]] = []
    exit_pages: Counter[str] = Counter()
    error_messages: Counter[str] = Counter()
    form_reasons: Counter[str] = Counter()
    countries: Counter[str] = Counter()
    converted_count = 0
    bounced_count = 0
    with_errors = 0
    duration_total = 0
    pages_total = 0
    # One lookup per IP when older events have an IP but no saved country yet.
    geo_by_ip: dict[str, dict[str, str]] = {}

    def _geo_for(event: StudioEvent) -> dict[str, str]:
        if event.country or event.country_code or event.city:
            return {
                "country_code": event.country_code or "",
                "country": event.country or "",
                "city": event.city or "",
                "region": event.region or "",
            }
        ip = str(event.client_ip or "").strip()
        if not ip:
            return {"country_code": "", "country": "", "city": "", "region": ""}
        if ip not in geo_by_ip:
            geo_by_ip[ip] = lookup_ip_location(ip)
        return geo_by_ip[ip]

    for visit_id, visit_events in by_visit.items():
        ordered = sorted(visit_events, key=lambda item: item.created_at)
        names = {item.name for item in ordered}
        paths: list[str] = []
        for item in ordered:
            path = (item.page_path or "").strip()
            if path and path not in paths:
                paths.append(path)
        if not paths:
            landing = _prop(ordered[0], "landing_page")
            if landing:
                paths.append(landing)

        duration_sec = 0
        for item in ordered:
            if item.name != "page_leave":
                continue
            raw = _prop(item, "duration_sec")
            try:
                duration_sec += max(0, int(float(raw)))
            except (TypeError, ValueError):
                pass

        error_count = sum(1 for item in ordered if item.name in {"js_error", "form_error"})
        converted = bool(names & CONVERSION_EVENT_NAMES)
        outcome_key, outcome_label = _outcome_for(names)
        if converted:
            converted_count += 1
            outcome_key = outcome_key if outcome_key in CONVERSION_EVENT_NAMES else "contact"
        elif len(paths) <= 1 and "case_study_view" not in names:
            bounced_count += 1
            outcome_key, outcome_label = "bounced", "Left quickly"
        if error_count:
            with_errors += 1

        first = ordered[0]
        landing = _prop(first, "landing_page") or (paths[0] if paths else "/")
        exit_path = paths[-1] if paths else landing
        if not converted:
            exit_pages[exit_path] += 1

        for item in ordered:
            if item.name == "js_error":
                msg = _prop(item, "message") or "error"
                error_messages[msg[:80]] += 1
            elif item.name == "form_error":
                form_reasons[f"{_prop(item, 'form') or 'form'}:{_prop(item, 'reason') or 'error'}"] += 1

        geo = _geo_for(first)
        location_label = format_location_label(
            city=geo.get("city", ""),
            region=geo.get("region", ""),
            country=geo.get("country", ""),
            country_code=geo.get("country_code", ""),
        )
        country_key = geo.get("country") or geo.get("country_code") or ""
        if country_key:
            countries[country_key] += 1

        steps = []
        for item in ordered:
            local = timezone.localtime(item.created_at)
            steps.append(
                {
                    "time": local.strftime("%H:%M:%S"),
                    "name": item.name,
                    "label": EVENT_LABELS.get(item.name, item.name),
                    "path": item.page_path or "",
                    "detail": _step_detail(item),
                    "created_at": item.created_at.isoformat(),
                }
            )

        duration_total += duration_sec
        pages_total += len(paths)
        started = timezone.localtime(first.created_at)
        journeys.append(
            {
                "visit_id": visit_id,
                "started_at": first.created_at.isoformat(),
                "started_label": started.strftime("%d %b · %H:%M").lstrip("0").replace(" 0", " "),
                "device": first.device or "",
                "client_ip": str(first.client_ip or ""),
                "country_code": geo.get("country_code") or "",
                "country": geo.get("country") or "",
                "city": geo.get("city") or "",
                "region": geo.get("region") or "",
                "location_label": location_label,
                "landing_page": landing,
                "exit_page": exit_path,
                "pages": paths[:12],
                "page_count": len(paths),
                "duration_sec": duration_sec,
                "event_count": len(ordered),
                "error_count": error_count,
                "converted": converted,
                "outcome": outcome_key,
                "outcome_label": outcome_label,
                "source": _prop(first, "utm_source") or "",
                "campaign": _prop(first, "utm_campaign") or "",
                "referrer": _prop(first, "referrer") or "",
                "steps": steps,
            }
        )

    journeys.sort(key=lambda row: row["started_at"], reverse=True)
    visit_count = len(journeys)
    avg_duration = int(duration_total / visit_count) if visit_count else 0
    avg_pages = round(pages_total / visit_count, 1) if visit_count else 0.0

    tips: list[dict[str, str]] = []
    for path, count in exit_pages.most_common(3):
        if count < 2:
            continue
        tips.append(
            {
                "title": f"People leave from {path}",
                "detail": f"{count} visits ended here without a contact action. Check the CTA and next step on this page.",
                "severity": "high" if count >= 5 else "medium",
            }
        )
    for reason, count in form_reasons.most_common(2):
        tips.append(
            {
                "title": f"Form friction: {reason}",
                "detail": f"Seen {count} time(s). Visitors hit this before they could finish.",
                "severity": "high",
            }
        )
    for msg, count in error_messages.most_common(2):
        tips.append(
            {
                "title": "Page error showing up",
                "detail": f"“{msg}” · {count} time(s). Fixing this removes a silent drop-off.",
                "severity": "high",
            }
        )
    if visit_count and bounced_count / visit_count >= 0.4:
        tips.append(
            {
                "title": "Many one-page visits",
                "detail": f"{bounced_count} of {visit_count} visits left after a single page. Strengthen the first screen CTA.",
                "severity": "medium",
            }
        )
    if not tips and visit_count:
        tips.append(
            {
                "title": "Keep watching journeys",
                "detail": "No strong drop-off pattern yet. As more consented visits arrive, exits and form issues will surface here.",
                "severity": "low",
            }
        )
    elif not tips:
        tips.append(
            {
                "title": "Waiting for consented visits",
                "detail": "Journeys appear after a visitor accepts analytics cookies and moves around the site.",
                "severity": "low",
            }
        )

    return {
        "stats": {
            "visits": visit_count,
            "converted": converted_count,
            "bounced": bounced_count,
            "with_errors": with_errors,
            "avg_duration_sec": avg_duration,
            "avg_pages": avg_pages,
        },
        "tips": tips[:6],
        "top_exit_pages": [
            {"path": path, "count": count} for path, count in exit_pages.most_common(8)
        ],
        "top_countries": [
            {"country": name, "count": count} for name, count in countries.most_common(8)
        ],
        "common_errors": [
            {"message": msg, "count": count} for msg, count in error_messages.most_common(5)
        ],
        "items": journeys[:60],
    }


def build_analytics(
    range_key: str = "7d",
    *,
    start_day: str | None = None,
    end_day: str | None = None,
) -> dict[str, Any]:
    custom_start = _parse_day(start_day)
    custom_end = _parse_day(end_day)
    use_custom = range_key == "custom" and custom_start and custom_end
    if use_custom and custom_start > custom_end:
        custom_start, custom_end = custom_end, custom_start

    if use_custom and custom_start and custom_end:
        start = timezone.make_aware(datetime.combine(custom_start, time.min))
        end = timezone.make_aware(datetime.combine(custom_end, time.max))
        events = list(
            StudioEvent.objects.filter(created_at__gte=start, created_at__lte=end).order_by("-created_at")[
                :4000
            ]
        )
        briefs = list(
            InquiryMessage.objects.filter(created_at__gte=start, created_at__lte=end).order_by(
                "-created_at"
            )[:200]
        )
        ga_start, ga_end = custom_start, custom_end
    else:
        if range_key == "custom":
            range_key = "7d"
        start = _range_start(range_key)
        events = list(StudioEvent.objects.filter(created_at__gte=start).order_by("-created_at")[:4000])
        briefs = list(
            InquiryMessage.objects.filter(created_at__gte=start).order_by("-created_at")[:200]
        )
        ga_start = ga_end = None

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

    # Paths opened in the same browser session (helps “what were they looking at?”).
    paths_by_visit: dict[str, list[str]] = defaultdict(list)
    for event in events:
        if not event.visit_id or not event.page_path:
            continue
        bucket = paths_by_visit[event.visit_id]
        if event.page_path not in bucket:
            bucket.append(event.page_path)

    journeys_payload = build_journeys(events)

    activity = []
    for event in events:
        if event.name in JOURNEY_NOISE:
            continue
        local = timezone.localtime(event.created_at)
        day_text = local.strftime("%A · %d %b").replace(" 0", " ")
        source = _prop(event, "utm_source")
        campaign = _prop(event, "utm_campaign")
        referrer = _prop(event, "referrer")
        landing = _prop(event, "landing_page")
        visit_paths = paths_by_visit.get(event.visit_id or "", [])[:5]
        activity.append(
            {
                "day": day_text,
                "time": local.strftime("%H:%M"),
                "action": EVENT_LABELS.get(event.name, event.name),
                "name": event.name,
                "detail": _activity_detail(event),
                "created_at": event.created_at.isoformat(),
                "visit_id": event.visit_id or "",
                "device": event.device or "",
                "client_ip": event.client_ip or "",
                "source": source,
                "campaign": campaign,
                "referrer": referrer,
                "landing_page": landing,
                "visit_paths": visit_paths,
            }
        )
        if len(activity) >= 40:
            break
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
                "kind": _page_kind(path),
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

    ga = fetch_ga_traffic(range_key, start_day=ga_start, end_day=ga_end)
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
                        "kind": _page_kind(path),
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
            "journeys": journeys_payload,
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
