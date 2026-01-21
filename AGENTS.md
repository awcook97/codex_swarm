# Repository Guidelines

## Project Structure & Module Organization
- `swarm/` is the core Python package; primary orchestration lives in `swarm/coordinator.py`, agents in `swarm/agents/`, tools in `swarm/tools/`, and config in `swarm/config.py`.
- `tests/` contains pytest suites (e.g., `tests/test_*.py`).
- `docs/` and `docs/agents/` hold architecture and agent behavior references.
- `scripts/` includes helper scripts for local workflows.
- `output/` and `swarm.db` are runtime artifacts created by executions.

## Build, Test, and Development Commands
- `python -m swarm "objective"` runs a full swarm execution using the default MockLLM.
- `python -m swarm "objective" --llm-provider ollama --ollama-model llama3.1` runs with Ollama (see `README.md` for flags).
- `pytest` runs the test suite (async tests use `pytest-asyncio`).

## Coding Style & Naming Conventions
- Python 3.11+; use 4-space indentation and type hints where practical.
- Naming follows standard Python conventions: `snake_case` for functions/modules, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.
- Agent outputs should remain JSON-serializable dictionaries to keep planner/critic pipelines stable.

## Testing Guidelines
- Framework: `pytest` with `pytest-asyncio` (see `pyproject.toml`).
- Naming: test files are `tests/test_*.py`; test functions should start with `test_`.
- No explicit coverage target is defined; favor targeted tests for new agents, tools, and coordinator flows.

## Commit & Pull Request Guidelines
- Recent history uses commit messages like `Update: <files or short summary>`; follow that pattern for consistency.
- PRs should include a brief summary, key commands run (e.g., `pytest`), and links to related issues where applicable.

## Security & Configuration Tips
- Filesystem, shell, and HTTP access are gated by allowlists in `SwarmConfig`; update `swarm/config.py` or CLI flags with care.
- Use `docs/AGENTS.md` and `docs/agents/*.md` when modifying agent behavior or output contracts.
