"""Fixed, local-only recovery agent for the observability dashboard alert."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

logger = logging.getLogger("marketlens.oncall")
ALERT_ID = "dashboard-availability"
PROJECT = "marketlens-observability"
SERVICE = "db"
FINGERPRINT_RE = re.compile(r"^[a-f0-9]{8,64}$")
STARTS_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
STATE_VALUES = {"attempted", "recovered", "resolved"}


@dataclass(frozen=True)
class DatabaseState:
    project: str
    service: str
    status: str
    health: str


class RecoveryAdapter(Protocol):
    def inspect_database(self) -> DatabaseState: ...
    def remediate_database(self, action: str) -> bool: ...
    def wait_database_healthy(self) -> bool: ...
    def dashboard_healthy(self) -> bool: ...


def _event_key(event: dict[str, Any]) -> tuple[str, str] | None:
    if event.get("status") not in {"firing", "resolved", "repeated"}:
        return None
    fingerprint, starts_at = event.get("fingerprint"), event.get("startsAt")
    labels = event.get("labels")
    if not isinstance(fingerprint, str) or not FINGERPRINT_RE.fullmatch(fingerprint):
        return None
    if not isinstance(starts_at, str) or not STARTS_AT_RE.fullmatch(starts_at):
        return None
    if not isinstance(labels, dict) or any(labels.get(key) != value for key, value in {
        "alert_id": ALERT_ID, "journey": "dashboard", "http_route": "/api/dashboard",
        "http_request_method": "GET", "http_response_status_class": "5xx",
        "journey_outcome": "failure",
    }.items()):
        return None
    return fingerprint, starts_at


class OnCallAgent:
    """Handle allowlisted alerts with durable one-action state per alert key."""

    def __init__(
        self,
        recovery: RecoveryAdapter,
        audit=logger.info,
        state_path: Path | None = None,
    ) -> None:
        self.recovery = recovery
        self.audit = audit
        self.state_path = state_path or Path(__file__).resolve().parents[1] / ".oncall-agent-state.json"
        self._alert_states: dict[tuple[str, str], str] = {}
        self._state_failed = False
        self._load_state()

    def _load_state(self) -> None:
        try:
            if not self.state_path.exists():
                return
            if self.state_path.stat().st_size > 1_048_576:
                raise ValueError("state_file_too_large")
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("version") != 1 or not isinstance(payload.get("alerts"), list):
                raise ValueError("invalid_state_file")
            for record in payload["alerts"]:
                if not isinstance(record, dict) or set(record) != {"fingerprint", "startsAt", "state"}:
                    raise ValueError("invalid_state_record")
                key = (record["fingerprint"], record["startsAt"])
                if (
                    not isinstance(key[0], str) or not FINGERPRINT_RE.fullmatch(key[0])
                    or not isinstance(key[1], str) or not STARTS_AT_RE.fullmatch(key[1])
                    or record["state"] not in STATE_VALUES
                    or key in self._alert_states
                ):
                    raise ValueError("invalid_state_record")
                self._alert_states[key] = record["state"]
        except (OSError, UnicodeError, ValueError, TypeError):
            self._alert_states.clear()
            self._state_failed = True

    def _persist_state(self, key: tuple[str, str], state: str) -> bool:
        if self._state_failed or state not in STATE_VALUES:
            return False
        updated = dict(self._alert_states)
        updated[key] = state
        payload = {
            "version": 1,
            "alerts": [
                {"fingerprint": fingerprint, "startsAt": starts_at, "state": value}
                for (fingerprint, starts_at), value in sorted(updated.items())
            ],
        }
        temporary = self.state_path.with_name(self.state_path.name + ".tmp")
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8", newline="\n") as state_file:
                state_file.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
                state_file.flush()
                os.fsync(state_file.fileno())
            os.replace(temporary, self.state_path)
        except OSError:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            self._state_failed = True
            return False
        self._alert_states = updated
        return True

    def handle(self, event: dict[str, Any]) -> None:
        key = _event_key(event)
        if key is None:
            self.audit("oncall status=escalated reason=unapproved_alert")
            return
        status = event["status"]
        if self._state_failed:
            self.audit("oncall status=escalated reason=state_unavailable")
            return
        if status == "repeated":
            self.audit("oncall status=escalated reason=repeated_alert")
            return
        if status == "resolved":
            prior_state = self._alert_states.get(key)
            if prior_state == "resolved":
                self.audit("oncall status=duplicate_ignored")
            elif prior_state != "recovered":
                self.audit("oncall status=escalated reason=unverified_recovery")
            elif self.recovery.dashboard_healthy():
                if self._persist_state(key, "resolved"):
                    self.audit("oncall status=resolved_verified")
                else:
                    self.audit("oncall status=escalated reason=state_unavailable")
            else:
                self.audit("oncall status=escalated reason=dashboard_unhealthy")
            return
        if key in self._alert_states:
            self.audit("oncall status=escalated reason=repeated_alert")
            return
        if not self._persist_state(key, "attempted"):
            self.audit("oncall status=escalated reason=state_unavailable")
            return
        try:
            state = self.recovery.inspect_database()
        except Exception:
            self.audit("oncall status=escalated reason=database_inspection_failed")
            return
        if state.project != PROJECT or state.service != SERVICE:
            self.audit("oncall status=escalated reason=target_mismatch")
            return
        stopped = state.status in {"exited", "stopped"}
        unhealthy = state.status == "running" and state.health == "unhealthy"
        if not (stopped or unhealthy):
            self.audit("oncall status=escalated reason=database_not_recoverable")
            return
        action = "restart"
        try:
            acted = self.recovery.remediate_database(action)
            healthy = acted and self.recovery.wait_database_healthy()
            dashboard = healthy and self.recovery.dashboard_healthy()
        except Exception:
            dashboard = False
        if dashboard:
            if self._persist_state(key, "recovered"):
                self.audit(f"oncall status=recovered action={action} dashboard=healthy")
            else:
                self.audit("oncall status=escalated reason=state_unavailable")
        else:
            self.audit(f"oncall status=escalated reason=recovery_unverified action={action}")


class DockerComposeRecovery:
    """Adapter with fixed Compose project/file/service and no shell command input."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path(__file__).resolve().parents[1]).resolve()
        env_file = ".env.observability" if (self.root / ".env.observability").is_file() else ".env.observability.example"
        self.base = ["docker", "compose", "--project-name", PROJECT, "--env-file", env_file,
                     "-f", "compose.observability.yaml"]

    def _run(self, args: list[str]) -> str:
        result = subprocess.run(args, cwd=self.root, shell=False, capture_output=True,
                                text=True, timeout=10, check=False)
        if result.returncode != 0:
            raise RuntimeError("fixed_local_command_failed")
        return result.stdout.strip()

    def inspect_database(self) -> DatabaseState:
        container = self._run(self.base + ["ps", "--all", "-q", SERVICE]).splitlines()
        if len(container) != 1 or not re.fullmatch(r"[a-f0-9]{12,64}", container[0]):
            raise RuntimeError("database_container_not_unique")
        template = '{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}'
        fields = self._run(["docker", "inspect", "--format", template, container[0]]).split("|")
        if len(fields) != 4:
            raise RuntimeError("database_state_unavailable")
        return DatabaseState(*fields)

    def remediate_database(self, action: str) -> bool:
        if action != "restart":
            return False
        self._run(self.base + ["restart", SERVICE])
        return True

    def wait_database_healthy(self) -> bool:
        for attempt in range(10):
            try:
                state = self.inspect_database()
                if state.project == PROJECT and state.service == SERVICE and state.status == "running" and state.health == "healthy":
                    return True
            except Exception:
                pass
            if attempt < 9:
                time.sleep(2)
        return False

    def dashboard_healthy(self) -> bool:
        try:
            with urlopen("http://127.0.0.1:8001/api/dashboard", timeout=3) as response:
                return response.status == 200
        except (HTTPError, URLError, TimeoutError, OSError):
            return False


def poll_once(cursor: int, agent: OnCallAgent, endpoint: str = "http://127.0.0.1:8081/agent/events") -> int:
    """Read the receiver's sanitized feed. Poll transport failures never trigger actions."""
    try:
        with urlopen(f"{endpoint}?{urlencode({'after': cursor})}", timeout=3) as response:
            payload = json.loads(response.read())
        events, next_cursor = payload["events"], payload["cursor"]
        if not isinstance(events, list) or not isinstance(next_cursor, int) or next_cursor < 0:
            raise ValueError("invalid_event_feed")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
        logger.info("oncall status=waiting reason=event_feed_unavailable")
        return cursor
    for event in events:
        if isinstance(event, dict):
            agent.handle(event)
        else:
            logger.info("oncall status=escalated reason=invalid_event")
    return next_cursor


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logger.info("oncall status=ready feed=127.0.0.1:8081 project=%s service=%s", PROJECT, SERVICE)
    agent, cursor = OnCallAgent(DockerComposeRecovery()), 0
    while True:
        cursor = poll_once(cursor, agent)
        time.sleep(2)


if __name__ == "__main__":
    main()
