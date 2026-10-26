---
name: subtask4llm-codex
description: Execute a multi-step software change through separate, sequential Codex workers with bounded retries and compact handoffs. Use when the user explicitly invokes $subtask4llm-codex or asks to carry out a dependency-ordered implementation plan with isolated worker contexts; do not use for planning-only requests or simple tasks that one Codex can complete directly.
---

# Subtask4LLM

Use the current Codex as the planner and reviewer. Delegate implementation steps to fresh `codex exec` workers through `scripts/run_workflow.py`.

## Workflow

1. Confirm this is a multi-step task whose ordered handoffs justify separate contexts. Do not decompose a small change merely to use the skill.
2. Inspect the repository and convert the authorized work into 2–10 concrete steps. Each step must have a bounded task, observable acceptance criteria, and only earlier steps as dependencies.
3. Read [references/plan-format.md](references/plan-format.md), create a version 1 JSON plan in a temporary location, and validate it with `--dry-run` before execution.
4. Select an explicitly available worker model that fits the user's cost/quality preference. Pass it with `--model` or set `CODEX_WORKFLOW_MODEL`; never silently assume that the planner's model is the intended worker model.
5. Run the orchestrator from the target repository:

   ```bash
   python3 <skill-path>/scripts/run_workflow.py <plan.json> \
     --workspace <repository> \
     --model <worker-model>
   ```

   Add `--artifacts-dir <directory>` only when persistent prompts and diagnostics are useful. Those artifacts can contain task details and dependency summaries, so treat them as potentially sensitive. Otherwise the orchestrator keeps only its compact final report.
6. If a worker fails, let the orchestrator perform its single retry. After the retry fails, stop; do not improvise additional child runs.
7. Review the final report and the actual workspace diff. Run or inspect proportionate final verification before claiming the user's task is complete. Report results, changed files, checks, and unresolved risks without reproducing child transcripts.

## Invariants

- Workers run one at a time in the same workspace, each in a fresh ephemeral Codex session.
- A worker receives its own task plus capped summaries only from dependencies named in its plan step.
- The orchestrator disables this exact skill for every child, sets `CODEX_WORKFLOW_CHILD=1` and `CODEX_WORKFLOW_DEPTH=1`, and refuses to run when either guard identifies a child.
- Child prompts forbid launching Codex, subagents, or this orchestrator. Do not weaken those controls.
- Use `workspace-write` unless the whole workflow is observational. Never widen sandbox permissions merely to make a failing step pass.
- Preserve unrelated user changes. Do not add destructive actions, external publication, credential use, or other authority that the original request did not grant.
- Reserve automatic retries for local, repeatable repository work. A failed attempt may leave partial edits for its retry; the orchestrator never resets or rolls back the workspace. Do not delegate deployments, publications, messages, migrations, purchases, or other non-idempotent external effects to this workflow.
- Do not start two workflows in the same workspace concurrently.
- Treat child summaries as evidence to verify, not as proof by themselves.

The guard prevents accidental recursion through this workflow. It is not an operating-system security boundary: a child able to clear its environment and execute arbitrary programs could launch another `codex` process. Strong prevention requires an external sandbox, executable allowlist, or wrapper policy.
