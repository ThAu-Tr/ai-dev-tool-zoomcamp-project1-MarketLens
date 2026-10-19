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

- [ ] Create `AGENTS.md`.
- [ ] Define the PM role.
- [ ] Define the Software Engineer role.
- [ ] Define the QA role.
- [ ] Define the general development process.
- [ ] Define how issues move through the workflow.

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

- [ ] Generate the basic frontend.
- [ ] Implement the main user flows.
- [ ] Use mocked data or mocked service calls.
- [ ] Make sure all core MVP actions can be demonstrated.
- [ ] Interact with the frontend yourself.
- [ ] Identify awkward or unnecessary functionality.
- [ ] Simplify the MVP if necessary.
- [ ] Update `plan.md` if the prototype changes the product definition.

The frontend at this point is a **prototype**, not necessarily the final production frontend.

### Output
- Working mock frontend
- Revised product specification if necessary

### Milestone
**M2 — The MVP can be demonstrated through the frontend using mocked data.**

---

## 5. Define the API contract

Use the validated frontend to determine what the backend actually needs to provide.

- [ ] Identify frontend operations requiring backend calls.
- [ ] Define endpoints.
- [ ] Define request formats.
- [ ] Define response formats.
- [ ] Define validation/error responses.
- [ ] Create or generate the OpenAPI specification.
- [ ] Check that every core frontend interaction has an API equivalent.

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

- [ ] Generate proposed backlog items.
- [ ] Review them manually.
- [ ] Remove unnecessary tasks.
- [ ] Split tasks that are too large.
- [ ] Merge tasks that are unnecessarily small.
- [ ] Check that every MVP feature is represented.
- [ ] Add required technical tasks that are not feature-specific.
- [ ] Move the final backlog to GitHub Issues.

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

- [ ] PM grooms the issue.
- [ ] PM defines the goal.
- [ ] PM defines acceptance criteria.
- [ ] PM defines out-of-scope behavior where necessary.
- [ ] SWE implements the feature.
- [ ] SWE adds appropriate tests.
- [ ] QA checks the acceptance criteria.
- [ ] QA returns PASS or FAIL.
- [ ] If FAIL, return the issue to SWE.
- [ ] Human-review the important changes.
- [ ] Merge/close the issue when accepted.

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

- [ ] Implement the database schema.
- [ ] Connect backend operations to the database.
- [ ] Add database setup instructions.
- [ ] Use configurable connection settings.
- [ ] Separate development/test/production configuration where appropriate.
- [ ] Avoid hardcoding environment-specific database URLs.
- [ ] Document migrations or initialization if relevant.

### Output
- Working persistent database layer
- Environment-aware database configuration

### Rubric coverage
- Database integration

---

## 9. Add automated tests during development

Do not postpone testing until the end.

For relevant features:

- [ ] Add backend unit tests.
- [ ] Add frontend/component tests where useful.
- [ ] Test validation and failure cases.
- [ ] Keep tests runnable locally.
- [ ] Maintain a passing test suite.

Focus effort on important behavior rather than maximizing test count.

---

## 10. Add explicit integration tests

Once the main system works end-to-end:

- [ ] Identify the 1–3 most important user workflows.
- [ ] Create integration tests for those workflows.
- [ ] Clearly separate integration tests from unit/component tests.
- [ ] Ensure tests exercise multiple system components.
- [ ] Document how integration tests are run.

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

- [ ] Create the required Dockerfile(s).
- [ ] Make sure the application runs in containers.
- [ ] Add Docker Compose only if useful.
- [ ] Move configuration into environment variables.
- [ ] Verify the complete app starts from a clean environment.
- [ ] Document container startup.

### Output
- Dockerfile(s)
- Optional `docker-compose.yml`
- Container run instructions

### Rubric coverage
- Containerization

---

## 12. Set up CI

- [ ] Create the CI workflow.
- [ ] Install dependencies automatically.
- [ ] Run relevant tests automatically.
- [ ] Make CI fail when tests fail.
- [ ] Keep the pipeline minimal.

### Output
- GitHub Actions workflow or equivalent

### Rubric coverage
- CI/CD pipeline

---

## 13. Deploy the application

- [ ] Choose the simplest acceptable hosting solution.
- [ ] Configure the production environment.
- [ ] Configure the production database if different.
- [ ] Deploy the application.
- [ ] Verify the deployed frontend.
- [ ] Verify the deployed API.
- [ ] Verify persistence.
- [ ] Verify the main user workflow.
- [ ] Add the public URL to the README.

### Output
- Publicly accessible application

### Rubric coverage
- Deployment

---

## 14. Add CD where useful

- [ ] Configure deployment after successful CI.
- [ ] Avoid automatic deployment if tests fail.
- [ ] Document how deployment works.
- [ ] Keep the pipeline as simple as possible.

### Output
- Automated or clearly documented deployment pipeline

### Milestone
**M5 — A tested, containerized version of the MVP is publicly deployed.**

---

# Phase 4 — Operations & Hardening

## 15. Add basic observability

Do the smallest amount necessary to meaningfully operate and diagnose the application.

- [ ] Add useful application logging.
- [ ] Log errors.
- [ ] Add health/status information if useful.
- [ ] Add metrics only where they provide rubric value.
- [ ] Verify that a production problem could be diagnosed from available information.

Do not build a large monitoring platform unless necessary.

### Output
- Logging
- Basic operational visibility
- Operational diagnosis evidence

---

## 16. Add security and audit evidence

Cover the rubric without turning the project into a security project.

- [ ] Run a deterministic security/dependency scan.
- [ ] Save or reference the findings.
- [ ] Perform a PR/code audit.
- [ ] Document relevant findings.
- [ ] Document security considerations for agents/extensions.
- [ ] Document how secrets are handled.
- [ ] Document what information AI tools are allowed to access.
- [ ] Create a short AI tool/data policy.

### Output
Possible artifacts:

```text
_docs/security.md
_docs/ai-data-policy.md
security scan output
audit output
```

### Rubric coverage
- Security, audit and DevOps hardening

### Milestone
**M6 — The deployed project has basic operational, audit and security evidence.**

---

# Phase 5 — Optional Agent Extension

Do this only after the core project is complete and only if the additional rubric points justify the effort.

Week 5 belongs here.

## 17. Evaluate criterion 12 effort

- [ ] Check the current rubric again before starting.
- [ ] Determine what is already satisfied through Week 1 artifacts.
- [ ] Calculate whether the additional point(s) justify the work.

Possible extension components:

- [ ] Reusable project workflow/skill
- [ ] Specialized subagent
- [ ] MCP tool/server
- [ ] Hook or guardrail
- [ ] Permission/security notes

Do **not** create artificial reusable tooling before you have an actual workflow worth reusing.

### Output
- Agent extension pack only if worthwhile

### Rubric coverage
- Agent Extension Pack

### Milestone
**M7 — Optional additional rubric coverage completed.**

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
- optionally one agent-extension example

### Output
- `_docs/ai-usage-report.md`

### Rubric coverage
- AI-assisted development workflow

---

## B. Documentation checkpoint after every major phase

### After Phase 1

- [ ] Update problem description.
- [ ] Update MVP scope.
- [ ] Update architecture.
- [ ] Reference OpenAPI.
- [ ] Add one useful AI workflow example.

### After Phase 2

- [ ] Update implemented-feature overview.
- [ ] Add local run instructions.
- [ ] Add test instructions.
- [ ] Add database/environment notes.
- [ ] Add representative AI implementation examples.

### After Phase 3

- [ ] Add Docker instructions.
- [ ] Add deployment instructions.
- [ ] Add CI/CD description.
- [ ] Add public URL.
- [ ] Add one deployment-related AI example if useful.

### After Phase 4

- [ ] Add observability notes.
- [ ] Add operational diagnosis evidence.
- [ ] Add security/audit evidence.
- [ ] Add AI tool/data policy.

### After Phase 5

- [ ] Document optional agent extensions if implemented.
- [ ] Document permissions/security implications.

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
- [ ] Security/audit evidence is accessible where required.
- [ ] All commands have been tested from a clean setup where practical.
- [ ] Remove outdated documentation.
- [ ] Remove unused files/features.
- [ ] Check the latest final-project rubric once more.
- [ ] Map every rubric criterion to visible evidence in the repository.

### Final milestone
**M8 — Another person can clone, understand, run, test and evaluate the complete project without additional explanation.**

---

# Milestone Summary

- [ ] **M1 — MVP Defined:** Product scope and non-goals are clear.
- [ ] **M2 — Prototype Validated:** Core MVP works with a mock frontend.
- [ ] **M3 — Backlog Ready:** Validated MVP translated into executable GitHub Issues.
- [ ] **M4 — Local MVP Complete:** Full-stack MVP works locally with persistence and tests.
- [ ] **M5 — Public MVP Complete:** Application is containerized, tested and deployed.
- [ ] **M6 — Production Evidence Complete:** Operations, security and audit requirements are covered.
- [ ] **M7 — Optional Extensions Complete:** Week 5 / criterion 12 added if worthwhile.
- [ ] **M8 — Submission Ready:** Documentation and reproducibility have been verified.