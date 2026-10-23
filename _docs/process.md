- Task are Github issues
- Work in isolated git worktrees and run up to three agents in parallel.
- Read the acceptance criteria before starting and before closing
- Commit regularly

Roles

- Engineer - implements one groomed task, follows _docs/team/software-engineer.md
- QA - checks the result against the acceptance criteria, follows _docs/team/qa-engineer.md
- Orchestrator - coordinate the work, follows _docs/team/orchestrator.md

Development Process

The main session is the orchestrator. It launches the engineer
and QA as subagents. It does not implement or test itself.

Lifecycle

1. Pick the next groomed issue from the backlog (identified by label)
2. Engineer implements it
3. QA verifies it
4. On FAIL, back to step 2 with the QA comment as input
5. On QA PASS, the orchestrator commits/merges approved changes and posts a concise implementation and QA report with how the human can verify the behavior; **leave the issue open**
6. The human tests/reviews the implemented behavior and **is the only one who may close the issue**. On human FAIL, return to implementation and QA; on human PASS, the human closes the issue
7. Repeat until the backlog is empty

Rules

- You can work on up to 3 issues at the time
- Do not skip step 2
- The engineer does not close the issue
- QA does not fix the code, only outputs PASS or FAIL
- The orchestrator may merge work only after QA PASS, but **must not close issues**
- **Only the human owner may close GitHub issues**, after manually accepting the delivered behavior; QA PASS is necessary but not sufficient for closure
- Codex agents must not change issue state to closed or imply human acceptance; leave each issue open with verification instructions