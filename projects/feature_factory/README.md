# Feature Factory Orchestrator

## Scope (MVP)
Build a system that accepts multiple feature requests and runs them in parallel using the swarm runner. Each feature run can spawn follow-up runs for tests, docs, or refactors. The system aggregates outputs into a release bundle with a summary, status, and links to artifacts.

## Components
- **Web app (`projects/feature_factory/web/`)**: Dashboard to submit batches, view run status, and browse artifacts.
- **API (`projects/feature_factory/api/`)**: Service that accepts batch requests, schedules runs, and returns status/results.
- **Data pipeline (`projects/feature_factory/pipeline/`)**: Ingests batch specs, normalizes tasks, and feeds the runner.
- **CLI (`projects/feature_factory/cli/`)**: Local tool to submit batches and fetch results.

## Quick Start
1. Start the API server:
   - `python -m projects.feature_factory.api.app`
2. Optional: start the standalone web server:
   - `python -m projects.feature_factory.web.app`
3. Submit the sample batch:
   - `python -m projects.feature_factory.cli.main submit --file projects/feature_factory/docs/sample_batch.json`

## Data Model (initial)
- `Batch`: id, created_at, status, features[]
- `Feature`: id, title, objective, status, run_id, artifacts[]
- `Artifact`: type, path, summary

## Interfaces (initial)
- API:
  - `POST /batches` → create a batch from JSON input
  - `GET /batches/{id}` → batch status + feature summaries
  - `GET /features/{id}` → full results + artifacts
- CLI:
  - `feature-factory submit --file specs.json`
  - `feature-factory status <batch-id>`
  - `feature-factory fetch <feature-id>`

## Execution Flow
1. API/CLI receives a batch spec.
2. Pipeline validates and expands each feature into a `RunSpec`.
3. `SwarmRunner` runs features concurrently.
4. Each run can spawn child runs via the spawner for tests/docs.
5. Results are aggregated and stored for the UI/API.

## Out of Scope (MVP)
- Authn/Authz
- Multi-tenant isolation
- Persistent job queue

## Deliverables
- Working API + CLI for batch submission and status
- Minimal web dashboard
- Pipeline runner that uses `SwarmRunner`
