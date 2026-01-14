#!/usr/bin/env python3
"""Simple script to POST a handoff JSON to a configured Codex endpoint.

Usage:
  scripts/passoff_to_codex.py --file output/.../handoff.json --endpoint https://example.com/receive

If `CODEX_ENDPOINT` env var is set, it will be used as the default endpoint.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from swarm.tools.http import HttpTool


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", required=True, help="Path to handoff.json")
    parser.add_argument("--endpoint", "-e", help="Codex endpoint URL (or set CODEX_ENDPOINT)")
    parser.add_argument("--timeout", "-t", type=float, default=15.0)
    args = parser.parse_args(argv)

    endpoint = args.endpoint or os.environ.get("CODEX_ENDPOINT")
    if not endpoint:
        print("ERROR: no endpoint provided and CODEX_ENDPOINT not set", file=sys.stderr)
        return 2

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 2

    payload = json.loads(path.read_text(encoding="utf-8"))

    tool = HttpTool()
    resp = tool.post(endpoint, payload, timeout=args.timeout)
    print(f"POST {endpoint} -> status={resp.status}")
    print(resp.text)
    return 0 if resp.status and resp.status < 400 else 1


if __name__ == "__main__":
    raise SystemExit(main())
