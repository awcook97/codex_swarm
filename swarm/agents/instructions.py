from __future__ import annotations

from pathlib import Path


_AGENT_DOCS = {
    "base": Path("docs/agents/base.md"),
    "planner": Path("docs/agents/planner.md"),
    "researcher": Path("docs/agents/researcher.md"),
    "coder": Path("docs/agents/coder.md"),
    "critic": Path("docs/agents/critic.md"),
}


def load_agent_instructions(repo_root: Path, agent_name: str) -> str | None:
    doc_path = _AGENT_DOCS.get(agent_name)
    if doc_path is None:
        return None
    full_path = repo_root / doc_path
    if not full_path.exists():
        return None
    return full_path.read_text(encoding="utf-8")
