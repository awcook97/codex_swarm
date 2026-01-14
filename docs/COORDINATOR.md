# Coordinator

I orchestrate the swarm run: build context, request a plan, execute steps, and
compose the final output.

Responsibilities:
- Create the run context and initialize shared tools.
- Ask the planner for a step graph and enforce dependency order.
- Execute ready steps concurrently and collect results.
- Route each non-critic result to the critic for review.
- Persist run metadata, messages, and artifacts.

Runtime contract:
- Inputs: objective string, optional run_id, output_dir, max_steps, dry_run, verbose.
- Outputs: final text plus metadata (run_id, output_dir, events).

Performance defaults:
- Executes independent steps concurrently with asyncio.gather.
- Reuses a persistent DB connection to reduce IO overhead.
- Keeps tool initialization simple and deterministic.

Output defaults:
- If output_dir is not provided, uses output/<slugified objective>.

Failure handling:
- Unknown agent names raise a ValueError.
- If plan dependencies cannot be satisfied, execution stops with partial output.
