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
    parser.add_argument("-o", "--output-dir", type=str, default=None, help="Output directory")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--max-steps", type=int, default=None, help="Maximum steps to execute")
    parser.add_argument("--dry-run", action="store_true", help="Plan and log without writing files")
    parser.add_argument(
        "--llm-provider",
        type=str,
        default=None,
        choices=["mock", "ollama"],
        help="LLM provider to use",
    )
    parser.add_argument("--ollama-model", type=str, default=None, help="Ollama model name")
    parser.add_argument("--ollama-url", type=str, default=None, help="Ollama base URL")
    parser.add_argument("--ollama-endpoint", type=str, default=None, help="Ollama endpoint")
    parser.add_argument("--ollama-timeout", type=int, default=None, help="Ollama request timeout (s)")
    parser.add_argument("--ollama-retries", type=int, default=None, help="Ollama retry count")
    parser.add_argument("--enable-http", action="store_true", help="Enable HTTP for research")
    parser.add_argument("--log-llm", action="store_true", help="Log LLM prompts/responses")
    parser.add_argument(
        "--search-provider",
        type=str,
        default=None,
        help="Web search provider (auto, duckduckgo, searxng, serpapi, serper, brave, bing, google)",
    )
    parser.add_argument(
        "--search-endpoint",
        type=str,
        default=None,
        help="Search endpoint base URL (used by searxng or custom providers)",
    )
    parser.add_argument(
        "--search-api-key",
        type=str,
        default=None,
        help="Search API key (overrides provider-specific env vars)",
    )
    parser.add_argument(
        "--search-max-results",
        type=int,
        default=None,
        help="Max search results to include in research (default 5)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    config = SwarmConfig.from_repo_root(repo_root)
    if args.llm_provider:
        config.llm_provider = args.llm_provider
    if args.ollama_model:
        config.ollama_model = args.ollama_model
    if args.ollama_url:
        config.ollama_url = args.ollama_url
    if args.ollama_endpoint:
        config.ollama_endpoint = args.ollama_endpoint
    if args.ollama_timeout is not None:
        config.ollama_timeout = args.ollama_timeout
    if args.ollama_retries is not None:
        config.ollama_retries = args.ollama_retries
    if args.enable_http:
        config.enable_http = True
    if args.log_llm:
        config.log_llm = True
    if args.search_provider:
        config.search_provider = args.search_provider
    if args.search_endpoint:
        config.search_endpoint = args.search_endpoint
    if args.search_api_key:
        config.search_api_key = args.search_api_key
    if args.search_max_results is not None:
        config.search_max_results = args.search_max_results
    coordinator = Coordinator(config=config)

    result = asyncio.run(
        coordinator.run(
            objective=args.objective,
            run_id=args.run_id,
            output_dir=args.output_dir,
            max_steps=args.max_steps,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    )

    print(result["final"])
    print(f"Output: {result['output_dir']}")
    return 0
