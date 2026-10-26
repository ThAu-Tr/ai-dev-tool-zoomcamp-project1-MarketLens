"""Strict, signed Grafana notification validation for the hosted responder."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from datetime import datetime
from typing import Any

MAX_BODY_BYTES = 65_536
MAX_TIMESTAMP_AGE_SECONDS = 300
FINGERPRINT_RE = re.compile(r"^[a-fA-F0-9]{8,64}$")
SERVICE_ID_RE = re.compile(r"^srv-[A-Za-z0-9]+$")
APPROVED_ALERT = "MarketLensProductionDashboardUnavailable"
APPROVED_LABELS = {
    "service": "marketlens",
    "environment": "production",
    "source": "synthetic",
    "severity": "critical",
    "job": "marketlens-production-dashboard",
}


class NotificationError(ValueError):
    """A request is not a fresh, authentic, approved Grafana notification."""


def verify_hmac(
    raw_body: bytes,
    signature: str | None,
    timestamp: str | None,
    secret: str,
    *,
    now: float | None = None,
) -> None:
    if not isinstance(secret, str) or len(secret) < 32:
        raise NotificationError("webhook_auth_unavailable")
    if not isinstance(signature, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", signature):
        raise NotificationError("invalid_signature")
    if not isinstance(timestamp, str) or not re.fullmatch(r"\d{10,13}", timestamp):
        raise NotificationError("invalid_timestamp")
    stamp = int(timestamp)
    if len(timestamp) == 13:
        stamp //= 1000
    current = int(time.time() if now is None else now)
    if abs(current - stamp) > MAX_TIMESTAMP_AGE_SECONDS:
        raise NotificationError("stale_timestamp")
    signed = timestamp.encode("ascii") + b":" + raw_body
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature.lower()):
        raise NotificationError("invalid_signature")


def _valid_iso_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 40:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def parse_notification(raw_body: bytes, dashboard_url: str) -> list[dict[str, Any]]:
    """Return only allowlisted event data; never forward Grafana prose or values."""
    if not raw_body or len(raw_body) > MAX_BODY_BYTES:
        raise NotificationError("invalid_payload_size")
    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise NotificationError("invalid_json") from error
    if not isinstance(payload, dict) or payload.get("status") not in {"firing", "resolved"}:
        raise NotificationError("invalid_notification")
    alerts = payload.get("alerts")
    if not isinstance(alerts, list) or len(alerts) > 20:
        raise NotificationError("invalid_alert_list")

    accepted: list[dict[str, Any]] = []
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        labels = alert.get("labels")
        status = alert.get("status", payload["status"])
        if not isinstance(labels, dict) or status not in {"firing", "resolved"}:
            continue
        if labels.get("alertname") != APPROVED_ALERT:
            continue
        if any(labels.get(key) != value for key, value in APPROVED_LABELS.items()):
            continue
        if labels.get("instance") != dashboard_url:
            continue
        fingerprint = alert.get("fingerprint")
        starts_at = alert.get("startsAt")
        if not isinstance(fingerprint, str) or not FINGERPRINT_RE.fullmatch(fingerprint):
            continue
        if not _valid_iso_timestamp(starts_at):
            continue
        # Do not copy untrusted annotations, values, generator URLs, or payload fields.
        accepted.append({
            "status": status,
            "fingerprint": fingerprint.lower(),
            "startsAt": starts_at,
            "labels": {
                "alertname": APPROVED_ALERT,
                **APPROVED_LABELS,
                "instance": dashboard_url,
            },
        })
    return accepted


async def receive_notification(
    raw_body: bytes,
    *,
    signature: str | None,
    timestamp: str | None,
    secret: str,
    dashboard_url: str,
    submit_events,
    now: float | None = None,
) -> int:
    """Authenticate, normalize, and durably enqueue before acknowledging."""
    verify_hmac(raw_body, signature, timestamp, secret, now=now)
    events = parse_notification(raw_body, dashboard_url)
    if not events:
        return 0
    return await submit_events(events)
