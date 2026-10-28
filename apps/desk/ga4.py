"""
Read traffic numbers from Google Analytics 4 for the Desk.

Needs:
  GA4_PROPERTY_ID — the numeric property id (Admin → Property settings), not G-XXXX
  GA4_CREDENTIALS_JSON — full service-account JSON as one line, or
  GOOGLE_APPLICATION_CREDENTIALS — path to that JSON file inside the container

If either is missing, or Google returns an error, callers get connected=False.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class GaTraffic:
    connected: bool
    visitors: int = 0
    sessions: int = 0
    page_views: int = 0
    visitor_daily: list[dict[str, Any]] = field(default_factory=list)
    top_pages: list[dict[str, Any]] = field(default_factory=list)
    channels: list[dict[str, Any]] = field(default_factory=list)
    campaign_sessions: list[dict[str, Any]] = field(default_factory=list)
    work_service_sessions: int = 0
    error: str = ""


def _property_id() -> str:
    return str(getattr(settings, "GA4_PROPERTY_ID", "") or "").strip()


def _credentials_info() -> dict[str, Any] | None:
    raw = str(getattr(settings, "GA4_CREDENTIALS_JSON", "") or "").strip()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("client_email"):
                return data
        except json.JSONDecodeError:
            logger.warning("GA4_CREDENTIALS_JSON is not valid JSON.")
            return None
    path = (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    if path and os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict) and data.get("client_email"):
                return data
        except (OSError, json.JSONDecodeError):
            logger.exception("Could not read GOOGLE_APPLICATION_CREDENTIALS.")
    return None


def ga4_configured() -> bool:
    return bool(_property_id() and _credentials_info())


def _date_bounds(range_key: str) -> tuple[date, date]:
    today = timezone.localdate()
    if range_key == "today":
        return today, today
    if range_key == "30d":
        return today - timedelta(days=29), today
    return today - timedelta(days=6), today


def fetch_ga_traffic(
    range_key: str = "7d",
    *,
    start_day: date | None = None,
    end_day: date | None = None,
) -> GaTraffic:
    """Pull the Desk traffic block. Never raises to the request."""
    property_id = _property_id()
    info = _credentials_info()
    if not property_id or not info:
        return GaTraffic(connected=False, error="GA4 is not configured.")

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Filter,
            FilterExpression,
            FilterExpressionList,
            Metric,
            OrderBy,
            RunReportRequest,
        )
        from google.oauth2 import service_account
    except ImportError as exc:
        logger.warning("GA4 import failed: %s", exc)
        return GaTraffic(connected=False, error=f"GA4 import failed: {exc}"[:200])

    try:
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=credentials)
        if start_day and end_day:
            start, end = start_day, end_day
            if start > end:
                start, end = end, start
        else:
            start, end = _date_bounds(range_key)
        date_range = DateRange(start_date=start.isoformat(), end_date=end.isoformat())
        property_name = f"properties/{property_id}"

        totals = client.run_report(
            RunReportRequest(
                property=property_name,
                date_ranges=[date_range],
                metrics=[
                    Metric(name="activeUsers"),
                    Metric(name="sessions"),
                    Metric(name="screenPageViews"),
                ],
            )
        )
        visitors = sessions = page_views = 0
        if totals.rows:
            values = totals.rows[0].metric_values
            visitors = int(float(values[0].value or 0))
            sessions = int(float(values[1].value or 0))
            page_views = int(float(values[2].value or 0))

        daily = client.run_report(
            RunReportRequest(
                property=property_name,
                date_ranges=[date_range],
                dimensions=[Dimension(name="date")],
                metrics=[Metric(name="activeUsers")],
                order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
            )
        )
        visitor_daily = []
        for index, row in enumerate(daily.rows or []):
            raw_day = row.dimension_values[0].value  # YYYYMMDD
            parsed = datetime.strptime(raw_day, "%Y%m%d")
            label = parsed.strftime("%d %b" if index == 0 else "%d").lstrip("0")
            visitor_daily.append(
                {"label": label, "value": int(float(row.metric_values[0].value or 0))}
            )

        pages = client.run_report(
            RunReportRequest(
                property=property_name,
                date_ranges=[date_range],
                dimensions=[Dimension(name="pagePath")],
                metrics=[Metric(name="screenPageViews")],
                order_bys=[
                    OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)
                ],
                limit=12,
            )
        )
        top_pages = [
            {
                "path": row.dimension_values[0].value or "/",
                "views": int(float(row.metric_values[0].value or 0)),
                "briefs": 0,
            }
            for row in (pages.rows or [])
        ]

        channels_report = client.run_report(
            RunReportRequest(
                property=property_name,
                date_ranges=[date_range],
                dimensions=[Dimension(name="sessionDefaultChannelGroup")],
                metrics=[Metric(name="sessions")],
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
                limit=8,
            )
        )
        channels = [
            {
                "name": row.dimension_values[0].value or "Other",
                "sessions": int(float(row.metric_values[0].value or 0)),
                "briefs": 0,
            }
            for row in (channels_report.rows or [])
        ]

        campaigns_report = client.run_report(
            RunReportRequest(
                property=property_name,
                date_ranges=[date_range],
                dimensions=[
                    Dimension(name="sessionSource"),
                    Dimension(name="sessionMedium"),
                    Dimension(name="sessionCampaignName"),
                ],
                metrics=[Metric(name="sessions")],
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
                limit=12,
                dimension_filter=FilterExpression(
                    not_expression=FilterExpression(
                        filter=Filter(
                            field_name="sessionCampaignName",
                            string_filter=Filter.StringFilter(
                                match_type=Filter.StringFilter.MatchType.EXACT,
                                value="(not set)",
                            ),
                        )
                    )
                ),
            )
        )
        campaign_sessions = [
            {
                "source": row.dimension_values[0].value or "(direct)",
                "medium": row.dimension_values[1].value or "(none)",
                "campaign": row.dimension_values[2].value or "(none)",
                "sessions": int(float(row.metric_values[0].value or 0)),
            }
            for row in (campaigns_report.rows or [])
        ]

        work_filter = FilterExpression(
            or_group=FilterExpressionList(
                expressions=[
                    FilterExpression(
                        filter=Filter(
                            field_name="pagePath",
                            string_filter=Filter.StringFilter(
                                match_type=Filter.StringFilter.MatchType.BEGINS_WITH,
                                value="/work",
                            ),
                        )
                    ),
                    FilterExpression(
                        filter=Filter(
                            field_name="pagePath",
                            string_filter=Filter.StringFilter(
                                match_type=Filter.StringFilter.MatchType.BEGINS_WITH,
                                value="/services",
                            ),
                        )
                    ),
                ]
            )
        )
        work_report = client.run_report(
            RunReportRequest(
                property=property_name,
                date_ranges=[date_range],
                metrics=[Metric(name="sessions")],
                dimension_filter=work_filter,
            )
        )
        work_service_sessions = 0
        if work_report.rows:
            work_service_sessions = int(float(work_report.rows[0].metric_values[0].value or 0))

        return GaTraffic(
            connected=True,
            visitors=visitors,
            sessions=sessions,
            page_views=page_views,
            visitor_daily=visitor_daily,
            top_pages=top_pages,
            channels=channels,
            campaign_sessions=campaign_sessions,
            work_service_sessions=work_service_sessions,
        )
    except Exception as exc:
        logger.exception("GA4 report failed.")
        return GaTraffic(connected=False, error=str(exc)[:200])
