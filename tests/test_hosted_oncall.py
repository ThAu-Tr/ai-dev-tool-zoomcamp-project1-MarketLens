from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import asyncio

import pytest

from hosted_oncall.agent import HostedOnCallPolicy, process_claimed_incident
from hosted_oncall.ledger import SQLiteIncidentLedger
from hosted_oncall.receiver import NotificationError, parse_notification, receive_notification, verify_hmac
from hosted_oncall.render import RenderRecoveryAdapter


DASHBOARD_URL = "https://marketlens-dtc.onrender.com/api/dashboard"
SECRET = "a-test-only-grafana-secret-with-more-than-32-bytes"
NOW = 1_798_688_000


def run(coro):
    return asyncio.run(coro)


def make_notification(*, labels: dict | None = None, status: str = "firing", extra: dict | None = None) -> bytes:
    alert_labels = {
        "alertname": "MarketLensProductionDashboardUnavailable",
        "service": "marketlens",
        "environment": "production",
        "source": "synthetic",
        "severity": "critical",
        "job": "marketlens-production-dashboard",
        "instance": DASHBOARD_URL,
    }
    alert_labels.update(labels or {})
    alert = {
        "status": status,
        "fingerprint": "ab12cd34ef56",
        "startsAt": "2026-10-26T12:00:00Z",
        "labels": alert_labels,
        "annotations": {"summary": "secret-like alert text must not persist"},
        "values": {"A": "private-value"},
        "generatorURL": "https://grafana.example/secret-query",
    }
    if extra:
        alert.update(extra)
    return json.dumps({"status": status, "alerts": [alert], "externalURL": "https://example.invalid"}).encode()


def signed_headers(body: bytes, timestamp: str = str(NOW)) -> tuple[str, str]:
    signature = hmac.new(SECRET.encode(), timestamp.encode() + b":" + body, hashlib.sha256).hexdigest()
    return signature, timestamp


def test_webhook_hmac_accepts_only_fresh_signed_raw_body() -> None:
    body = make_notification()
    signature, timestamp = signed_headers(body)

    verify_hmac(body, signature, timestamp, SECRET, now=NOW)

    with pytest.raises(NotificationError, match="invalid_signature"):
        verify_hmac(body + b" ", signature, timestamp, SECRET, now=NOW)
    with pytest.raises(NotificationError, match="stale_timestamp"):
        verify_hmac(body, signature, timestamp, SECRET, now=NOW + 301)
    with pytest.raises(NotificationError, match="invalid_timestamp"):
        verify_hmac(body, signature, "not-a-time", SECRET, now=NOW)


def test_notification_accepts_exact_production_alert_and_redacts_payload() -> None:
    event = parse_notification(make_notification(), DASHBOARD_URL)[0]

    assert event == {
        "status": "firing",
        "fingerprint": "ab12cd34ef56",
        "startsAt": "2026-10-26T12:00:00Z",
        "labels": {
            "alertname": "MarketLensProductionDashboardUnavailable",
            "service": "marketlens",
            "environment": "production",
            "source": "synthetic",
            "severity": "critical",
            "job": "marketlens-production-dashboard",
            "instance": DASHBOARD_URL,
        },
    }
    assert "annotations" not in event and "values" not in event


@pytest.mark.parametrize("labels", [
    {"service": "other"},
    {"environment": "staging"},
    {"source": "local"},
    {"alertname": "OtherAlert"},
    {"instance": "https://attacker.example/api/dashboard"},
])
def test_notification_ignores_unrelated_or_misdirected_alerts(labels: dict) -> None:
    assert parse_notification(make_notification(labels=labels), DASHBOARD_URL) == []


def test_notification_rejects_malformed_or_oversized_payload() -> None:
    with pytest.raises(NotificationError, match="invalid_payload_size"):
        parse_notification(b"", DASHBOARD_URL)
    with pytest.raises(NotificationError, match="invalid_payload_size"):
        parse_notification(b"x" * 65_537, DASHBOARD_URL)
    with pytest.raises(NotificationError, match="invalid_json"):
        parse_notification(b"not json", DASHBOARD_URL)
    with pytest.raises(NotificationError, match="invalid_notification"):
        parse_notification(b'{"status":"pending","alerts":[]}', DASHBOARD_URL)


def test_receiver_authenticates_and_submits_only_redacted_event_before_ack() -> None:
    body = make_notification()
    signature, timestamp = signed_headers(body)
    submitted: list[dict] = []

    async def submit(events):
        submitted.extend(events)
        return len(events)

    accepted = run(receive_notification(
        body, signature=signature, timestamp=timestamp, secret=SECRET,
        dashboard_url=DASHBOARD_URL, submit_events=submit, now=NOW,
    ))

    assert accepted == 1
    assert len(submitted) == 1
    assert "secret-like" not in json.dumps(submitted)

    async def must_not_submit(_events):
        pytest.fail("bad authentication must not reach durable storage")

    with pytest.raises(NotificationError, match="invalid_signature"):
        run(receive_notification(
            body, signature="0" * 64, timestamp=timestamp, secret=SECRET,
            dashboard_url=DASHBOARD_URL, submit_events=must_not_submit, now=NOW,
        ))


class FakeAdapter:
    def __init__(self, *, dashboard=(False,), readiness=(200,), render="ready", restart=True):
        self.dashboard = list(dashboard)
        self.readiness = list(readiness)
        self.render = render
        self.restart = restart
        self.waits: list[float] = []
        self.restart_calls = 0

    async def dashboard_healthy(self):
        return self.dashboard.pop(0) if len(self.dashboard) > 1 else self.dashboard[0]

    async def database_ready(self):
        return self.readiness.pop(0) if len(self.readiness) > 1 else self.readiness[0]

    async def render_preflight(self):
        return self.render

    async def restart_service(self):
        self.restart_calls += 1
        return self.restart

    async def wait(self, seconds: float):
        self.waits.append(seconds)


@pytest.mark.parametrize(("dashboard", "readiness", "render", "expected"), [
    ([True], [200], "ready", "already_healthy"),
    ([False], [503], "ready", "database_unavailable"),
    ([False], [None], "ready", "readiness_unknown"),
    ([None], [200], "ready", "dashboard_probe_unknown"),
    ([False, True], [200], "ready", "cold_start_recovered"),
    ([False, False], [200, 200], "deployment_in_progress", "deployment_in_progress"),
    ([False, False], [200, 200], "render_service_suspended", "render_service_suspended"),
])
def test_preflight_no_action_for_healthy_database_cold_start_or_unknown(
    dashboard, readiness, render, expected
) -> None:
    adapter = FakeAdapter(dashboard=dashboard, readiness=readiness, render=render)

    outcome = run(HostedOnCallPolicy(adapter).run(lambda: pytest.fail("must not persist an action attempt")))

    assert outcome == expected
    assert adapter.restart_calls == 0


@pytest.mark.parametrize("initial_readiness", [503, None])
def test_temporary_readiness_failure_recovers_during_cold_start_grace(initial_readiness) -> None:
    adapter = FakeAdapter(
        dashboard=[False, True], readiness=[initial_readiness, 200], render="ready"
    )

    outcome = run(HostedOnCallPolicy(adapter).run(lambda: pytest.fail("must not restart")))

    assert outcome == "cold_start_recovered"
    assert adapter.waits == [70]
    assert adapter.restart_calls == 0


@pytest.mark.parametrize(("readiness", "expected"), [
    ([200, 503], "database_unavailable"),
    ([None, None], "readiness_unknown"),
])
def test_persistent_post_grace_readiness_failure_never_restarts(readiness, expected) -> None:
    adapter = FakeAdapter(dashboard=[False, False], readiness=readiness, render="ready")

    outcome = run(HostedOnCallPolicy(adapter).run(lambda: pytest.fail("must not restart")))

    assert outcome == expected
    assert adapter.waits == [70]
    assert adapter.restart_calls == 0


def test_recoverable_failure_persists_attempt_then_restarts_once_and_verifies() -> None:
    adapter = FakeAdapter(dashboard=[False, False, True], readiness=[200, 200, 200])
    transitions: list[str] = []

    outcome = run(HostedOnCallPolicy(adapter).run(lambda: transitions.append("attempted") or True))

    assert outcome == "recovered"
    assert transitions == ["attempted"]
    assert adapter.restart_calls == 1
    assert adapter.waits == [70]


def test_failed_or_ambiguous_restart_does_not_retry() -> None:
    adapter = FakeAdapter(dashboard=[False, False], readiness=[200, 200], restart=False)

    outcome = run(HostedOnCallPolicy(adapter).run(lambda: True))

    assert outcome == "restart_rejected"
    assert adapter.restart_calls == 1


def test_failed_durable_attempt_write_prevents_restart() -> None:
    adapter = FakeAdapter(dashboard=[False, False], readiness=[200, 200])

    outcome = run(HostedOnCallPolicy(adapter).run(lambda: False))

    assert outcome == "state_unavailable"
    assert adapter.restart_calls == 0


def test_render_adapter_uses_only_fixed_target_and_restart_endpoint() -> None:
    calls: list[tuple[str, str, dict, int]] = []
    dashboard = {"assets": [], "articles": [], "summaries": [], "lastRefreshedAt": "Not refreshed yet", "newsStatus": "current", "aiStatus": "unknown"}

    async def request(method, url, *, headers, timeout):
        calls.append((method, url, headers, timeout))
        if url == DASHBOARD_URL:
            return 200, json.dumps(dashboard).encode()
        if url.endswith("/health/ready"):
            return 200, b""
        if url.endswith("/services/srv-fixed123"):
            return 200, json.dumps({"id": "srv-fixed123", "type": "web_service", "suspended": "not_suspended", "serviceDetails": {"url": "https://marketlens-dtc.onrender.com"}}).encode()
        if "/deploys?" in url:
            return 200, json.dumps([{"deploy": {"status": "live", "createdAt": "2026-10-26T11:00:00Z"}}]).encode()
        if url.endswith("/services/srv-fixed123/restart"):
            return 200, b"{}"
        raise AssertionError(f"Unexpected request {method} {url}")

    adapter = RenderRecoveryAdapter(request=request, api_key="fake-test-key", service_id="srv-fixed123", dashboard_url=DASHBOARD_URL)

    assert run(adapter.dashboard_healthy()) is True
    assert run(adapter.database_ready()) == 200
    assert run(adapter.render_preflight()) == "ready"
    assert run(adapter.restart_service()) is True
    post_requests = [call for call in calls if call[0] == "POST"]
    assert post_requests == [(
        "POST", "https://api.render.com/v1/services/srv-fixed123/restart",
        {"accept": "application/json", "authorization": "Bearer fake-test-key"}, 10,
    )]
    assert all("Authorization" not in str(call[2]) for call in calls if call[0] != "POST")


def test_render_adapter_rejects_wrong_target_and_non_live_deploy() -> None:
    async def request(method, url, *, headers, timeout):
        if url.endswith("/services/srv-fixed123"):
            return 200, json.dumps({"id": "srv-other", "type": "web_service", "suspended": "not_suspended", "serviceDetails": {"url": "https://marketlens-dtc.onrender.com"}}).encode()
        if "/deploys?" in url:
            return 200, json.dumps([{"deploy": {"status": "live", "createdAt": "2026-10-26T11:00:00Z"}}]).encode()
        return 200, b"{}"

    adapter = RenderRecoveryAdapter(request=request, api_key="fake", service_id="srv-fixed123", dashboard_url=DASHBOARD_URL)
    assert run(adapter.render_preflight()) == "render_target_mismatch"
    with pytest.raises(ValueError, match="invalid_render_service_id"):
        RenderRecoveryAdapter(request=request, api_key="fake", service_id="arbitrary", dashboard_url=DASHBOARD_URL)
    with pytest.raises(ValueError, match="invalid_recovery_configuration"):
        RenderRecoveryAdapter(request=request, api_key="fake", service_id="srv-fixed123", dashboard_url="https://evil.example/api/dashboard")


def test_render_restart_rechecks_service_and_deploy_state_immediately_before_action() -> None:
    calls: list[str] = []

    async def request(method, url, *, headers, timeout):
        calls.append(f"{method} {url}")
        if url.endswith("/services/srv-fixed123"):
            return 200, json.dumps({"id": "srv-fixed123", "type": "web_service", "suspended": "not_suspended", "serviceDetails": {"url": "https://marketlens-dtc.onrender.com"}}).encode()
        if "/deploys?" in url:
            return 200, json.dumps([{"deploy": {"status": "update_in_progress", "createdAt": "2026-10-26T12:00:00Z"}}]).encode()
        raise AssertionError("Render restart must not run while a deployment is active")

    adapter = RenderRecoveryAdapter(request=request, api_key="fake", service_id="srv-fixed123", dashboard_url=DASHBOARD_URL)

    assert run(adapter.restart_service()) is False
    assert len(calls) == 2


class SqliteStorage:
    """Small local analogue of DurableObjectStorage.sql for persistence tests."""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def exec(self, query: str, *values):
        return self.connection.execute(query, values)


def test_incident_state_and_audit_survive_new_ledger_instances_and_suppress_replay() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    first_instance = SQLiteIncidentLedger(SqliteStorage(connection), now=lambda: NOW)
    event = parse_notification(make_notification(), DASHBOARD_URL)[0]
    key = first_instance.incident_key(event)

    assert first_instance.submit(event) == "queued"
    claimed = first_instance.claim_next()
    assert claimed["status"] == "preflight"
    assert first_instance.transition(key, "attempted", "single_restart_boundary") is True

    second_instance = SQLiteIncidentLedger(SqliteStorage(connection), now=lambda: NOW + 5)
    assert second_instance.submit(event) == "duplicate"
    assert second_instance.claim_next() is None
    audit = second_instance.audit(key)
    assert [(row["status"], row["reason"]) for row in audit] == [
        ("received", "approved_firing_alert"),
        ("preflight", "durable_work_claimed"),
        ("attempted", "single_restart_boundary"),
        ("duplicate", "repeated_firing_alert"),
    ]
    assert "secret-like" not in json.dumps(audit)


def test_interrupted_or_unreadable_durable_state_fails_closed() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    ledger = SQLiteIncidentLedger(SqliteStorage(connection), now=lambda: NOW)
    event = parse_notification(make_notification(), DASHBOARD_URL)[0]
    key = ledger.incident_key(event)
    ledger.submit(event)
    ledger.claim_next()
    assert ledger.fail_interrupted_work() == 1
    assert ledger.claim_next() is None
    assert ledger.audit(key)[-1]["reason"] == "processing_interrupted"

    class BrokenStorage:
        def exec(self, *args):
            raise OSError("private storage error")

    with pytest.raises(OSError):
        SQLiteIncidentLedger(BrokenStorage())


def test_durable_alarm_policy_replays_without_a_second_render_action() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    event = parse_notification(make_notification(), DASHBOARD_URL)[0]
    adapter = FakeAdapter(dashboard=[False, False, True], readiness=[200, 200, 200])
    first = SQLiteIncidentLedger(SqliteStorage(connection), now=lambda: NOW)
    key = first.incident_key(event)
    assert first.submit(event) == "queued"
    work = first.claim_next()

    status, reason = run(process_claimed_incident(first, work, adapter))
    assert (status, reason) == ("recovered", "recovered")
    assert adapter.restart_calls == 1

    # New Durable Object instance, same persistent SQLite storage and alert.
    second = SQLiteIncidentLedger(SqliteStorage(connection), now=lambda: NOW + 10)
    assert second.submit(event) == "duplicate"
    assert second.claim_next() is None
    assert second.audit(key)[-2]["status"] == "recovered"
    assert adapter.restart_calls == 1

    resolved = dict(event, status="resolved")
    assert second.submit(resolved) == "queued"
    resolve_work = second.claim_next()
    resolved_status, resolved_reason = run(process_claimed_incident(second, resolve_work, adapter))
    assert (resolved_status, resolved_reason) == ("resolved", "resolved_verified")
    assert adapter.restart_calls == 1
