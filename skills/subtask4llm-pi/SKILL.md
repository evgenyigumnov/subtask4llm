---
name: subtask4llm-pi
description: Plan and run a dependency-ordered software change through sequential, one-shot Pi workers with bounded retries and explicit dependency handoffs. Use for authorized multi-step implementation work that benefits from isolated worker contexts; avoid it for planning-only requests or small changes that one worker can complete directly.
---

# Subtask4LLM for Pi

Use the current Pi session as the planner and reviewer. The standalone runner at [scripts/run_workflow.py](scripts/run_workflow.py) launches sequential Pi workers in the target workspace.

## Workflow

1. Choose this workflow when the requested implementation has multiple concrete steps and ordered handoffs make separate worker contexts useful. Do not split a small change just to use the runner.
2. Inspect the repository and prepare a complete version 1 JSON plan with 1–10 ordered steps. Give every step a unique ID, a bounded task, nonempty acceptance criteria, and dependencies only on earlier steps. Include shared repository findings, user requirements, constraints, relevant paths, design decisions, and edge cases in the plan so workers do not need the planner's conversation.
3. Read [references/plan-format.md](references/plan-format.md), write the plan to a temporary JSON file, and validate it with `--dry-run` before execution.
4. Before starting workers, show the user the goal and ordered step titles, each with a short description and its dependencies. Then launch the workflow unless the user asks to review or change the plan first.
5. Run the runner from the target repository.

   On macOS or Linux:

   ```bash
   python3 <skill-path>/scripts/run_workflow.py <plan.json> --workspace <repository>
   ```

   On Windows PowerShell:

   ```powershell
   py -3 <skill-path>\scripts\run_workflow.py <plan.json> --workspace <repository>
   ```

   Add `--model <model-id>` only when the model ID is known and should override the configured model. Otherwise, the runner uses `PI_WORKFLOW_MODEL` when set, then Pi's configured default. Use `--timeout-seconds`, `--retries 0|1`, `--max-summary-chars`, `--pi-bin`, or `--artifacts-dir` only when the task calls for those controls. Artifacts are optional and the runner refuses to overwrite an existing artifact destination.
6. Workers run as one-shot print-mode Pi processes with `--print --no-session --no-skills`. Prompts are sent through standard input, and the runner expects the final print-mode text to be raw JSON matching the documented result schema. Workers retain normal `AGENTS.md` context discovery; the runner does not disable context files. Each worker gets the shared context, the full workflow map, its assigned task and acceptance criteria, and detailed results only for its declared dependencies.
7. If a step fails, let the runner use at most its configured retry, then stop at the first unsuccessful step. Do not improvise extra worker runs after the runner stops.
8. Review the runner's final report and the actual workspace diff. Verify the requested changes proportionately, then report changed files, checks, and unresolved risks.

## Prerequisites and permissions

Pi CLI and a provider configured for Pi must already be installed and usable before running this workflow. This skill does not install Pi, providers, or other tools automatically.

Pi worker commands can modify files with the current user's permissions. Pi CLI is not a sandbox. Use the runner only when those permissions are appropriate for the requested repository work, preserve unrelated changes, and do not grant workers unrelated external actions.

## References

- [Version 1 plan and result format, CLI controls, and examples](references/plan-format.md)
- [Standalone sequential Pi runner](scripts/run_workflow.py)
