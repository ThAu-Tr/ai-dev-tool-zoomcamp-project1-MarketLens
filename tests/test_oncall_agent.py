from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from app import alert_receiver
from app.alert_receiver import AlertHandler, DeliveryRegistry
from app.oncall_agent import DatabaseState, DockerComposeRecovery, OnCallAgent, poll_once


class FakeRecovery:
    def __init__(self, state=None, acted=True, healthy=True, dashboard=True):
        self.state = state or DatabaseState("marketlens-observability", "db", "exited", "none")
        self.acted, self.healthy, self.dashboard = acted, healthy, dashboard
        self.actions = []
        self.inspections = 0

    def inspect_database(self):
        self.inspections += 1
        return self.state

    def remediate_database(self, action):
        self.actions.append(action)
        return self.acted

    def wait_database_healthy(self):
        return self.healthy

    def dashboard_healthy(self):
        return self.dashboard


def event(status="firing", *, fingerprint="a1b2c3d4", starts_at="2026-10-25T19:00:00Z", **changes):
    labels = {
        "alert_id": "dashboard-availability", "journey": "dashboard",
        "http_route": "/api/dashboard", "http_request_method": "GET",
        "http_response_status_class": "5xx", "journey_outcome": "failure",
    }
    labels.update(changes)
    return {"status": status, "fingerprint": fingerprint, "startsAt": starts_at, "labels": labels}


def test_stopped_database_uses_the_single_restart_action_and_resolution_rechecks_dashboard():
    recovery, records = FakeRecovery(), []
    agent = OnCallAgent(recovery, records.append)
    agent.handle(event())
    agent.handle(event())
    agent.handle(event("resolved"))
    agent.handle(event("resolved"))
    assert recovery.actions == ["restart"]
    assert records == ["oncall status=recovered action=restart dashboard=healthy",
                       "oncall status=escalated reason=repeated_alert", "oncall status=resolved_verified",
                       "oncall status=duplicate_ignored"]


def test_unhealthy_database_restarts_only_the_fixed_db():
    recovery = FakeRecovery(DatabaseState("marketlens-observability", "db", "running", "unhealthy"))
    OnCallAgent(recovery, lambda _: None).handle(event())
    assert recovery.actions == ["restart"]


def test_unapproved_or_mismatched_target_escalates_without_action():
    recovery, records = FakeRecovery(), []
    agent = OnCallAgent(recovery, records.append)
    agent.handle(event(alert_id="other"))
    agent.handle(event(fingerprint="bad!"))
    mismatch = FakeRecovery(DatabaseState("other-project", "db", "exited", "none"))
    OnCallAgent(mismatch, records.append).handle(event())
    assert recovery.actions == []
    assert mismatch.actions == []
    assert records == ["oncall status=escalated reason=unapproved_alert",
                       "oncall status=escalated reason=unapproved_alert",
                       "oncall status=escalated reason=target_mismatch"]


def test_healthy_database_and_failed_verification_escalate_without_retries():
    healthy = FakeRecovery(DatabaseState("marketlens-observability", "db", "running", "healthy"))
    OnCallAgent(healthy, lambda _: None).handle(event())
    assert healthy.actions == []

    unknown = FakeRecovery(DatabaseState("marketlens-observability", "db", "paused", "none"))
    OnCallAgent(unknown, lambda _: None).handle(event())
    assert unknown.actions == []

    failed = FakeRecovery(healthy=False)
    agent = OnCallAgent(failed, lambda _: None)
    agent.handle(event())
    agent.handle(event("resolved"))
    assert failed.actions == ["restart"]
    assert failed.inspections == 1

    api_failed = FakeRecovery(dashboard=False)
    OnCallAgent(api_failed, lambda _: None).handle(event())
    assert api_failed.actions == ["restart"]


def test_unhealthy_action_failure_is_not_retried_for_same_alert_key():
    recovery = FakeRecovery(DatabaseState("marketlens-observability", "db", "running", "unhealthy"), acted=False)
    agent = OnCallAgent(recovery, lambda _: None)
    agent.handle(event())
    agent.handle(event())
    assert recovery.actions == ["restart"]


def test_docker_adapter_uses_fixed_argv_without_shell(monkeypatch, tmp_path):
    import subprocess

    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        if args[:2] == ["docker", "compose"] and "ps" in args:
            output = "0123456789abcdef0123456789abcdef"
        elif args[:2] == ["docker", "inspect"]:
            output = "marketlens-observability|db|exited|none"
        else:
            output = ""
        return subprocess.CompletedProcess(args, 0, stdout=output, stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    adapter = DockerComposeRecovery(tmp_path)
    assert adapter.inspect_database() == DatabaseState("marketlens-observability", "db", "exited", "none")
    assert adapter.remediate_database("restart")
    assert not adapter.remediate_database("start")
    assert calls[0][0][-4:] == ["ps", "--all", "-q", "db"]
    assert calls[2][0][-2:] == ["restart", "db"]
    assert all(call[1]["shell"] is False and call[1]["timeout"] == 10 for call in calls)
    assert all("marketlens-observability" in call[0] or call[0][1] == "inspect" for call in calls)


def test_receiver_feed_poll_wakes_agent_and_escalates_repeated_delivery(monkeypatch):
    registry = DeliveryRegistry()
    monkeypatch.setattr(alert_receiver, "registry", registry)
    server = ThreadingHTTPServer(("127.0.0.1", 0), AlertHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        alert = event()
        alert["labels"]["authorization"] = "Bearer private-value"
        payload = json.dumps({"status": "firing", "alerts": [alert]}).encode()
        post_url = f"http://127.0.0.1:{server.server_port}/webhook"
        for _ in range(2):
            request = Request(post_url, data=payload, headers={"Content-Type": "application/json"})
            with urlopen(request) as response:
                assert response.status == 202

        recovery, records = FakeRecovery(), []
        agent = OnCallAgent(recovery, records.append)
        cursor = poll_once(0, agent, f"http://127.0.0.1:{server.server_port}/agent/events")
        assert cursor == 2
        assert recovery.actions == ["restart"]
        assert records == ["oncall status=recovered action=restart dashboard=healthy",
                           "oncall status=escalated reason=repeated_alert"]
        assert "private-value" not in json.dumps(registry.events())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
