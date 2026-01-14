from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from swarm.bus import EventLog
from swarm.config import SwarmConfig
from swarm.llm import LLM
from swarm.memory import PersistentMemory, ShortTermMemory
from swarm.tools import FilesystemTool, HttpTool, ShellTool


@dataclass(slots=True)
class AgentContext:
    run_id: str
    objective: str
    config: SwarmConfig
    output_dir: Path
    event_log: EventLog
    short_term: ShortTermMemory
    persistent: PersistentMemory
    filesystem: FilesystemTool
    shell: ShellTool
    http: HttpTool
    llm: LLM
    dry_run: bool
    verbose: bool


class BaseAgent:
    def __init__(self, name: str, role: str, instructions: str) -> None:
        self.name = name
        self.role = role
        self.instructions = instructions

    async def run(self, task: str, context: AgentContext) -> dict[str, Any]:
        raise NotImplementedError

    def log(self, context: AgentContext, message: str) -> None:
        context.event_log.log(
            "agent_message",
            {"agent": self.name, "role": self.role, "message": message},
        )

    async def complete(self, context: AgentContext, prompt: str) -> str:
        context.event_log.log(
            "llm_prompt",
            {"agent": self.name, "role": self.role, "prompt": prompt},
        )
        if context.config.log_llm and not context.dry_run:
            log_path = context.output_dir / "llm.log"
            context.filesystem.append_text(
                log_path,
                "\n".join(
                    [
                        "=== PROMPT ===",
                        f"agent={self.name} role={self.role}",
                        prompt,
                        "",
                    ]
                ),
            )
        response = await context.llm.complete(prompt)
        context.event_log.log(
            "llm_response",
            {"agent": self.name, "role": self.role, "response": response.content},
        )
        if context.config.log_llm and not context.dry_run:
            log_path = context.output_dir / "llm.log"
            context.filesystem.append_text(
                log_path,
                "\n".join(
                    [
                        "=== RESPONSE ===",
                        f"agent={self.name} role={self.role}",
                        response.content,
                        "",
                    ]
                ),
            )
        return response.content
