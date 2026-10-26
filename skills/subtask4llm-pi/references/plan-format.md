# Pi workflow plan format (version 1)

The Pi workflow runner executes a bounded plan one step at a time in the same
workspace. Each step runs in a new, one-shot Pi process. This format and runner
are self-contained in this skill directory.

## Plan schema

Pass a UTF-8 JSON object with these fields:

| Field | Type | Requirement |
| --- | --- | --- |
| `version` | integer | Must be exactly `1` (`true` is not accepted as an integer). |
| `goal` | string | Required and non-empty after trimming. |
| `context` | string or `null` | Optional shared context; omitted or `null` defaults to empty. |
| `steps` | array | Required, with 1–10 step objects in execution order. |

Every step has the following fields:

| Field | Type | Requirement |
| --- | --- | --- |
| `id` | string | Required, unique, and matches `^[a-z0-9][a-z0-9_-]{0,63}$`. |
| `title` | string | Required and non-empty after trimming. |
| `task` | string | Required and non-empty after trimming. |
| `context` | string or `null` | Optional step-specific context; omitted or `null` defaults to empty. |
| `acceptance` | array of strings | Required and non-empty; every item must be non-empty. |
| `depends_on` | array of strings | Required; may be empty. IDs must be unique and refer only to earlier steps. |

Steps run in listed order. Dependencies do not reorder steps; they declare
which earlier results are handed to a worker. Unknown object properties are
ignored by the current runner. A compact example:

```json
{
  "version": 1,
  "goal": "Add and document a small feature",
  "context": "Keep the change compatible with the existing project.",
  "steps": [
    {
      "id": "implement",
      "title": "Implement the feature",
      "task": "Add the requested feature and inspect related code.",
      "context": "Use the existing project conventions.",
      "acceptance": ["The feature is implemented", "Relevant checks pass"],
      "depends_on": []
    },
    {
      "id": "document",
      "title": "Document the feature",
      "task": "Document the interface and how to use it.",
      "acceptance": ["Usage is documented"],
      "depends_on": ["implement"]
    }
  ]
}
```

## Worker result contract

Every Pi worker must finish with raw JSON as its final assistant text. Do not
wrap it in a Markdown code fence or add commentary before or after it. The
object must contain exactly these fields:

```json
{
  "status": "completed",
  "summary": "Implemented the assigned step.",
  "files_changed": ["src/example.py"],
  "verification": [
    {"command": "python -m compileall src", "outcome": "passed"}
  ],
  "risks": []
}
```

`status` must be `completed`, `blocked`, or `failed`; `summary` must be a
non-empty string. `files_changed` and `risks` are arrays of strings, and
`verification` is an array of objects containing only string fields `command`
and `outcome`. The runner rejects malformed JSON, duplicate keys, Markdown
wrappers, extra or missing fields, and invalid field types. Only `completed`
counts as success. A `blocked` or `failed` result is an unsuccessful attempt.

Pi JSON mode returns a JSONL event stream on stdout and exits after one
invocation. The runner passes each prompt on stdin and launches Pi with
`--mode json --no-session --no-skills`, plus `--model MODEL` when a model is
set. It extracts the final assistant text and accepts it only if it parses as
the exact result object above; a nonzero process exit also fails the attempt.
See the official [Pi CLI integration guide](https://pi.dev/docs/latest/cli-integration)
and [JSON event stream reference](https://pi.dev/docs/latest/json).

## Dependency handoff and execution

Each worker receives the goal, shared context, complete ordered workflow map,
its assigned task and acceptance criteria, and the detailed results for only
the IDs in its `depends_on` list. Results are included in the dependency
section of the prompt, truncated to the `--max-summary-chars` limit across all
declared dependencies. Workers run sequentially in one workspace, so later
steps can inspect changes already made there.

The runner attempts each step once, plus the configured retry count, except
that timeouts are not retried. A retry count of `1` is the maximum; after the
last unsuccessful attempt, the workflow stops and later steps are reported as
not run. A failed attempt may have left partial changes in the workspace; the
runner does not roll them back.

## Runner options

Run the script from the project root, or provide paths to the script and plan.
The plan path can be `-` to read JSON from stdin.

| Option | Default | Behavior |
| --- | --- | --- |
| `--workspace DIR` | `.` | Existing directory shared by all workers; resolved before execution. |
| `--dry-run` | off | Validates the plan and prints the ordered steps, command arguments, and effective controls as JSON without launching Pi. |
| `--timeout-seconds N` | `1800` | Hard maximum runtime for an individual worker process. |
| `--timeout-checkpoint-seconds N` | `600` | Check progress and inspect active shell commands at each interval before the hard timeout. |
| `--retries N` | `1` | Number of retries after a failed attempt; only `0` or `1` is allowed. |
| `--max-summary-chars N` | `16000` | Positive character cap for detailed dependency results included in each prompt. |
| `--artifacts-dir DIR` | not retained | Optional new directory outside the workspace for prompts, diagnostics, results, and the report. The path must not already exist; existing destinations are refused. |
| `--live-log PATH` | system temp directory | Write orchestrator and worker activity to one workflow-wide log. The runner prints its path and a `tail -f` command at startup. |
| `--pi-bin PATH` | `pi` | Pi executable name or executable path. Names are resolved through `PATH`. |
| `--model MODEL` | `PI_WORKFLOW_MODEL`, then Pi's configured model | Model passed to Pi as `--model MODEL`; the CLI option takes precedence over the environment variable. |

The runner does not start a shell. It invokes Pi with an argument array and
supplies the task prompt on stdin. It retains Pi's `AGENTS.md` context
discovery by not passing `--no-context-files`; `--no-skills` prevents workers
from recursively loading skills. The worker environment sets
`PI_WORKFLOW_CHILD=1` and `PI_WORKFLOW_DEPTH=1`. The runner refuses to start
when either Pi-specific variable indicates it is already running as a child.
These Pi guards do not read or modify `CODEX_WORKFLOW_*` variables.

The runner streams readable summaries from every attempt, plus orchestrator
updates, into one workflow-wide live log. It does not create per-attempt
progress log files. Recent events are also held in memory for diagnostics. At
each 10-minute checkpoint the runner prints the latest events and continues
unless a shell command has produced no update for 10 minutes. Such a command is
stopped immediately; otherwise the worker can continue until the 30-minute
hard limit. Timeout attempts are not retried. Timeout diagnostics include the
recent progress and available stderr tail.

Pi CLI can run commands and modify files using the current user's permissions;
the runner and Pi CLI are not a security sandbox. Review the plan and use an
appropriately isolated workspace for work that needs stronger containment.
When `--artifacts-dir` is enabled, retained prompts and diagnostics can contain
project details, dependency summaries, and recent command output. The live log
is managed separately; use `--live-log` to choose its path.

## Examples

From the repository root on Linux or macOS, validate and inspect a plan without
starting Pi, then launch it:

```bash
python3 skills/subtask4llm-pi/scripts/run_workflow.py ./plan.json --workspace . --dry-run
python3 skills/subtask4llm-pi/scripts/run_workflow.py ./plan.json --workspace . --timeout-seconds 1800 --timeout-checkpoint-seconds 600 --retries 1
```

In Windows PowerShell, use the Python launcher and Windows paths:

```powershell
py -3 .\skills\subtask4llm-pi\scripts\run_workflow.py .\plan.json --workspace . --dry-run
py -3 .\skills\subtask4llm-pi\scripts\run_workflow.py .\plan.json --workspace . --timeout-seconds 1800 --timeout-checkpoint-seconds 600 --retries 1
```

To retain artifacts, add a fresh path outside the workspace to the launch
command, for example `--artifacts-dir ../workflow-artifacts` on Linux/macOS or
`--artifacts-dir ..\workflow-artifacts` in PowerShell. An existing directory
at that path causes the runner to stop without overwriting it.

## Official references

- [Pi CLI integration: print mode and output](https://pi.dev/docs/latest/cli-integration)
- [Pi skills: discovery and project locations](https://pi.dev/docs/latest/skills)
- [Skills CLI: supported agents and install paths](https://github.com/vercel-labs/skills/blob/main/docs/agents.md)
- [Skills CLI: `skills add`, `--skill`, and `--agent`](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)
