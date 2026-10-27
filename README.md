# subtask4llm

## Make small-context LLMs handle big coding tasks

**The problem:** Coding agents accumulate context as they work: source code, tool outputs, reasoning, errors, and previous attempts. Eventually, the context window fills up, the model loses focus, and coding quality degrades.

This is especially painful when running local LLMs with limited context windows (32K–64K tokens).

**The solution:** Instead of forcing one LLM to complete a massive task in a single conversation, **subtask4llm splits the work into up to 10 smaller, sequential tasks, each executed by a fresh coding agent with its own clean context window.**

The main agent acts as an orchestrator: it plans the work, delegates tasks, collects results, and verifies the outcome. Each worker receives only the project information and task-specific context it needs, including relevant results from previous tasks.

**The key idea: Give each subtask a fresh context window instead of filling one context window with the entire project history.**

This makes complex coding workflows more practical with smaller local models, reduces context pollution, and can also reduce token costs when using cloud APIs.

Works with **Pi Coding Agent** and **OpenAI Codex CLI**.

No complex infrastructure. No recursive agent spawning. Just a structured plan, isolated workers, and sequential execution.

Agent-specific skills live in `skills/<skill-name>/`. The Codex skill is in
`skills/subtask4llm-codex/` and can be installed on its own:

```bash
npx skills add evgenyigumnov/subtask4llm --skill subtask4llm-codex --agent codex
```

The standalone Pi skill is in `skills/subtask4llm-pi/` and can also be installed
on its own:

```bash
npx skills add evgenyigumnov/subtask4llm --skill subtask4llm-pi --agent pi
```

The Skills CLI installs project skills for Pi under `.agents/skills/`. See its
[supported agents](https://github.com/vercel-labs/skills/blob/main/docs/agents.md)
and [`skills add` options](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)
for the target path and command syntax.

Each skill directory contains its own `SKILL.md` and any supporting files, so
other agent-specific skills can be added and installed independently.

Both workflow runners write orchestrator and worker activity to one live log per
run. Each subtask appends its events to that same file; no per-subtask log files
are created. At startup, the runner prints the log path and a `tail -f` command.
Use `--live-log <path>` to choose where the log is written.
The planner should share that path and let the user follow progress there instead
of repeatedly polling workers or rereading the log.

By default, both runners stop after a subtask remains unsuccessful after its
allowed attempts. Pass `--continue-on-error` at launch to run the remaining plan
steps; the final workflow status still reports failure if any step failed.
