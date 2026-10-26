# Local on-call agent: isolated recovery demo

Run commands below from the repository root. This documents the QA-demonstrated **local** recovery workflow, not the unverified hosted Cloudflare extension.

### Local on-call recovery demo (issue #40)

This reuses only the optional `marketlens-observability` Compose stack. Keep the host agent running before fault injection so it detects the real Grafana event automatically. The receiver feed is published on loopback only (`127.0.0.1:8081`); it exposes sanitized alert events, never a command endpoint.

In terminal 1, start the isolated stack as above and run the host agent from the repository root:

```powershell
uv run python -m app.oncall_agent
```

Wait for `oncall status=ready`. In terminal 2, create the approved isolated fault and inspect the dashboard:

```powershell
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml stop db
curl.exe -i http://127.0.0.1:8001/api/dashboard
```

Grafana's real dashboard availability notification reaches the receiver; the agent reads the sanitized event feed, verifies the fixed project/service labels and that the DB is stopped or running unhealthy, then runs the same single action in either case: `docker compose ... restart db`. Compose restart was verified to start the stopped isolated DB. The agent checks the DB health and polls `/api/dashboard` for HTTP 200 before logging `oncall status=recovered`. Grafana later sends `resolved`; the agent rechecks the dashboard before logging `resolved_verified`. Keep the agent process running through recovery and resolution. The agent writes only the validated alert fingerprint, start time, and state (`attempted`, `recovered`, or `resolved`) to an atomically replaced, gitignored `.oncall-agent-state.json` file. On restart, replayed firing alerts escalate without another action; resolved alerts are acknowledged only when a prior recovery was recorded and the dashboard is currently healthy. Missing/corrupt state, unknown alerts, a healthy DB, duplicate events, or failed verification produce an escalation with no retry. It does not connect to Render or providers, accept shell input, or access any other Compose project. Audit output contains only allowlisted status/action values and no request or database payloads.

The receiver's GET `/agent/events?after=N` endpoint is read-only and returns only its redacted delivery registry. The first repeated firing delivery adds one redacted `repeated` feed event; the poller explicitly escalates it as `oncall status=escalated reason=repeated_alert` without taking a second action. Further repeats of that same firing are coalesced. Tests cover the single fixed-target restart for stopped and unhealthy states, durable replay across agent restarts, end-to-end receiver/feed/poller wake-up, unexpected labels, already-healthy state, repeated alerts, and failed health/dashboard verification. The real end-to-end chain requires Docker and the optional local observability stack; verify the firing and resolved `oncall` records in the terminal and the alert state under Grafana **Alerting → Alert rules**. Never stop a database outside this isolated project.

Redacted automatic recovery evidence (2026-10-25 UTC; one allowed `restart db`, no duplicate action):

```text
20:08:40Z  dashboard fault injected only by stopping marketlens-observability/db; /api/dashboard returned HTTP 500
20:09:14Z  alert_delivery status=firing fingerprint=0850647b23910719
20:09:24Z  oncall status=recovered action=restart dashboard=healthy; marketlens-observability/db healthy; /api/dashboard returned HTTP 200
20:09:44Z  alert_delivery status=resolved fingerprint=0850647b23910719
20:09:46Z  oncall status=resolved_verified
```

