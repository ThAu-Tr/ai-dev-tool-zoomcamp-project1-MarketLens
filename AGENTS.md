# Agent Instructions

## Project Context

Read these files when relevant:

- `_docs/plan.md` — product scope and MVP
- `_docs/architecture.md` — system architecture
- `_docs/process.md` — development workflow
- `_docs/team/pm.md` — PM role
- `_docs/team/swe.md` — software engineer role
- `_docs/team/qa.md` — QA role

## General Rules

- Keep the project within the defined MVP.
- Prefer small, understandable solutions.
- Avoid unnecessary abstractions.
- Implement features vertically where practical.
- Follow the OpenAPI contract.
- Add tests for important behavior.
- Do not hardcode secrets.
- Do not change unrelated parts of the project.
- Ask for or surface missing requirements instead of inventing major product behavior.

## Development Workflow

Use:

```text
PM → SWE → QA
```

If QA fails:

```text
QA → SWE → QA
```

Human review remains the final acceptance step for important changes.
