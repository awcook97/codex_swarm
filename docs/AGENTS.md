# Agents

This repo defines a small, opinionated agent set that the coordinator can schedule.
Each agent owns a narrow responsibility and exposes a simple JSON output contract.

Docs by role:
- Base agent: docs/agents/base.md
- Planner: docs/agents/planner.md
- Researcher: docs/agents/researcher.md
- Coder/Writer: docs/agents/coder.md
- Critic: docs/agents/critic.md

Conventions:
- Inputs are plain-text tasks plus the shared AgentContext.
- Outputs are JSON dicts; keep them compact and parseable.
- Follow SwarmConfig allowlists for filesystem, shell, and HTTP tools.
- Prefer deterministic, reproducible behavior by default.
- Write artifacts into the shared output directory.
- Planner/researcher/critic emit supporting files alongside coder outputs.
