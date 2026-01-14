# AI Swarm

A local, production-ready multi-agent framework built with asyncio. It runs out of the box using a deterministic MockLLM and can be swapped to a real LLM provider later.

## Quick start

```bash
python -m swarm "test"
```

Optional flags:

```bash
python -m swarm "my objective" --run-id demo --max-steps 3 --dry-run --verbose -o output/demo
```

Outputs are written to `output/<slug>` by default (or `-o/--output-dir`) and run metadata is stored in `swarm.db`.

## Using Ollama

```bash
python -m swarm "build me a 5 stage rocket animation" --llm-provider ollama --ollama-model llama3.1
```

If your Ollama server uses a different endpoint, pass it explicitly:

```bash
python -m swarm "build me a 5 stage rocket animation" --llm-provider ollama --ollama-model llama3.1 --ollama-endpoint /api/chat
```

For large models, you may want a longer timeout:

```bash
python -m swarm "make a snake game" --llm-provider ollama --ollama-model llama3.1 --ollama-timeout 120
```

## Adding a new agent

1. Create a new agent in `swarm/agents/` that subclasses `BaseAgent` and implements `async run()`.
2. Register it in `swarm/coordinator.py` inside `self.agents`.
3. Update your planner output to reference the new agent in a step.

## Swapping in a real LLM

The interface is defined in `swarm/llm.py`. Implement `LLM.complete()` and pass your implementation into `Coordinator`.

Example sketch:

```python
from swarm.coordinator import Coordinator
from swarm.config import SwarmConfig
from your_llm import RealLLM

config = SwarmConfig.from_repo_root(...)
coordinator = Coordinator(config=config, llm=RealLLM())
```

## Security notes

- Filesystem access is restricted to allowlisted paths in `SwarmConfig`.
- Shell execution is limited to an allowlist of commands.
- HTTP requests are disabled by default (`enable_http=False`) to avoid accidental network access.

## Tests

```bash
pytest
```

## Docs

- Agents overview: docs/AGENTS.md
- Coordinator: docs/COORDINATOR.md
