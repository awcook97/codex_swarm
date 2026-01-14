# Base Agent

I define the shared contract for all agents.

Purpose:
- Provide a consistent interface (name, role, instructions, run()).
- Log agent messages to the event bus.

Inputs:
- task: string
- context: AgentContext (tools, memory, config, run_id, flags)

Outputs:
- A JSON-compatible dict specific to the agent's role.

Constraints:
- Use only the tools exposed on AgentContext.
- Respect allowlists and dry-run behavior.
- Keep outputs concise and machine-friendly.
