#!/usr/bin/env python3
"""Pass off a handoff.json to N sub-agents.

Behavior:
- Read a handoff JSON file (default: provided path).
- Generate N subpayloads (default 3) that include the original payload and a `subtask_id`.
- For each sub-agent i, if env var `AGENT_{i}_ENDPOINT` is set, POST the subpayload to that endpoint using `HttpTool`.
- Otherwise write the subpayload to `artifacts/<run_id>/subagent-{i}.json` under repo root.

This is intentionally simple and safe: remote POSTs are optional and network failures are returned
as non-zero exit codes but do not raise exceptions.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from swarm.tools.http import HttpTool


def make_subpayload(original: dict, i: int, total: int) -> dict:
    return {
        "subtask_id": i,
        "total": total,
        "parent": original,
        "instructions": f"Handle portion {i} of {total} for the objective."
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", required=True, help="Path to handoff.json")
    parser.add_argument("--run-id", "-r", default="passoff", help="Run id for artifacts")
    parser.add_argument("--count", "-n", type=int, default=3, help="Number of sub-agents (default 3)")
    parser.add_argument("--output-root", "-o", default="artifacts", help="Artifacts root relative to repo")
    parser.add_argument("--timeout", "-t", type=float, default=15.0)
    args = parser.parse_args(argv)

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 2

    try:
        original = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: failed to parse JSON: {exc}", file=sys.stderr)
        return 2

    http = HttpTool()
    repo_root = Path(__file__).resolve().parents[1]
    artifacts_dir = repo_root / args.output_root / args.run_id
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    overall_ok = True
    for i in range(1, args.count + 1):
        sub = make_subpayload(original, i, args.count)
        endpoint = os.environ.get(f"AGENT_{i}_ENDPOINT")
        if endpoint:
            resp = http.post(endpoint, sub, timeout=args.timeout)
            ok = resp.status and resp.status < 400
            print(f"POST -> agent {i} {endpoint} status={resp.status}")
            print(resp.text)
            overall_ok = overall_ok and ok
        else:
            out = artifacts_dir / f"subagent-{i}.json"
            out.write_text(json.dumps(sub, indent=2), encoding="utf-8")
            print(f"WROTE: {out}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
