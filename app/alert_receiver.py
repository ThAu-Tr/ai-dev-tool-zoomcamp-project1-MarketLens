"""Local-only, redacting Grafana webhook receiver for dashboard alerts."""

from __future__ import annotations

import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, urlsplit

logger = logging.getLogger("marketlens.alert_receiver")
SAFE_LABEL_VALUES = {
    "alertname": {"Dashboard unavailable"},
    "alert_id": {"dashboard-availability"},
    "severity": {"critical"},
    "journey": {"dashboard"},
    "http_route": {"/api/dashboard"},
    "http_request_method": {"GET"},
    "http_response_status_class": {"5xx"},
    "journey_outcome": {"failure"},
}


class DeliveryRegistry:
    """Keep redacted transitions and surface one repeat signal per firing alert."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._seen: set[tuple[str, str, str]] = set()
        self._repeated: set[tuple[str, str, str]] = set()
        self._events: list[dict[str, Any]] = []

    def accept(self, payload: dict[str, Any]) -> tuple[int, int]:
        alerts = payload.get("alerts", [])
        if not isinstance(alerts, list):
            raise ValueError("invalid alert notification")
        new_count = 0
        with self._lock:
            for alert in alerts:
                if not isinstance(alert, dict):
                    continue
                status = alert.get("status", payload.get("status"))
                if status not in {"firing", "resolved"}:
                    continue
                labels = alert.get("labels", {})
                if not isinstance(labels, dict) or labels.get("alert_id") != "dashboard-availability":
                    logger.info(
                        "alert_delivery_ignored reason=unapproved_rule status=%s",
                        status,
                    )
                    continue
                fingerprint = alert.get("fingerprint")
                starts_at = alert.get("startsAt")
                if (
                    not isinstance(fingerprint, str)
                    or re.fullmatch(r"[0-9a-fA-F]{8,64}", fingerprint) is None
                    or not isinstance(starts_at, str)
                    or len(starts_at) > 40
                ):
                    continue
                key = (fingerprint, status, starts_at)
                safe_labels = {
                    key: labels[key]
                    for key, allowed in SAFE_LABEL_VALUES.items()
                    if labels.get(key) in allowed
                }
                trace_id = labels.get("trace_id")
                if isinstance(trace_id, str) and re.fullmatch(r"[0-9a-fA-F]{32}", trace_id):
                    safe_labels["trace_id"] = trace_id
                if key in self._seen:
                    if status == "firing" and key not in self._repeated:
                        self._repeated.add(key)
                        event = {"status": "repeated", "fingerprint": fingerprint,
                                 "startsAt": starts_at, "labels": safe_labels}
                        self._events.append(event)
                        logger.info("alert_delivery %s", json.dumps(event, sort_keys=True, separators=(",", ":")))
                        new_count += 1
                    continue
                self._seen.add(key)
                event = {"status": status, "fingerprint": fingerprint, "startsAt": starts_at, "labels": safe_labels}
                self._events.append(event)
                logger.info("alert_delivery %s", json.dumps(event, sort_keys=True, separators=(",", ":")))
                new_count += 1
        return len(alerts), new_count

    def events(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)

    def events_after(self, cursor: int) -> tuple[list[dict[str, Any]], int]:
        with self._lock:
            next_cursor = len(self._events)
            if cursor > next_cursor:
                cursor = next_cursor
            return list(self._events[cursor:]), next_cursor


registry = DeliveryRegistry()


class AlertHandler(BaseHTTPRequestHandler):
    server_version = "MarketLensAlertReceiver/1"

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path != "/agent/events":
            self.send_error(404)
            return
        try:
            query = parse_qs(parsed.query, strict_parsing=True)
            if set(query) - {"after"} or len(query.get("after", ["0"])) != 1:
                raise ValueError
            cursor = int(query.get("after", ["0"])[0])
            if cursor < 0:
                raise ValueError
        except (ValueError, TypeError):
            self.send_error(400)
            return
        events, next_cursor = registry.events_after(cursor)
        body = json.dumps({"events": events, "cursor": next_cursor}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/webhook":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 65536:
                raise ValueError("invalid payload size")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("invalid alert notification")
            total, accepted = registry.accept(payload)
        except (ValueError, json.JSONDecodeError):
            self.send_error(400)
            return
        body = json.dumps({"received": total, "accepted": accepted}).encode()
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        # Never log request headers or the webhook payload.
        logger.info("webhook_http %s %s", self.command, self.path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ThreadingHTTPServer(("0.0.0.0", 8080), AlertHandler).serve_forever()


if __name__ == "__main__":
    main()
