from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from swarm.config import SwarmConfig
from swarm.coordinator import Coordinator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI Swarm coordinator.")
    parser.add_argument("objective", type=str, help="Objective for the swarm")
    parser.add_argument("--run-id", type=str, default=None, help="Override run identifier")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--max-steps", type=int, default=None, help="Maximum steps to execute")
    parser.add_argument("--dry-run", action="store_true", help="Plan and log without writing files")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    config = SwarmConfig.from_repo_root(repo_root)
    coordinator = Coordinator(config=config)

    result = asyncio.run(
        coordinator.run(
            objective=args.objective,
            run_id=args.run_id,
            max_steps=args.max_steps,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    )

    print(result["final"])
    print(f"Artifacts: {result['artifacts_dir']}")
    return 0
