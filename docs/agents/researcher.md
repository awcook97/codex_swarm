# Researcher Agent

I gather context and assumptions to support downstream work.

Purpose:
- Collect relevant facts or constraints for the objective.
- Summarize findings for the planner and coder.

Inputs:
- task: research objective or sub-task
- context: shared run context

Outputs:
- {"summary": "..."}

Constraints:
- Use HTTP only when enable_http is true and not in dry-run.
- Be explicit about assumptions and data sources.
- Keep summaries short and actionable.
- When HTTP is enabled, prefer web search results; fall back to Wikipedia only if search returns no results.
- Avoid fixating on the deliverable format; include both domain and solution angles when they help solve the objective.
- Favor breadth: cover multiple angles that help solve the objective (constraints, examples, risks, options) instead of repeating the prompt.

Web search configuration:
- CLI: `--search-provider`, `--search-endpoint`, `--search-api-key`, `--search-max-results`
- Optional: `--search-max-queries` to cap how many different queries run per task.
- Providers: `duckduckgo` (no API key, HTML scrape, default when no provider configured), `searxng`, `serper`, `serpapi`, `brave`, `bing`, `google` (alias)
- Env vars: `SEARXNG_URL`, `SEARCH_ENDPOINT`, `SERPER_API_KEY`, `SERPAPI_API_KEY`, `BRAVE_API_KEY`, `BING_API_KEY`, `SEARCH_MAX_RESULTS`, `SEARCH_MAX_QUERIES`
