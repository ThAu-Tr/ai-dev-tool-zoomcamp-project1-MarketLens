# AI-Assisted Development Evidence

## Purpose

This document contains a small number of representative examples showing how AI was used during development.

Do not document every prompt or every issue. Aim for approximately 4–6 useful examples across the full project.

## Codex Model & Usage Comparison

| Issues | Model | Reasoning effort | 5-hour usage | Notes |
| --- | --- | --- | --- | --- |
| #6, #7 | Terra | Medium | 86% | Combined session; included PM, engineering, and QA |
| #8 | Luna | Medium | 8% | Engineering and QA |
| #5, #9 | Luna | Medium | 25% | Combined parallel implementation; engineering and QA |

Usage percentages reflect the reported share of the five-hour Codex allowance for each session, **not per-issue costs or measured token counts**. Tasks differed in complexity, and the Terra session also included PM work, so the figures are not a controlled model benchmark.

---

---

## Example Template

### Task / Issue

**Task:**
**Issue:**

### AI Workflow

Which AI roles or tools were used?

- PM:
- SWE:
- QA:
- Other:

### What Happened

Short summary of the useful interaction, correction or iteration.

### Human Review

What did you manually review, change, reject or approve?

### Result

- [ ] Passed first QA cycle
- [ ] Required revision
- [ ] Merged / completed
- [ ] Other:

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

Not yet applicable. This example will be added during the productionization phase.

---

## 5. Optional Extension

Not yet applicable.
