# Alerting: dashboard user-impact alerts

Run commands below from the repository root. Use only the isolated observability environment for controlled fault injection.

### Local dashboard availability alert (issue #39)

The local Grafana rule `Dashboard unavailable` evaluates every 10 seconds and fires when at least one dashboard HTTP 5xx is observed in the rolling previous minute. It resolves after a full minute without a dashboard failure. Alert math uses a dedicated low-cardinality failure counter because the trace-correlated request counter has one unique trace ID per series and cannot produce a meaningful rolling increase. The local demo exports metrics every 5 seconds for a responsive demonstration. Grafana sends firing and resolved notifications to an internal-only webhook in the isolated Compose network. The receiver retains only the alert state, static rule name/severity/journey, a validated trace ID if a future rule supplies one, and the Grafana fingerprint/start time; repeated deliveries for the same alert transition are idempotent. It drops annotations, URLs, arbitrary labels, request data, and credentials. Its webhook contract is a local hand-off surface that a later on-call responder can consume.

Start or rebuild the optional stack using the #38 commands above. Reproduce and recover without contacting external providers:

```powershell
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml stop db
curl.exe -i http://localhost:8001/api/dashboard
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml logs --since 2m alert-receiver
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml start db
curl.exe -i http://localhost:8001/api/dashboard
```

The stopped database produces HTTP 500; the alert receiver logs one redacted `firing` event. After PostgreSQL is healthy, the dashboard returns HTTP 200 and Grafana delivers `resolved` after the failure leaves the one-minute window. In Grafana **Alerting → Alert rules**, verify `Dashboard unavailable` returns to **Normal**. The delivery contains the alert fingerprint and static journey/route/status class. To find the corresponding trace, open Loki in Explore and query `{service_name="marketlens-api"} |= "dashboard_request"`; select the matching time and use its configured trace link to Tempo. The alert threshold, delivery and recovery tests are in `tests/test_alert_receiver.py`. Do not stop a database outside this isolated observability project.

Redacted local run evidence (same fingerprint for firing and recovery; repeated webhook posts produced no duplicate `alert_delivery` record):

```text
2026-10-25T19:35:15Z alert_delivery {"fingerprint":"0850647b23910719","labels":{"alert_id":"dashboard-availability","alertname":"Dashboard unavailable","http_request_method":"GET","http_response_status_class":"5xx","http_route":"/api/dashboard","journey":"dashboard","journey_outcome":"failure","severity":"critical"},"startsAt":"2026-10-25T19:34:40Z","status":"firing"}
2026-10-25T19:35:45Z alert_delivery {"fingerprint":"0850647b23910719","labels":{"alert_id":"dashboard-availability","alertname":"Dashboard unavailable","http_request_method":"GET","http_response_status_class":"5xx","http_route":"/api/dashboard","journey":"dashboard","journey_outcome":"failure","severity":"critical"},"startsAt":"2026-10-25T19:34:40Z","status":"resolved"}
```

#### Production alert in Grafana Cloud

The local alert above remains the safe fault-injection demo. For production, reuse the owner-managed Synthetic Monitoring check `marketlens-production-dashboard`; do not create a duplicate. The check should remain a public HTTP `GET` to `https://marketlens-dtc.onrender.com/api/dashboard`, accept only HTTP 200, run every 5 minutes from one European probe, and use a 60-second timeout. Render Free services can sleep after 15 minutes idle and take about one minute to wake, so a single timed-out probe is expected to be transient; the timeout plus the repeated-failure threshold below prevents one cold start from paging. Keep the existing frequency and probe count to avoid extra check executions.

In Grafana Cloud, open **Testing & synthetics → Synthetics → Checks**, edit the existing check, confirm its target/method/status/frequency/probe, set **Timeout** to 60 seconds, and save. Verify the `job` label is `marketlens-production-dashboard` and `instance` is the API URL in **Explore → Metrics** with `probe_success`. Grafana's Synthetic Monitoring labels use the configured job name as `job`, the target as `instance`, and the location as `probe` ([check metrics and labels](https://grafana.com/docs/grafana-cloud/observe-and-act/testing/synthetic-monitoring/create-checks/checks/)).

Create one **Grafana-managed** alert rule in the existing Grafana Cloud stack using its Prometheus/Mimir data source. Call it `MarketLensProductionDashboardUnavailable`; evaluate every **1 minute**, set the pending period to **1 minute**, and alert when query A is **above 0.5**. This query counts actual failed probe samples in a rolling 15-minute window (a success is 1, a failure is 0) and returns 0 while healthy, so a single Render cold-start miss does not fire:

```promql
(
  sum by (job, instance, probe) (
    count_over_time(probe_success{
      job="marketlens-production-dashboard",
      instance="https://marketlens-dtc.onrender.com/api/dashboard"
    }[15m])
    -
    sum_over_time(probe_success{
      job="marketlens-production-dashboard",
      instance="https://marketlens-dtc.onrender.com/api/dashboard"
    }[15m])
  )
) >= bool 2
```

If the `job` label in your check differs, use the exact value shown by `probe_success`; keep the URL filter exact. Add these rule labels: `service=marketlens`, `environment=production`, `source=synthetic`, and `severity=critical`. Set the summary annotation to `MarketLens production dashboard API is unavailable` and the description to `Synthetic check {{ $labels.job }} for {{ $labels.instance }} at probe {{ $labels.probe }} recorded at least 2 failures in 15m. Check its recent results in Synthetic Monitoring.` Do not include response bodies or other request data. Set **No data** and **Error** handling to **Keep last state**: probe failures are reported as `probe_success=0`, while missing check telemetry is a monitoring-pipeline issue to inspect separately. The rule resolves once fewer than two failed samples remain in the rolling window and the pending period clears.

For email delivery, go to **Alerts & IRM → Alerting → Notification configuration → Contact points** and create an **Email** contact point for your own address. Test it there. Then create a child notification policy matching `service=marketlens`, `environment=production`, and `source=synthetic`; select that email contact point, keep resolved notifications enabled, group by `alertname`, `job`, and `instance`, set group wait to **30 seconds**, group interval to **5 minutes**, and repeat interval to **4 hours**. Keep these labels stable so a future owner-managed webhook route can be added without changing the alert rule. Grafana Cloud provides email delivery without a self-managed SMTP server ([contact points](https://grafana.com/docs/grafana-cloud/alerting-and-irm/alerting/configure-notifications/manage-contact-points/), [email integration](https://grafana.com/docs/grafana-cloud/alerting-and-irm/alerting/configure-notifications/manage-contact-points/integrations/configure-email/), [notification policies](https://grafana.com/docs/grafana-cloud/observe-and-act/alert-and-measure-reliability/alerting/configure-notifications/create-notification-policy/)).

Validate without taking production down: (1) confirm the existing check is enabled and its latest result is green/HTTP 200; (2) send Grafana's test notification from the email contact point and confirm receipt; (3) create a temporary, clearly named `MarketLensNotificationRouteTest` rule using the same notification labels, PromQL `vector(1)`, and a condition above 0.5; confirm a firing email; change it to `vector(0)`, confirm a resolved email, then delete the temporary rule. This tests notification routing only; it is simulated evidence, not a real production outage. The real production threshold is passively verified from the existing check with `probe_success{job="marketlens-production-dashboard",instance="https://marketlens-dtc.onrender.com/api/dashboard"}`: healthy is 1; repeated check failure is 0. Render Free can take about one minute to wake ([Render Free services](https://render.com/docs/free)); do not inject a failure into Render or Neon. Grafana Cloud account configuration and email receipt must be verified by the owner; Codex has no account access.

