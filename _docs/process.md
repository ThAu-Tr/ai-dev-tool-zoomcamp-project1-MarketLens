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
5. On PASS, close the issue
6. Repeat until the backlog is empty

Rules

- You can work on up to 3 issues at the time
- Do not skip step 2
- The engineer does not close the issue
- QA does not fix the code, only outputs PASS or FAIL
- The orchestrator merges the approved work and closes the issue only after QA outputs PASS