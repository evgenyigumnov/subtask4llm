# subtask4llm

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
