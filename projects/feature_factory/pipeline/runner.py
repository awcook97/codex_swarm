from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from swarm import RunResult, RunSpec, SwarmConfig, SwarmRunner


@dataclass(slots=True)
class FeatureSpec:
    feature_id: str
    objective: str
    dry_run: bool = False
    max_steps: int | None = None


@dataclass(slots=True)
class BatchSpec:
    batch_id: str
    features: list[FeatureSpec]
    dry_run: bool = False
    max_steps: int | None = None


def normalize_batch(payload: dict[str, Any]) -> BatchSpec:
    if not isinstance(payload, dict):
        raise ValueError("Batch payload must be a JSON object")
    batch_id = payload.get("batch_id")
    if not isinstance(batch_id, str) or not batch_id:
        raise ValueError("batch_id is required")
    features_payload = payload.get("features")
    if not isinstance(features_payload, list) or not features_payload:
        raise ValueError("features must be a non-empty list")
    batch_dry_run = bool(payload.get("dry_run", False))
    batch_max_steps = payload.get("max_steps")
    if batch_max_steps is not None and not isinstance(batch_max_steps, int):
        raise ValueError("max_steps must be an integer")

    features: list[FeatureSpec] = []
    for item in features_payload:
        if not isinstance(item, dict):
            raise ValueError("Each feature must be an object")
        feature_id = item.get("feature_id")
        objective = item.get("objective")
        if not isinstance(feature_id, str) or not feature_id:
            raise ValueError("feature_id is required")
        if not isinstance(objective, str) or not objective:
            raise ValueError("objective is required")
        feature_dry_run = bool(item.get("dry_run", batch_dry_run))
        feature_max_steps = item.get("max_steps", batch_max_steps)
        if feature_max_steps is not None and not isinstance(feature_max_steps, int):
            raise ValueError("max_steps must be an integer")
        features.append(
            FeatureSpec(
                feature_id=feature_id,
                objective=objective,
                dry_run=feature_dry_run,
                max_steps=feature_max_steps,
            )
        )
    return BatchSpec(
        batch_id=batch_id,
        features=features,
        dry_run=batch_dry_run,
        max_steps=batch_max_steps,
    )


def run_batch(batch: BatchSpec, repo_root: Path, concurrency: int = 4) -> list[RunResult]:
    config = SwarmConfig.from_repo_root(repo_root)
    runner = SwarmRunner(config=config, concurrency=concurrency)
    run_specs = [
        RunSpec(
            objective=feature.objective,
            run_id=feature.feature_id,
            dry_run=feature.dry_run,
            max_steps=feature.max_steps,
        )
        for feature in batch.features
    ]
    return _run_specs(runner, run_specs)


def _run_specs(runner: SwarmRunner, run_specs: list[RunSpec]) -> list[RunResult]:
    return asyncio.run(runner.run(run_specs))
