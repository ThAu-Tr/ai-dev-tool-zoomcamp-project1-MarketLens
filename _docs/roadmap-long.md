# DTC Final Project Roadmap

## Goal

Build the final project as one integrated workflow combining the course modules rather than treating each week separately.

Overall flow:

**Define → Prototype → Plan → Implement → Deploy → Operate → Extend**

The project should maximize rubric coverage while keeping unnecessary work low.

---

# Phase 1 — MVP Definition & Technical Blueprint

## 1. Define the product

- [X] Discuss the app idea with an LLM.
- [X] Define the target user.
- [X] Define the problem the app solves.
- [X] Define the main user workflow.
- [X] Define the smallest useful MVP.
- [X] Explicitly define what is out of scope.
- [X] Reduce features if the MVP becomes too large.

### Output
- `_docs/plan.md` or equivalent product specification

### Milestone
**M1 — MVP scope is clear enough that no major product decisions are required before prototyping.**

---

## 2. Define the technical architecture

- [X] Choose the frontend technology.
- [X] Choose the backend technology.
- [X] Choose the database technology.
- [X] Decide how frontend and backend communicate.
- [X] Decide how configuration will differ between development, test and production.
- [X] Document the architecture at a high level.
- [X] Keep the architecture as simple as possible.

Expected general structure:

```text
Frontend
   ↓
OpenAPI / HTTP API
   ↓
Backend
   ↓
Database
```

### Output
- `_docs/architecture.md`
- Selected technology stack

### Rubric coverage
- Problem description
- Technologies and system architecture

---

## 3. Set up the AI-assisted development workflow

Use the Week 1 workflow as the development process for the whole project.

- [X] Create `AGENTS.md`.
- [X] Define the PM role.
- [X] Define the Software Engineer role.
- [X] Define the QA role.
- [X] Define the general development process.

Expected workflow:

```text
Issue
  ↓
PM
  ↓
SWE
  ↓
QA
  ├── PASS → Done
  └── FAIL → SWE
```

Do not over-engineer the agent setup at this point.

### Output
Possible files:

```text
AGENTS.md
_docs/process.md
_docs/team/pm.md
_docs/team/swe.md
_docs/team/qa.md
```

### Rubric coverage
- AI-assisted development workflow

---

## 4. Create the mock frontend

Use the product specification to build the application UI before implementing the real backend.

- [X] Generate the basic frontend.
- [X] Implement the main user flows.
- [X] Use mocked data or mocked service calls.
- [X] Make sure all core MVP actions can be demonstrated.
- [X] Interact with the frontend yourself.
- [X] Identify awkward or unnecessary functionality.
- [X] Simplify the MVP if necessary.
- [X] Update `plan.md` if the prototype changes the product definition.

The frontend at this point is a **prototype**, not necessarily the final production frontend.

### Output
- Working mock frontend
- Revised product specification if necessary

### Milestone
**M2 — The MVP can be demonstrated through the frontend using mocked data.**

---

## 5. Define the API contract

Use the validated frontend to determine what the backend actually needs to provide.

- [X] Identify frontend operations requiring backend calls.
- [X] Define endpoints.
- [X] Define request formats.
- [X] Define response formats.
- [X] Define validation/error responses.
- [X] Create or generate the OpenAPI specification.
- [X] Check that every core frontend interaction has an API equivalent.

### Output
- `openapi.yaml`, generated OpenAPI documentation or equivalent API contract

### Rubric coverage
- API contract

---

## 6. Create the real MVP implementation backlog

Only now create the detailed MVP backlog.

Base it on:

```text
Product specification
+
Validated frontend
+
Architecture
+
OpenAPI contract
```

Backlog items should describe **features or behaviors**, not technical layers.

Avoid:

```text
Build frontend
Build backend
Build database
```

Prefer:

```text
Create expense
View expenses
Delete expense
Split expense
```

Each feature may span:

```text
UI → API → backend logic → persistence → tests
```

- [X] Generate proposed backlog items.
- [X] Review them manually.
- [X] Remove unnecessary tasks.
- [X] Split tasks that are too large.
- [X] Merge tasks that are unnecessarily small.
- [X] Check that every MVP feature is represented.
- [X] Add required technical tasks that are not feature-specific.
- [X] Move the final backlog to GitHub Issues.

### Output
- Final MVP backlog
- GitHub Issues

### Milestone
**M3 — The MVP is fully represented by a small, executable backlog.**

---

# Phase 2 — MVP Implementation

## 7. Implement features vertically

Work through the backlog issue by issue.

For each important feature:

- [X] PM grooms the issue.
- [X] PM defines the goal.
- [X] PM defines acceptance criteria.
- [X] PM defines out-of-scope behavior where necessary.
- [X] SWE implements the feature.
- [X] SWE adds appropriate tests.
- [X] QA checks the acceptance criteria.
- [X] QA returns PASS or FAIL.
- [X] If FAIL, return the issue to SWE.
- [X] Human-review the important changes.
- [X] Merge/close the issue when accepted.

Each feature should ideally cover all necessary layers:

```text
Frontend
↓
API
↓
Backend
↓
Database
```

Do not artificially separate development into frontend/backend/database phases.

---

## 8. Add database persistence

As features require persistence:

- [X] Implement the database schema.
- [X] Connect backend operations to the database.
- [X] Add database setup instructions.
- [X] Use configurable connection settings.
- [X] Separate development/test/production configuration where appropriate.
- [X] Avoid hardcoding environment-specific database URLs.
- [X] Document migrations or initialization if relevant.

### Output
- Working persistent database layer
- Environment-aware database configuration

### Rubric coverage
- Database integration

---

## 9. Add automated tests during development

Do not postpone testing until the end.

For relevant features:

- [X] Add backend unit tests.
- [X] Add frontend/component tests where useful.
- [X] Test validation and failure cases.
- [X] Keep tests runnable locally.
- [X] Maintain a passing test suite. (`uv run pytest` — 140 passed, 0 failed; the #29 AI-context test fixtures now use observations inside the production evidence window.)

Focus effort on important behavior rather than maximizing test count.

---

## 10. Add explicit integration tests

Once the main system works end-to-end:

- [X] Identify the 1–3 most important user workflows.
- [X] Create integration tests for those workflows.
- [X] Clearly separate integration tests from unit/component tests.
- [X] Ensure tests exercise multiple system components.
- [X] Document how integration tests are run.

Example:

```text
Request
↓
API
↓
Backend
↓
Database
↓
Response
```

### Output
- Separate integration-test suite
- Test instructions

### Rubric coverage
- Integration testing

### Milestone
**M4 — The full MVP works locally with persistence and automated tests.**

---

# Phase 3 — Productionization & Delivery

## 11. Containerize the application

- [X] Create the required Dockerfile(s).
- [X] Make sure the application runs in containers.
- [X] Add Docker Compose only if useful.
- [X] Move configuration into environment variables.
- [X] Verify the complete app starts from a clean environment.
- [X] Document container startup.

### Output
- Dockerfile(s)
- Optional `docker-compose.yml`
- Container run instructions

### Rubric coverage
- Containerization

---

## 12. Set up CI

- [X] Create the CI workflow.
- [X] Install dependencies automatically.
- [X] Run relevant tests automatically.
- [X] Make CI fail when tests fail.
- [X] Keep the pipeline minimal.

### Output
- GitHub Actions workflow or equivalent

### Rubric coverage
- CI/CD pipeline

---

## 13. Deploy the application

- [X] Choose the simplest acceptable hosting solution.
- [X] Configure the production environment.
- [X] Configure the production database if different.
- [X] Deploy the application.
- [X] Verify the deployed frontend.
- [X] Verify the deployed API.
- [X] Verify persistence.
- [X] Verify the main user workflow.
- [X] Add the public URL to the README.

### Output
- Publicly accessible application

### Rubric coverage
- Deployment

---

## 14. Add CD where useful

- [X] Configure deployment after successful CI.
- [X] Avoid automatic deployment if tests fail.
- [X] Document how deployment works.
- [X] Keep the pipeline as simple as possible.

### Output
- Automated or clearly documented deployment pipeline

### Milestone
**M5 — A tested, containerized version of the MVP is publicly deployed.**

---

# Phase 4 — Observability & User-Impact Alerting

## Current rubric and scope

This future work targets the [final-project rubric](https://raw.githubusercontent.com/DataTalksClub/ai-dev-tools-zoomcamp/main/project/README.md) checked on **2026-10-25**: 12 criteria, 24 available points, and a passing submission requires **at least 10 points plus three completed peer reviews**. Recheck the current rubric before submission.

M6–M8 below are roadmap targets, not claims of delivered evidence. Existing M1–M5 evidence is expected to exceed the passing score; confirm that assessment in M8 before spending effort on additional points. M6 targets criteria 10–11 (up to 3 points), and M7 targets criterion 12 (up to 2 points). Neither is a prerequisite for passing if the other evidenced criteria already reach 10 points. Security scans and generic agent extension packs are not separate criteria in this rubric.

Keep all work within the existing MVP and React → FastAPI → PostgreSQL architecture. Prefer one existing dashboard journey and small operational changes. Choose tools during grooming; request approval before adding, removing or upgrading dependencies. This roadmap does not authorize production changes.

## 15. Observe a key user journey

Criterion 10 awards 1 point for logging and 2 points for key user journeys covered by metrics, traces and structured logs, with telemetry collected, stored and viewable in a UI.

- [ ] Select and document one key journey, such as loading the stored watchlist/dashboard through the frontend, API and database.
- [ ] Capture journey success/failure and latency metrics, traces, and structured logs correlated by a shared trace ID.
- [ ] Collect and store the telemetry and demonstrate how to inspect it in a UI.
- [ ] Exclude customer data and credentials from telemetry; do not record portfolio payloads, article contents, API keys or other secrets.
- [ ] Demonstrate diagnosis of a controlled failure in an isolated dev/demo environment using the correlated telemetry.
- [ ] Add deterministic tests for important instrumentation and redaction behavior, using fake external providers and no live market, news or AI calls.

### Output
- Documented journey and telemetry fields, retention/access settings and UI inspection instructions
- Redacted evidence connecting metrics, traces and logs for one success and one controlled failure

### Rubric coverage
- Criterion 10 — Observability (target: 2/2)

---

## 16. Alert on user impact

Criterion 11 awards 1 point for at least one alert on user impact. These are operational alerts, not price notifications or investment recommendations.

- [ ] Define one actionable alert on the selected journey, with a documented failure/latency threshold, evaluation window and recovery condition.
- [ ] Configure an actual alert delivery path and record enough redacted context to diagnose the affected journey.
- [ ] Trigger the alert with a reproducible fault in an isolated dev/demo environment; do not interrupt the public application or consume live provider services.
- [ ] Remove the fault and verify the user journey and alert return to a healthy state.
- [ ] Test alert trigger, delivery, recovery and duplicate handling deterministically.
- [ ] Record the alert rule, delivered alert and recovery evidence; obtain QA verification and human acceptance through the existing process.

### Output
- One working user-impact alert and a safe trigger/recovery runbook
- Redacted alert delivery and verified recovery evidence

### Rubric coverage
- Criterion 11 — Alerting on User Impact (target: 1/1)

### Milestone
**M6 — One key MVP journey has inspectable, correlated telemetry and a demonstrated user-impact alert with verified recovery.**

---

# Phase 5 — Alert-Triggered On-Call Agent

## 17. Remediate one bounded operational failure

Criterion 12 awards 2 points when an agent wakes on an alert and fixes the issue. Development-role documentation, a reusable skill, an MCP server or notification-only triage does not demonstrate this behavior.

Confirm evidence already meets the passing threshold before pursuing this additional score; finalize submission checks in M8. Reuse M6's alert and isolated dev/demo journey; do not add product features or a general-purpose autonomous operations platform.

- [ ] Groom one recoverable operational failure and a specific remediation that restores the selected journey.
- [ ] Connect the actual alert delivery to an agent wake-up, passing only redacted diagnostic context.
- [ ] Define the agent's allowed actions, limited credentials, retry/time limits, duplicate handling, audit trail and escalation behavior.
- [ ] Restrict autonomous remediation to the isolated dev/demo environment; exclude production access, destructive database actions, arbitrary shell execution and unrestricted provider calls.
- [ ] Implement the bounded remediation and independently verify journey recovery; acknowledge success only after the health/journey check passes.
- [ ] On unsupported failures, exhausted retries or failed verification, stop and escalate for human intervention.
- [ ] Add deterministic tests for alert-triggered wake-up, successful remediation, failed recovery, duplicate alerts and permission boundaries, using fake external providers.
- [ ] Demonstrate the complete chain: controlled fault → user-impact alert → agent wake-up → remediation → verified recovery.
- [ ] Record redacted evidence and obtain QA verification and human acceptance through the existing process.

### Output
- Alert-triggered on-call agent with a documented, bounded remediation and permissions
- Reproducible isolated fault/remediation runbook, deterministic test results and recovery evidence

### Rubric coverage
- Criterion 12 — On-Call Agent (target: 2/2)

### Milestone
**M7 — An actual alert wakes the on-call agent, which fixes one bounded operational issue and verifies recovery in an isolated environment.**

---

# Cross-Cutting Documentation & Evidence

Documentation should be systematic but lightweight.

Do **not** document every prompt, conversation or implementation decision.

Use two levels of documentation.

---

## A. Small AI workflow evidence entries

For a few representative tasks across the project, record:

- [ ] Task / issue
- [ ] Which AI roles or tools were used
- [ ] What important result/correction occurred
- [ ] What you manually reviewed
- [ ] Final result

Example format:

```text
Issue #7 — Create expense

PM refined the scope and acceptance criteria.
SWE implemented the UI/API/database changes.
QA identified a validation bug.
I reviewed the fix and accepted the final behavior.

Result: passed after second QA cycle.
```

Target approximately **4–6 good examples across the entire project**, not every issue.

Good moments to capture:

- one planning/prototyping example
- two or three MVP implementation examples
- one deployment/DevOps example
- optionally one alert-triggered on-call remediation example

### Output
- `_docs/ai-usage-report.md`

### Rubric coverage
- AI-assisted development workflow

---

## B. Documentation checkpoint after every major phase

### After Phase 1

- [X] Update problem description.
- [X] Update MVP scope.
- [X] Update architecture.
- [X] Reference OpenAPI.
- [X] Add one useful AI workflow example.

### After Phase 2

- [X] Update implemented-feature overview.
- [X] Add local run instructions.
- [X] Add test instructions.
- [X] Add database/environment notes.
- [X] Add representative AI implementation examples.

### After Phase 3

- [X] Add Docker instructions.
- [X] Add deployment instructions.
- [X] Add CI/CD description.
- [X] Add public URL.
- [X] Add one deployment-related AI example if useful.

### After Phase 4

- [ ] Document the observed journey, telemetry UI, correlation and data redaction.
- [ ] Link redacted success/failure diagnosis evidence.
- [ ] Document the user-impact alert, isolated trigger and verified recovery evidence.

### After Phase 5

- [ ] Document the on-call agent's alert trigger, allowed remediation and permission boundaries if implemented.
- [ ] Link isolated end-to-end remediation evidence, deterministic test results and verified recovery.
- [ ] Clearly mark any unimplemented rubric targets and retain QA/human acceptance records.

---

# Final Reproducibility Check

Before submission, assume someone has never seen the project.

They should be able to understand:

```text
What is this?
↓
How is it built?
↓
How do I run it?
↓
How do I test it?
↓
How do I run it with Docker?
↓
How is it deployed?
```

Final checklist:

- [ ] README explains the problem.
- [ ] README explains the MVP.
- [ ] README explains the architecture.
- [ ] README lists the technology stack.
- [ ] README contains local setup instructions.
- [ ] README contains run instructions.
- [ ] README contains test instructions.
- [ ] README contains Docker instructions.
- [ ] README contains deployment information.
- [ ] README contains the public application URL.
- [ ] OpenAPI documentation is accessible.
- [ ] Architecture documentation is accessible.
- [ ] AI usage report is accessible.
- [ ] M6/M7 telemetry, alert and on-call evidence is accessible if implemented; otherwise record the scoring gaps.
- [ ] Verify documented setup, migrations and Docker Compose startup from a clean checkout; record the tested revision and prerequisites.
- [ ] Correct stale documentation, including resolved test-failure warnings and obsolete security-audit/agent-extension rubric claims, while preserving historical milestone records.
- [ ] Check that documentation describes the submitted MVP without adding unrelated cleanup or features.
- [ ] Recheck the latest final-project rubric and record its date/version.
- [ ] Map all 12 current criteria to direct evidence links, expected scores and remaining gaps: problem description; product specification; agent team specification; context management; application; testing; containerization; deployment; CI/CD; observability; alerting on user impact; on-call agent.
- [ ] Confirm the submitted revision has passing CI and verify the public application and its main journey; link the CI run and deployment evidence.
- [ ] Describe CI/CD accurately: tests plus current direct automatic Render deployment target 2/3; 3/3 requires automatic dev deployment followed by manual production deployment. A separate dev environment is an additional-score option, not required for passing.
- [ ] Confirm at least 10/24 points from delivered evidence, without counting unimplemented M6/M7 targets.
- [ ] Complete three peer reviews as required for a passing submission and record completion in the submission process.

### Final milestone
**M8 — The submitted revision is reproducible, its 12-criterion evidence map supports at least 10/24 points, and the three required peer reviews are complete.**

---

# Milestone Summary

- [X] **M1 — MVP Defined:** Product scope and non-goals are clear.
- [X] **M2 — Prototype Validated:** Core MVP works with a mock frontend.
- [X] **M3 — Backlog Ready:** Validated MVP translated into executable GitHub Issues.
- [X] **M4 — Local MVP Complete:** Full-stack MVP locally accepted in #22 with persistence and documented test evidence in #20/#21/#23 (see noted test limitation).
- [X] **M5 — Public MVP Complete:** Docker Compose, CI, public Render/Neon deployment and rollback were manually accepted (#33–#35); see #36 for milestone evidence.
- [ ] **M6 — Observability & Alerting Demonstrated:** One MVP journey has correlated telemetry in a UI and a working user-impact alert with verified recovery (criteria 10–11; additional-score targets).
- [ ] **M7 — On-Call Remediation Demonstrated:** An alert wakes an agent that fixes one bounded operational failure and verifies recovery in isolation (criterion 12; additional-score target).
- [ ] **M8 — Submission Ready:** Clean-start, CI/deployment checks and a current 12-criterion evidence map support at least 10/24 points; three peer reviews are complete.
