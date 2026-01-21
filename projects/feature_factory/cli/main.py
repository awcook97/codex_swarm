from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="feature-factory")
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8080",
        help="Base URL for the Feature Factory API",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    submit = sub.add_parser("submit", help="Submit a batch spec")
    submit.add_argument("--file", required=True, help="Path to batch spec JSON")

    status = sub.add_parser("status", help="Check batch status")
    status.add_argument("batch_id", help="Batch identifier")

    fetch = sub.add_parser("fetch", help="Fetch a feature result")
    fetch.add_argument("feature_id", help="Feature identifier")
    return parser


def _request_json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload else None
    headers = {"Content-Type": "application/json"} if payload else {}
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"API error {exc.code}: {body}") from exc


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    base_url = args.api_url.rstrip("/")

    if args.command == "submit":
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
        res = _request_json(f"{base_url}/batches", method="POST", payload=payload)
        print(json.dumps(res, indent=2))
        return 0
    if args.command == "status":
        res = _request_json(f"{base_url}/batches/{args.batch_id}")
        print(json.dumps(res, indent=2))
        return 0
    if args.command == "fetch":
        res = _request_json(f"{base_url}/features/{args.feature_id}")
        print(json.dumps(res, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
