# MarketLens — Final Project Submission Evidence

**Prepared:** 2026-10-26  
**Repository:** https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens  
**Public demo:** https://marketlens-dtc.onrender.com/  
**Rubric checked:** [Official DataTalksClub AI Dev Tools Zoomcamp final-project criteria](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/project/README.md) (GitHub `main`, read 2026-10-26). The rubric has **12 criteria, 24 possible points; 10 points and three peer reviews are required to pass**. Final scores are determined by peer reviewers, not this document.

This is an **evidence index**, not a claim that every operation was independently re-tested on the submitted revision. Scores are **provisional targets based on documented implementation**, and limits are explicit below. Inspect the linked evidence before awarding points.

## Criterion-by-criterion evidence

| # | Criterion | Provisional target | Direct evidence | Status / limitation |
|---|---|---:|---|---|
| 1 | Problem Description | 2/2 | [README — problem](../README.md#the-problem), [MVP scope](../README.md#mvp-scope) | Documented target user, need, behavior and exclusions. |
| 2 | Product Specification | 2/2 | [Product plan](plan.md), [GitHub issues](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues), [backlog](backlog.md), [process](process.md) | Public tracker and acceptance/QA evidence; see completed [#22](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/22) and ongoing [#40](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/40). |
| 3 | Agent Team Specification | 2/2 | [Process](process.md), [team roles](team/), [agent instructions](../AGENTS.md) | Engineer, independent QA and orchestrator responsibilities documented; human alone closes issues. |
| 4 | Context Management | 2/2 | [AGENTS.md](../AGENTS.md), [process](process.md), [architecture](architecture.md), [team docs](team/) | Agent instructions point to modular documents. |
| 5 | Application | 2/2 | [Public demo](https://marketlens-dtc.onrender.com/), [frontend](../frontend/), [backend](../app/), [Docker quick start](../README.md#quick-start-with-docker-compose), [MVP acceptance #22](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/22) | Full-stack app with PostgreSQL persistence documented; a fresh clean-checkout run has **not been independently reproduced in this final audit**. |
| 6 | Testing | 2/2 | [Tests](../tests/), [integration tests](../tests/integration/), [run commands and test coverage](testing.md#automated-checks-and-test-coverage), [successful CI run](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/actions/runs/40382491149) | Backend/integration tests, frontend tests and frontend build passed in the cited CI run (2026-10-26). Check CI again after subsequent code commits. |
| 7 | Containerization | 2/2 | [Dockerfile](../Dockerfile), [Compose](../compose.yaml), [quick start](../README.md#quick-start-with-docker-compose), [deployment/Compose evidence #33–#36](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/36) | Documented single-command Compose startup; clean-checkout reproduction still recommended. |
| 8 | Deployment | 2/2 | [Live site](https://marketlens-dtc.onrender.com/), [Render deployment guide](deployment.md#render-deployment), [milestone evidence #36](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/36) | Public Render/Neon deployment owner-reported and previously accepted. Recheck current accessibility before submitting. |
| 9 | CI/CD | 2/3 | [GitHub workflow](../.github/workflows/ci.yml), [successful run](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/actions/runs/40382491149), [Render deployment guide](deployment.md#render-deployment) | GitHub Actions automated CI verified; Render automatic deploy after passing checks is documented/owner-reported. **No separate dev environment and manual promotion to production**; do not claim 3/3. Live Render deployment trigger not independently tested here. |
| 10 | Observability | 2/2 | [Local observability guide](observability.md#local-dashboard-observability-demo-issue-38), [Grafana Cloud export](observability.md#grafana-cloud-export-for-the-deployed-dashboard), [#38](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/38) | Dashboard journey has correlated telemetry and documented redacted success/failure evidence. Grafana account UI isn't publicly accessible; reviewer may rely on redacted evidence. |
| 11 | Alerting on User Impact | 1/1 | [Alert setup/evidence](alerting.md#local-dashboard-availability-alert-issue-39), [#39](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/39) | Local failure alert and production synthetic availability rule documented. Owner confirmed synthetic monitoring was enabled/healthy and Grafana test notification sent. |
| 12 | On-Call Agent | 2/2 **subject to reviewer acceptance** | [Local on-call runbook](oncall-agent.md#local-on-call-recovery-demo-issue-40), [issue #40 QA and evidence](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/40) | **Local isolated chain demonstrated:** controlled DB fault → real local Grafana alert → agent → one bounded Compose recovery → healthy dashboard. **Hosted Cloudflare extension is not accepted**: Grafana webhook reached Worker, but runtime logged `state_or_runtime_error`. Do not claim live hosted remediation; #40 stays open. |

**Provisional evidence-based total:** **23/24** *if* each linked criterion receives its target, including 2 points for the local on-call chain and 2 for CI/CD. This is **not a verified score**: the reviewer may award fewer points, especially for a clean local startup, hosted on-call expectations, and automatic delivery. The documented M1–M5 implementation alone supports a plausible passing margin, but passing is not guaranteed.

## Current independent checks and outstanding gaps

- [x] Repository is public and its issue history, instructions, docs and workflows are reviewable.
- [x] GitHub Actions [run #40382491149](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/actions/runs/40382491149) completed successfully on `main` (backend/integration tests, frontend tests, production build).
- [x] README includes product overview, architecture, quick-start, testing, deployment, observability and limitations.
- [ ] Recheck the **submitted SHA's** latest CI run, after any further merges or commits.
- [ ] Smoke-check live application homepage and `GET /api/dashboard` immediately before submission.
- [ ] From a clean checkout, reproduce `docker compose --env-file .env.compose up --build` and document result; if not possible, explicitly retain that limitation.
- [ ] Finish or transparently defer hosted agent #40; do not report its recovery action as proven while `state_or_runtime_error` remains unresolved.
- [ ] If hosted fixes merge, reconcile the hosted README runbook with this evidence index.
- [ ] Submit through [the course platform](https://courses.datatalks.club/ai-dev-tools-2026/) by its posted deadline.
- [ ] Complete **three required peer reviews** in the course's review window; the project does not pass without them.

## For reviewers

1. Start with the [live demo](https://marketlens-dtc.onrender.com/) and [README](../README.md).
2. Review the [product specification](plan.md), [agent process](process.md) and [AI usage report](ai-usage-report.md).
3. Inspect the [tests](../tests/), [GitHub Actions](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/actions) and [Compose quick start](../README.md#quick-start-with-docker-compose).
4. Follow [#38](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/38), [#39](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/39) and [#40](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/40) for operational evidence, QA feedback, and limitations. Provider keys and private Grafana/Render account access are intentionally not published.
