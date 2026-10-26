---
name: subtask4llm-codex
description: Execute a multi-step software change through separate, sequential Codex workers with bounded retries and detailed, relevant handoffs. Use when the user explicitly invokes $subtask4llm-codex or asks to carry out a dependency-ordered implementation plan with isolated worker contexts; do not use for planning-only requests or simple tasks that one Codex can complete directly.
---

# Subtask4LLM

Use the current Codex as the planner and reviewer. Delegate implementation steps to fresh `codex exec` workers through `scripts/run_workflow.py`.

## Workflow

1. Confirm this is a multi-step task whose ordered handoffs justify separate contexts. Do not decompose a small change merely to use the skill.
2. Inspect the repository and convert the authorized work into 2–10 concrete steps. Each step must have a bounded task, observable acceptance criteria, and only earlier steps as dependencies. Treat each worker as having no access to the planner's conversation: put relevant user requirements, decisions, repository findings, file paths, architecture, constraints, edge cases, and implementation guidance into the plan. Use shared `context` for information that applies across steps and each step's `context` for details specific to that step. Include enough detail that the worker can act without guessing; do not rely on unstated conversation context.
3. Read [references/plan-format.md](references/plan-format.md), create a version 1 JSON plan in a temporary location, and validate it with `--dry-run` before execution.
4. Use the current Codex session's model for workers by default, and pass it with `--model`. Choose a different worker model only when the user explicitly requests one or has stated a cost/quality preference that calls for it. Do not upgrade to a stronger model based on your own judgment. If the current model cannot be determined, ask instead of guessing. `CODEX_WORKFLOW_MODEL` may be used when the user has explicitly configured a worker model.
5. Before launching any worker, show the user the plan in a concise, readable form in the conversation: the goal and the ordered list of step titles with a short description and dependencies. Then launch the workflow immediately; do not wait for confirmation. The user can interrupt it or send a follow-up comment while it runs.
6. Run the orchestrator from the target repository:

   ```bash
   python3 <skill-path>/scripts/run_workflow.py <plan.json> \
     --workspace <repository> \
     --model <worker-model>
   ```

   Add `--artifacts-dir <directory>` only when persistent prompts and diagnostics are useful. Those artifacts can contain task details and dependency summaries, so treat them as potentially sensitive. Otherwise the orchestrator keeps only its compact final report.
   The orchestrator launches each worker with `--yolo`, as requested for this workflow.
7. If the user asks to stop while the workflow is running, interrupt it promptly. If the user sends a follow-up comment, acknowledge it and incorporate it into the remaining work where possible. If a worker fails, let the orchestrator perform its single retry. After the retry fails, stop; do not improvise additional child runs.
8. Review the final report and the actual workspace diff. Run or inspect proportionate final verification before claiming the user's task is complete. Report results, changed files, checks, and unresolved risks without reproducing child transcripts.

## Invariants

- Workers run one at a time in the same workspace, each in a fresh ephemeral Codex session.
- A worker receives the shared project context, the full workflow map, its detailed task and step context, acceptance criteria, and detailed results only from dependencies named in its plan step. Dependency results have a configurable character cap; keep important requirements and design decisions in the uncapped plan context fields.
- The orchestrator disables this exact skill for every child, sets `CODEX_WORKFLOW_CHILD=1` and `CODEX_WORKFLOW_DEPTH=1`, and refuses to run when either guard identifies a child.
- Child prompts forbid launching Codex, subagents, or this orchestrator. Do not weaken those controls.
- Workers run with `--yolo`, which disables Codex sandboxing and approval prompts. Use this workflow only in an externally isolated environment; workers can access files and network resources beyond the workspace.
- Preserve unrelated user changes. Do not add destructive actions, external publication, credential use, or other authority that the original request did not grant.
- Reserve automatic retries for local, repeatable repository work. A failed attempt may leave partial edits for its retry; the orchestrator never resets or rolls back the workspace. Do not delegate deployments, publications, messages, migrations, purchases, or other non-idempotent external effects to this workflow.
- Do not start two workflows in the same workspace concurrently.
- Treat child summaries as evidence to verify, not as proof by themselves.

The guard prevents accidental recursion through this workflow. It is not an operating-system security boundary: a child able to clear its environment and execute arbitrary programs could launch another `codex` process. Strong prevention requires an external sandbox, executable allowlist, or wrapper policy.
