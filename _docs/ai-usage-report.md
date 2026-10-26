# AI-Assisted Development Evidence

## Development approach: ChatGPT planning and Codex implementation

I used ChatGPT to identify and groom the GitHub issues I considered useful to implement next. Before assigning work to Codex, I refined each issue's scope, dependencies and acceptance criteria, and considered which tasks could proceed independently. This separated planning from implementation: Codex could focus on delivering well-defined changes and independent QA rather than repeatedly spending its limited usage allowance on issue discovery and grooming. Where dependencies allowed, I organized multiple issues for parallel work in isolated worktrees. I still reviewed the proposed tasks, decided what to prioritize, and manually accepted completed changes.

The goal was to use the available Codex allowance more efficiently, not to claim measured token savings. The implementation workflow and agent roles are documented separately in [process.md](process.md); that historical process file is left unchanged.

## Evidence in this report

The examples below document representative planning, implementation, QA and operational work rather than every AI conversation or GitHub issue.

---

## Codex Model & Usage Comparison

The following table records the models, reasoning settings and approximate five-hour Codex allowance consumed in selected implementation sessions. I tracked these sessions to compare practical usage while experimenting with parallel issue execution and different model configurations; they are observations from different tasks, not controlled measurements of model efficiency.

| Issues | Model | Reasoning effort | 5-hour usage | Notes |
| --- | --- | --- | --- | --- |
| #6, #7 | GPT-5.6 Terra | Medium | 86% | Combined session; included PM, engineering, and QA |
| #8 | GPT-5,6 Luna | Medium | 8% | Engineering and QA |
| #5, #9 | GPT-5.6 Luna | Medium | 25% | Combined parallel implementation; engineering and QA |
| #4, #10 | GPT-5.6 Terra | Medium | 85% | Combined parallel implementation; engineering and QA |
| #11, #14 | GPT-6 Luna | Medium | 15% | Parallel implementation, engineering and QA |
| #12 | GPT-6 Luna | Medium | 10% | Implementation and QA using "Approve for me" mode |
| #13 | GPT-6.1 Sol | Medium | 81% | Implementation, QA, and live OpenAI smoke test using "Approve for me" mode |

Usage percentages reflect the reported share of the five-hour Codex allowance for each session, **not per-issue costs or measured token counts**. Tasks differed in complexity, and the Terra session also included PM work, so the figures are not a controlled model benchmark.

---

# Representative Examples

## 1. Planning / Prototype

### Task / Issue

**Task:** Define the simplified MarketLens MVP, validate the mock frontend, and derive the HTTP contract.
**Issue:** Planning work completed before the GitHub implementation backlog.

### AI Workflow

- PM: Not used as a separate role for this early planning activity; the user and assistant refined the scope together.
- SWE: Examined the mocked frontend client to identify backend operations and wrote the initial OpenAPI contract.
- QA: Audited frontend interactions against the contract and identified the missing asset-catalogue lookup before the backlog was finalized.
- Other: The user selected the simplified React → FastAPI → PostgreSQL architecture and reviewed the resulting product and architecture documents.

### What Happened

The prototype made the intended flows concrete and exposed that adding an asset required a valid catalogue-selection endpoint rather than free text. The contract gained `GET /api/assets/search`, and the refined backlog was split into small, vertical MVP issues.

### Human Review

The user chose the simplified architecture, confirmed the MVP boundaries, and requested the refined backlog structure. The product plan, architecture, frontend specification, and OpenAPI contract were reviewed before implementation issues were created.

### Result

- [x] Passed first QA cycle
- [ ] Required revision
- [x] Merged / completed
- [ ] Other:

---

## 2. MVP Implementation

### Task / Issue

**Task:** View the stored dashboard through the real API.
**Issue:** [#1 — View the stored dashboard](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/1)

### AI Workflow

- PM: Groomed the feature into explicit API, empty-state, error-state, and provider-isolation acceptance criteria.
- SWE: Added the FastAPI dashboard read path, migrations, React API integration, and automated tests.
- QA: Found an OpenAPI serialization mismatch and insufficient proof that dashboard reads make no provider calls, then re-tested the correction.
- Other: The user approved the minimal backend and frontend testing dependencies needed to meet the agreed acceptance criteria.

### What Happened

The first implementation passed basic checks but failed independent QA because lot decimals did not match the OpenAPI schema, an empty refresh timestamp was nullable, and frontend/provider-isolation coverage was missing. The correction aligned serialization, injected a failing provider boundary to prove zero calls, and added dashboard UI/API tests.

### Human Review

The user approved the limited dependency additions after the gap was explained. The final QA report and passing test results were reviewed before the issue was closed.

### Result

- [ ] Passed first QA cycle
- [x] Required revision
- [x] Merged / completed
- [ ] Other:

---

## 3. MVP Implementation

### Task / Issue

**Task:** Search the supported asset catalogue before adding an asset.
**Issue:** [#2 — Search the supported asset catalogue](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/2)

### AI Workflow

- PM: Defined provider-free, deterministic search behavior and validation/error states.
- SWE: Implemented the local catalogue search service, centralized frontend client, result selection, and automated tests.
- QA: Independently verified case-insensitive matching, duplicate filtering, invalid queries, stale-result handling, and no watchlist mutation.
- Other: The user reviewed the progress and authorized continuation after the initial engineer session encountered a service limit.

### What Happened

The feature was implemented as a vertical slice without adding external-provider calls or new dependencies. Independent QA passed the API contract, no-match and validation states, frontend loading/error/selection behavior, and test suite.

### Human Review

The user approved the issue criteria and continuation. The feature was closed only after the QA PASS report and passing backend, frontend, and production-build checks.

### Result

- [x] Passed first QA cycle
- [ ] Required revision
- [x] Merged / completed
- [ ] Other:

---

## 4. Deployment / DevOps

### Task / Issue

**Task:** Add production dashboard observability, alerting and a bounded on-call recovery workflow.  
**Issues:** [#38 — Production observability](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/38), [#39 — Production alerting](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/39), [#40 — Hosted on-call responder](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/40).

### AI Workflow and Human Review

The issue history documents iterative implementation, independent QA feedback and owner-side setup/verification. The locally isolated Grafana → alert receiver → on-call agent → Docker database restart → healthy dashboard chain was independently QA-reviewed. The owner configured the hosted Cloudflare Worker and Grafana Cloud webhook integration separately rather than handing provider credentials to Codex. During live hosted acceptance, webhook requests arrived but the Worker logged `state_or_runtime_error`; this remains an **open blocker** on #40, not a production recovery PASS.

### Result

- [x] Local on-call flow has historical QA evidence in #40
- [x] Production monitoring and alerting are documented in #38 and #39
- [ ] Hosted Cloudflare recovery accepted — **not yet verified; issue #40 remains open**

Evidence: [Issue #40 and its QA discussion](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/40), [on-call runbook](../README.md#local-on-call-recovery-demo-issue-40), and [CI runs](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/actions).

---

## 5. Optional Extension

No separate optional extension evidence is claimed here; relevant post-MVP requests remain open in the [GitHub backlog](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues?q=is%3Aopen+label%3Apost-MVP).
