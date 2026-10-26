"""Cloudflare Python Worker and SQLite-backed Durable Object entry points."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlparse

from workers import DurableObject, Response, WorkerEntrypoint

from agent import process_claimed_incident
from ledger import SQLiteIncidentLedger
from receiver import MAX_BODY_BYTES, NotificationError, receive_notification
from render import RenderRecoveryAdapter

logger = logging.getLogger("marketlens.hosted_oncall")
SIGNATURE_HEADER = "x-grafana-alerting-signature"
TIMESTAMP_HEADER = "x-grafana-alerting-timestamp"


async def _fetch_request(method: str, url: str, *, headers: dict[str, str], timeout: int, body: str | None = None):
    """Call the Workers Fetch API; no host sockets or subprocesses are used."""
    from js import AbortSignal, fetch

    options: dict[str, Any] = {"method": method, "headers": headers, "signal": AbortSignal.timeout(timeout * 1000)}
    if body is not None:
        options["body"] = body
    response = await fetch(url, options)
    response_text = await response.text()
    return int(response.status), response_text.encode("utf-8")


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        parsed = urlparse(request.url)
        if parsed.path != "/webhook":
            return Response("Not found", status=404)
        if request.method != "POST":
            return Response("Method not allowed", status=405)
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            return Response("Unsupported media type", status=415)
        try:
            declared_length = request.headers.get("content-length")
            if declared_length is not None:
                try:
                    if int(declared_length) > MAX_BODY_BYTES or int(declared_length) < 0:
                        raise NotificationError("invalid_payload_size")
                except ValueError as error:
                    raise NotificationError("invalid_payload_size") from error
            raw_body = (await request.text()).encode("utf-8")
            secret = self.env.GRAFANA_HMAC_SECRET
            dashboard_url = self.env.MARKETLENS_DASHBOARD_URL
            namespace = self.env.INCIDENTS
            stub = namespace.get(namespace.idFromName("marketlens-production-oncall"))
            accepted = await receive_notification(
                raw_body,
                signature=request.headers.get(SIGNATURE_HEADER),
                timestamp=request.headers.get(TIMESTAMP_HEADER),
                secret=secret,
                dashboard_url=dashboard_url,
                submit_events=stub.accept_events,
            )
            return Response.json({"accepted": accepted}, status=202)
        except NotificationError as error:
            logger.info("webhook rejected reason=%s", str(error))
            return Response("Rejected", status=401 if str(error) in {"invalid_signature", "invalid_timestamp", "stale_timestamp", "webhook_auth_unavailable"} else 400)
        except Exception:
            # Never log request headers, payload, API response bodies, or secrets.
            logger.error("webhook unavailable reason=state_or_runtime_error")
            return Response("Temporarily unavailable", status=503)


class Incidents(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.ledger = SQLiteIncidentLedger(ctx.storage.sql)

    async def accept_events(self, events: list[dict[str, Any]]) -> int:
        accepted = 0
        for event in events:
            outcome = self.ledger.submit(event)
            if outcome == "queued":
                accepted += 1
        # Schedule even for duplicates: an earlier alarm may have been lost
        # after durable submission but before it was registered.
        await self.ctx.storage.set_alarm(int(time.time() * 1000) + 1000)
        return accepted

    async def alarm(self):
        # A retry after a crash must never repeat an ambiguous restart request.
        self.ledger.fail_interrupted_work()
        work = self.ledger.claim_next()
        if work is None:
            return
        adapter = self._adapter()
        status, outcome = await process_claimed_incident(self.ledger, work, adapter)
        self._emit_audit(status, outcome)

        # Process one event at a time; each action is bounded and the next
        # pending event remains durable if this alarm is interrupted.
        next_work = self.ledger._one("SELECT incident_key FROM incidents WHERE status IN ('pending', 'resolved_pending') LIMIT 1")
        if next_work is not None:
            await self.ctx.storage.set_alarm(int(time.time() * 1000) + 1000)

    def _adapter(self):
        async def request(method: str, url: str, *, headers: dict[str, str], timeout: int):
            return await _fetch_request(method, url, headers=headers, timeout=timeout)

        return RenderRecoveryAdapter(
            request=request,
            api_key=self.env.RENDER_API_KEY,
            service_id=self.env.RENDER_SERVICE_ID,
            dashboard_url=self.env.MARKETLENS_DASHBOARD_URL,
        )

    @staticmethod
    def _emit_audit(status: str, reason: str) -> None:
        # The ledger is the durable audit; runtime logs are a redacted operator view.
        logger.info("oncall status=%s reason=%s", status, reason)
