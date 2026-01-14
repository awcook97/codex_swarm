<!-- Copilot instructions for this repository -->

<!-- Copilot instructions for this repository -->

# Copilot instructions — swarm

Quick, actionable notes to help AI coding agents be productive in this repo.

## Big picture
- The core runtime is the `swarm` package. The entrypoint is the CLI: `python -m swarm "<objective>"` (see [README.md](../README.md)).
- Orchestration is in [swarm/coordinator.py](../swarm/coordinator.py): the `Coordinator` builds a plan (via the `planner` agent) then executes steps in dependency order.
- Agents live under [swarm/agents/](../swarm/agents/) and implement `BaseAgent` (`async run(task, context) -> dict`). Agent instructions are loaded from `docs/agents/*` via [swarm/agents/instructions.py](../swarm/agents/instructions.py).
- Short-lived context is in `ShortTermMemory`; durable data (runs, messages, artifacts) is persisted by `PersistentMemory` into `swarm.db`.

## How the runtime works (important bits)
- `Coordinator.run(...)` returns a dict: `run_id`, `objective`, `final`, `output_dir`, `events`. See [swarm/coordinator.py](../swarm/coordinator.py).
- Planner uses the LLM interface (`swarm/llm.py`). The repo ships a deterministic `MockLLM` used by default; swap by passing a real `LLM` implementation into `Coordinator`.
- Tools are permissioned: `FilesystemTool`, `ShellTool`, and `HttpTool`. Allowlists are defined via `SwarmConfig` (see [swarm/config.py](../swarm/config.py)). Filesystem writes must be inside `filesystem_allowlist`.
- `output_dir` must be inside `repo_root` (coordinator enforces this); artifacts go in `artifacts/<run_id>` and outputs in `output/` by default.

## Agent development conventions
- Create a subclass of `BaseAgent` in `swarm/agents/`, set `name` and `role`, and implement `async run(self, task: str, context: AgentContext) -> dict`.
- Agents should return compact JSON-serializable dicts (examples in `docs/agents/*`). Planner output must be `{"plan": {"steps": [...]}}` with step objects containing `id`, `agent`, `task`, and optional `depends_on`.
- Agent textual instructions are authored in `docs/agents/*.md` and are loaded at runtime by name.
- Respect `context.dry_run`: do not perform persistent writes when `dry_run=True` (tests use `dry_run=True`).

## Safety and limits (project-specific)
- HTTP is disabled by default (`enable_http=False` in `SwarmConfig`). Only call `context.http` when `enable_http` is true.
- Shell commands are checked against a command allowlist (`shell_allowlist` in `SwarmConfig`) by `ShellTool` (see [swarm/tools/shell.py](../swarm/tools/shell.py)).
- Filesystem access is checked against `filesystem_allowlist` by `FilesystemTool` (see [swarm/tools/filesystem.py](../swarm/tools/filesystem.py)).

## Tests & local workflows
- Run the smoke test and full test suite with `pytest` (project uses `pytest-asyncio`). See `tests/test_swarm_smoke.py` for a canonical example of constructing `SwarmConfig` and running `Coordinator` in `dry_run`.
- Quick manual run: `python -m swarm "My objective" --run-id demo --max-steps 3 --dry-run --verbose`.

## Where to make common changes
- Replace the mock LLM: `swarm/llm.py` defines the `LLM` interface; pass a real LLM instance into `Coordinator`.
- Add/register agents: implement a class in `swarm/agents/` and register in `Coordinator.__init__` (`self.agents[...] = <AgentClass>(instructions=...)`).
- Adjust security allowlists: edit defaults in `SwarmConfig.from_repo_root` in [swarm/config.py](../swarm/config.py).

## Quick examples (copy/paste)
Run locally (dry run):
```
python -m swarm "Summarize the repo" --run-id quick --dry-run
pytest
```

## Short checklist for PRs that change behavior
- Update `docs/agents/*.md` for any agent instruction changes.
- If adding a tool or expanding allowlists, update `SwarmConfig` defaults and add tests verifying restrictions.
- Add or update a test in `tests/` demonstrating the new flow (use `dry_run` where possible).

---
If anything above is unclear or you want extra examples (e.g., a new-agent template), tell me which part to expand.
