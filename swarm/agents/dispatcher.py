from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from swarm.agents.base import AgentContext, BaseAgent


class DispatcherAgent(BaseAgent):
    def __init__(self, instructions: str | None = None) -> None:
        super().__init__(name="dispatcher", role="Dispatcher", instructions=instructions or "Dispatch handoff to sub-agents or artifacts.")

    async def run(self, task: str, context: AgentContext) -> dict[str, Any]:
        # task is ignored; the agent operates on the run's output_dir/handoff.json
        handoff_path = context.output_dir / "handoff.json"
        try:
            raw = context.filesystem.read_text(handoff_path)
            payload = json.loads(raw)
        except Exception as exc:  # could be missing or parse error
            self.log(context, f"No handoff found or parse error: {exc}")
            return {"dispatched": False, "reason": str(exc)}

        total = int(os.environ.get("DISPATCH_SUBAGENTS", "3"))
        results: dict[int, dict[str, Any]] = {}
        for i in range(1, total + 1):
            sub = {
                "subtask_id": i,
                "total": total,
                "parent": payload,
                "instructions": f"Handle portion {i} of {total} for the objective." ,
            }
            endpoint = os.environ.get(f"AGENT_{i}_ENDPOINT")
            if endpoint:
                # perform HTTP POST
                try:
                    resp = context.http.post(endpoint, sub)
                    results[i] = {"endpoint": endpoint, "status": resp.status, "text": resp.text}
                except Exception as exc:  # defensive
                    results[i] = {"endpoint": endpoint, "error": str(exc)}
            else:
                # write artifact
                artifact_dir = context.config.artifacts_dir / context.run_id
                artifact_dir_path = artifact_dir
                # use filesystem tool to write
                artifact_path = artifact_dir_path / f"subagent-{i}.json"
                try:
                    # ensure artifact dir exists using Path (filesystem tool enforces allowlist)
                    context.filesystem.write_text(artifact_path, json.dumps(sub, indent=2))
                    results[i] = {"artifact": str(artifact_path)}
                except Exception as exc:
                    results[i] = {"artifact_error": str(exc)}

        return {"dispatched": True, "results": results}
