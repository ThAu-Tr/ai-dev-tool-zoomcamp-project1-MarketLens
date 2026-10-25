from __future__ import annotations

import json
import logging

from app.alert_receiver import DeliveryRegistry


def notification(status: str) -> dict:
    return {
        "status": status,
        "receiver": "ignored",
        "alerts": [
            {
                "status": status,
                "fingerprint": "a1b2c3d4",
                "startsAt": "2026-10-25T19:00:00Z",
                "labels": {
                    "alertname": "Dashboard unavailable",
                    "alert_id": "dashboard-availability",
                    "severity": "critical",
                    "journey": "dashboard",
                    "trace_id": "1234567890abcdef1234567890abcdef",
                    "authorization": "Bearer private-token",
                    "tenant": "customer-private-data",
                },
                "annotations": {"description": "SQL password private-value"},
                "generatorURL": "http://grafana/?token=api-secret",
            }
        ],
    }


def test_alert_delivery_trigger_recovery_and_duplicate_suppression(caplog) -> None:
    registry = DeliveryRegistry()
    caplog.set_level(logging.INFO, logger="marketlens.alert_receiver")

    total, accepted = registry.accept(notification("firing"))
    assert (total, accepted) == (1, 1)
    assert registry.accept(notification("firing")) == (1, 0)

    assert registry.accept(notification("resolved")) == (1, 1)
    assert registry.accept(notification("resolved")) == (1, 0)
    assert [event["status"] for event in registry.events()] == ["firing", "resolved"]

    delivered = " ".join(caplog.messages)
    assert "1234567890abcdef1234567890abcdef" in delivered
    assert all(secret not in delivered for secret in ("private-token", "customer-private-data", "private-value", "api-secret"))
    assert "annotations" not in json.dumps(registry.events())


def test_receiver_ignores_unapproved_alerts_and_malformed_correlation() -> None:
    registry = DeliveryRegistry()
    unidentified_alert = notification("firing")
    del unidentified_alert["alerts"][0]["labels"]["alert_id"]
    assert registry.accept(unidentified_alert) == (1, 0)

    other_alert = notification("firing")
    other_alert["alerts"][0]["labels"]["alert_id"] = "other-alert"
    assert registry.accept(other_alert) == (1, 0)

    malformed_trace = notification("firing")
    malformed_trace["alerts"][0]["labels"]["trace_id"] = "not-a-trace-id"
    assert registry.accept(malformed_trace) == (1, 1)
    assert "trace_id" not in registry.events()[0]["labels"]
