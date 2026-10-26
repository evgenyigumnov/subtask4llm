# subtask4llm

Agent-specific skills live in `skills/<skill-name>/`. The Codex skill is in
`skills/subtask4llm-codex/` and can be installed on its own:

```bash
npx skills add evgenyigumnov/subtask4llm --skill subtask4llm-codex --agent codex
```

Each skill directory contains its own `SKILL.md` and any supporting files, so
other agent-specific skills can be added and installed independently.
