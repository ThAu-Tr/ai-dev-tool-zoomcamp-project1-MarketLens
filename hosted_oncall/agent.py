"""Bounded recovery policy shared by the Cloudflare worker and its local tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class RecoveryAdapter(Protocol):
    async def dashboard_healthy(self) -> bool | None: ...
    async def database_ready(self) -> int | None: ...
    async def render_preflight(self) -> str: ...
    async def restart_service(self) -> bool: ...
    async def wait(self, seconds: float) -> None: ...


@dataclass(frozen=True)
class PolicyResult:
    reason: str
    restart_permitted: bool = False


class HostedOnCallPolicy:
    """Only restart after sustained app failure with DB and Render checks healthy."""

    COLD_START_GRACE_SECONDS = 70
    VERIFY_DELAYS_SECONDS = (0, 10, 20, 30, 30)

    def __init__(self, adapter: RecoveryAdapter) -> None:
        self.adapter = adapter

    async def preflight(self) -> PolicyResult:
        dashboard = await self.adapter.dashboard_healthy()
        if dashboard is True:
            return PolicyResult("already_healthy")
        if dashboard is None:
            return PolicyResult("dashboard_probe_unknown")
        if dashboard is not False:
            return PolicyResult("dashboard_failure_not_server_error")

        readiness = await self.adapter.database_ready()
        if readiness == 503:
            return PolicyResult("database_unavailable")
        if readiness != 200:
            return PolicyResult("readiness_unknown")

        # A public request wakes a Render Free service. Allow its documented
        # cold-start window before considering the one restart action.
        await self.adapter.wait(self.COLD_START_GRACE_SECONDS)
        dashboard = await self.adapter.dashboard_healthy()
        if dashboard is True:
            return PolicyResult("cold_start_recovered")
        if dashboard is None:
            return PolicyResult("dashboard_probe_unknown")
        if dashboard is not False:
            return PolicyResult("dashboard_failure_not_server_error")

        readiness = await self.adapter.database_ready()
        if readiness == 503:
            return PolicyResult("database_unavailable")
        if readiness != 200:
            return PolicyResult("readiness_unknown")

        render_state = await self.adapter.render_preflight()
        if render_state != "ready":
            return PolicyResult(render_state)
        return PolicyResult("recoverable_application_failure", restart_permitted=True)

    async def verify_recovery(self) -> str:
        for delay in self.VERIFY_DELAYS_SECONDS:
            if delay:
                await self.adapter.wait(delay)
            readiness = await self.adapter.database_ready()
            if readiness == 503:
                return "database_unavailable_after_restart"
            if readiness != 200:
                continue
            if await self.adapter.dashboard_healthy() is True:
                return "recovered"
        return "recovery_unverified"

    async def run(self, mark_attempted) -> str:
        """Persist the one-action boundary before making the external API call."""
        decision = await self.preflight()
        if not decision.restart_permitted:
            return decision.reason
        # Durable caller records attempted before POST; if it fails, do not
        # attempt again because the request outcome may be ambiguous.
        if not mark_attempted():
            return "state_unavailable"
        try:
            accepted = await self.adapter.restart_service()
        except Exception:
            return "restart_outcome_unknown"
        if not accepted:
            return "restart_rejected"
        return await self.verify_recovery()


async def process_claimed_incident(ledger, work: dict[str, str], adapter: RecoveryAdapter) -> tuple[str, str]:
    """Run one durable claim; separate from Workers bindings for deterministic tests."""
    key = work["incident_key"]
    if work["status"] == "resolving":
        readiness = await adapter.database_ready()
        dashboard_ok = readiness == 200 and await adapter.dashboard_healthy() is True
        reason = "resolved_verified" if dashboard_ok else "unverified_resolution"
        status = "resolved" if dashboard_ok else "escalated"
        ledger.transition(key, status, reason)
        return status, reason

    policy = HostedOnCallPolicy(adapter)
    outcome = await policy.run(lambda: ledger.transition(key, "attempted", "single_restart_boundary"))
    if outcome == "recovered":
        status = "recovered"
        ledger.transition(key, status, "dashboard_and_database_ready")
    elif outcome in {"already_healthy", "cold_start_recovered"}:
        status = "no_action"
        ledger.transition(key, status, outcome)
    else:
        status = "escalated"
        ledger.transition(key, status, outcome)
    return status, outcome
