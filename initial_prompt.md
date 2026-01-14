Build me a production-ready “AI Swarm” (multi-agent) framework in Python.

GOAL
I want a local codebase that lets me define multiple specialized agents (e.g., Researcher, Planner, Coder, Critic) that collaborate on tasks via a coordinator. The system should support:
- Parallel execution for independent subtasks
- Shared memory (short-term + persistent store)
- Tool calling (shell commands, HTTP requests, file read/write)
- A message bus / event log so I can inspect agent decisions
- Deterministic-ish runs via seeded randomness where applicable
- Extensible agent definitions

REQUIREMENTS
1) Create a repo structure like:
   swarm/
     __init__.py
     main.py
     coordinator.py
     agents/
       __init__.py
       base.py
       researcher.py
       planner.py
       coder.py
       critic.py
     memory/
       __init__.py
       short_term.py
       persistent.py
     tools/
       __init__.py
       filesystem.py
       shell.py
       http.py
     bus/
       __init__.py
       event_log.py
     config.py
   tests/
     test_swarm_smoke.py
   README.md
   pyproject.toml (or requirements.txt)

2) Use Python 3.11+. Use type hints everywhere.
3) Implement concurrency using asyncio. Agents can run concurrently when tasks are independent.
4) Coordinator:
   - Accepts a user objective string
   - Asks the Planner to decompose into steps
   - Dispatches subtasks to agents
   - Routes outputs through Critic for quality checks
   - Produces a final combined result
   - Maintains an event log (timestamped) of all messages/actions

5) Agents:
   - BaseAgent with name, role, instructions, and async run(task, context)
   - Researcher: gathers info (stubbed; uses HTTP tool)
   - Planner: breaks objective into a structured plan (JSON output)
   - Coder: writes/edits files via filesystem tool
   - Critic: reviews outputs and requests revisions if needed

6) Memory:
   - Short-term memory: in-memory dict keyed by run_id + agent
   - Persistent memory: sqlite file (swarm.db) with tables for runs, messages, artifacts
   - Simple API: put/get/list

7) Tools:
   - filesystem: safe read/write with path allowlist rooted in repo
   - shell: run limited commands (config allowlist) and capture stdout/stderr
   - http: basic GET with timeouts and user-agent header

8) CLI:
   - `python -m swarm "my objective here"`
   - flags: --run-id, --verbose, --max-steps, --dry-run
   - prints final answer plus location of artifacts

9) Provide a smoke test that runs the coordinator on a trivial objective and asserts it produces a non-empty output and logs events.

10) IMPORTANT: Do NOT require any external paid API keys. If LLM calls are needed, implement a “MockLLM” that returns deterministic canned responses so the framework runs out-of-the-box. Make the LLM interface pluggable so I can later swap in a real provider.

DELIVERABLE
Generate all files with complete code, plus README explaining:
- how to run
- how to add an agent
- how to plug in a real LLM later
- security notes about tools

Quality bar: clean architecture, readable code, minimal dependencies, and everything runs successfully after `python -m swarm "test"`.

Start by outputting a tree of files you will create, then output each file’s full contents.
