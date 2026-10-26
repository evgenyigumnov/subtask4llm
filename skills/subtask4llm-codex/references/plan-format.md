# Plan format

The orchestrator accepts a UTF-8 JSON document with `version: 1`, one goal, and 1–10 ordered steps.

```json
{
  "version": 1,
  "goal": "Add token-based authentication to the service",
  "context": "The service is a Python API. Keep the existing public health endpoints unauthenticated. The user requires bearer tokens. Prefer the existing stack and avoid adding dependencies unless inspection shows they are needed. Existing route conventions are in src/api/routes.py and middleware is registered in src/api/app.py.",
  "steps": [
    {
      "id": "api",
      "title": "Implement the authentication API",
      "task": "Add the token endpoint and request authentication middleware. Preserve existing public health endpoints.",
      "context": "Follow the existing router and dependency injection patterns. Inspect current user credential validation before adding new abstractions. Return the token in the API's existing response envelope.",
      "acceptance": [
        "Valid credentials return a token",
        "Protected endpoints reject missing or invalid tokens"
      ],
      "depends_on": []
    },
    {
      "id": "tests",
      "title": "Add authentication coverage",
      "task": "Add focused tests for successful login and protected endpoint failures.",
      "acceptance": [
        "Tests cover valid, missing, and invalid credentials",
        "Existing tests remain unchanged unless behavior requires it"
      ],
      "depends_on": ["api"]
    },
    {
      "id": "verify",
      "title": "Run repository checks",
      "task": "Run the narrow authentication tests, then the repository's standard verification commands. Fix only regressions caused by this plan.",
      "acceptance": [
        "Relevant tests and standard checks pass",
        "Any remaining failure is reported with its exact command"
      ],
      "depends_on": ["api", "tests"]
    }
  ]
}
```

## Field rules

- `version` must be the integer `1`.
- `goal` must be a non-empty string describing the shared outcome.
- `context` is an optional string for shared user requirements, decisions, repository findings, architecture, conventions, constraints, and other information workers need but cannot infer from the goal. Include the relevant details from the user's request; do not assume workers can see the planner's conversation.
- `steps` must contain 1–10 objects in execution order.
- `id` must be unique and use only lowercase ASCII letters, digits, `_`, or `-`, starting with a letter or digit.
- `title` and `task` must be non-empty strings. Put the concrete action, scope boundaries, relevant files, behavior, edge cases, and implementation detail in `task`.
- `context` is an optional per-step string for details that apply only to that step, such as discovered code paths, interfaces, prior decisions, compatibility requirements, and constraints. Add enough detail for an isolated worker to execute without guessing. Shared and step context is passed without the dependency-summary character cap.
- `acceptance` must be a non-empty list of non-empty strings that a worker can check.
- `depends_on` must be a list of unique step IDs that occur earlier in the file. Omit unrelated prior steps so their summaries are not injected.

## Planning guidance

- Split at meaningful ownership or verification boundaries, not by file count.
- Include the commands or observable behavior needed for acceptance, but do not prescribe code the worker should rediscover from the repository.
- Give each write step enough scope to leave the workspace coherent for the next step.
- Put a dedicated verification step last when checks span multiple implementation steps.
- Keep steps local and safely repeatable: a retry sees any partial files left by its first attempt. Perform non-idempotent external actions outside this workflow.
- Do not place secrets, full chat history, or unrelated repository content in the plan. Include all relevant requirements and repository findings; workers can inspect the shared workspace for additional detail.
- The worker prompt includes the shared context, all step titles/tasks/acceptance criteria as a workflow map, and the assigned step's detailed context. It also includes detailed results from declared dependencies, subject to the configurable `--max-summary-chars` limit (16,000 characters by default). Put critical requirements and decisions in plan context rather than relying on dependency summaries.
- Before launching the plan, show the user its goal and ordered step titles, each with a short description and dependencies. Then launch immediately without waiting for confirmation, so the user can interrupt or comment while it runs.

Validate without starting a child session:

```bash
python3 <skill-path>/scripts/run_workflow.py <plan.json> --workspace <repository> --dry-run
```

On Windows PowerShell, use `py -3 <skill-path>\scripts\run_workflow.py <plan.json> --workspace <repository> --dry-run`. Add `--model <worker-model>` only when you want to override the Codex CLI configured model.

The dry run displays the effective child command controls and step ordering. It does not contact a model.
