from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
from html.parser import HTMLParser
from typing import Any

from swarm.agents.base import AgentContext, BaseAgent


class ResearcherAgent(BaseAgent):
    def __init__(self, instructions: str | None = None) -> None:
        super().__init__(
            name="researcher",
            role="Researcher",
            instructions=instructions or "Gather context relevant to the objective.",
        )

    async def run(self, task: str, context: AgentContext) -> dict[str, Any]:
        self.log(context, f"Starting research task: {task}")
        search_summary = ""
        search_error = None
        references: list[str] = []
        http_notes = ""
        if context.config.enable_http and not context.dry_run:
            try:
                search_summary, search_refs, search_error = _fetch_search_results(
                    context.http, context.objective, context.config
                )
                if search_refs:
                    references.extend(search_refs)
            except Exception as exc:  # pragma: no cover - network path
                search_error = f"Web search failed: {exc}"

            if search_summary:
                http_notes = f"\n\nWeb search results:\n{search_summary}"
            elif search_error:
                http_notes = f"\n\nWeb search issue:\n{search_error}"

        prompt_lines = [
            "ROLE: Researcher",
            "Return JSON with fields: summary, deliverable, needs.",
            "Focus on the subject matter in the objective; avoid web design advice unless the objective is about web design.",
            "If a website is requested, assume general web knowledge and research the domain instead.",
            f"Objective: {context.objective}",
            f"Task: {task}",
        ]
        if search_summary or search_error:
            prompt_lines.append("Sources:")
            prompt_lines.append(search_summary or search_error or "")
        response_text = await self.complete(context, "\n".join(prompt_lines))
        summary = None
        deliverable = None
        needs: list[str] = []
        try:
            payload = json.loads(response_text)
            summary = payload.get("summary")
            deliverable = payload.get("deliverable")
            needs = payload.get("needs") or []
        except json.JSONDecodeError:
            summary = None

        if context.config.enable_http and not context.dry_run and not search_summary:
            try:
                summary_text, refs = _fetch_wikipedia_summary(context.http, context.objective)
                references.extend(refs)
                if summary_text:
                    http_notes = (
                        f"{http_notes}\n\nWikipedia summary:\n{summary_text}"
                        if http_notes
                        else f"\n\nWikipedia summary:\n{summary_text}"
                    )
            except Exception as exc:  # pragma: no cover - network path
                http_notes = (
                    f"{http_notes}\n\nWikipedia lookup failed: {exc}"
                    if http_notes
                    else f"\n\nWikipedia lookup failed: {exc}"
                )

        if summary is None:
            summary = (
                "Research stub: No HTTP calls made. Provide domain-focused guidance and assumptions "
                "based on the objective (avoid web design unless explicitly requested)."
            )
            lowered = context.objective.lower()
            if "animation" in lowered or "movie" in lowered:
                summary = (
                    f"{summary}\n\nSuggested deliverable: animated GIF (or short video).\n"
                    "Needs: gif encoder or video render pipeline.\n"
                    "Deliverable: animated gif"
                )
                deliverable = "gif"
                needs = ["gif encoder"]
        if http_notes:
            summary = f"{summary}{http_notes}"

        context.short_term.put(context.run_id, self.name, "research", summary)
        if deliverable:
            context.short_term.put(context.run_id, self.name, "deliverable", deliverable)
        if needs:
            context.short_term.put(context.run_id, self.name, "needs", needs)
        if references:
            context.short_term.put(context.run_id, self.name, "references", references)
        research_path = context.output_dir / "research.md"
        handoff_path = context.output_dir / "handoff.json"
        if not context.dry_run:
            context.filesystem.write_text(
                research_path,
                "\n".join(
                    [
                        "# Research Notes",
                        "",
                        f"Objective: {context.objective}",
                        "",
                        summary,
                        "",
                        "References:",
                        *references,
                        "",
                    ]
                ),
            )
            context.filesystem.write_text(
                handoff_path,
                json.dumps(
                    {
                        "summary": summary,
                        "deliverable": deliverable,
                        "needs": needs,
                        "references": references,
                    },
                    indent=2,
                ),
            )
        return {
            "summary": summary,
            "deliverable": deliverable,
            "needs": needs,
            "files": [str(research_path), str(handoff_path)],
        }


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    if not lowered:
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    return cleaned.strip("-")[:64]


def _fetch_wikipedia_summary(http: Any, objective: str) -> tuple[str, list[str]]:
    query = objective.strip()
    if not query:
        return "", []
    search_url = (
        "https://en.wikipedia.org/w/api.php?action=opensearch&search="
        + _url_escape(query)
        + "&limit=1&namespace=0&format=json"
    )
    response = http.get(search_url, timeout=6.0)
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError:
        return "", [response.url]
    if len(payload) < 2 or not payload[1]:
        return "", [response.url]
    title = str(payload[1][0]).replace(" ", "_")
    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    summary_response = http.get(summary_url, timeout=6.0)
    try:
        summary_payload = json.loads(summary_response.text)
        extract = summary_payload.get("extract") or ""
    except json.JSONDecodeError:
        extract = summary_response.text[:500]
    return extract[:500], [response.url, summary_response.url]


def _fetch_search_results(
    http: Any, objective: str, config: Any
) -> tuple[str, list[str], str | None]:
    queries = _build_search_queries(objective)
    if not queries:
        return "", [], "Empty search query."
    provider, endpoint, api_key, max_results, error = _resolve_search_settings(config)
    if error:
        return "", [], error
    if provider is None:
        return "", [], "Search provider not configured."
    last_error = None
    for query in queries:
        results, search_error = _run_search_query(http, provider, query, endpoint, api_key)
        if search_error:
            last_error = search_error
            continue
        if results:
            return _format_search_summary(provider, results, max_results)
    return "", [], last_error or "No results found."


def _build_search_queries(objective: str) -> list[str]:
    cleaned = _strip_web_terms(objective)
    queries: list[str] = []
    if cleaned:
        queries.append(cleaned)
    lowered = objective.lower()
    if "bookstore" in lowered or "book shop" in lowered or "bookshop" in lowered or "book " in lowered:
        queries.extend(
            [
                "independent bookstore community events",
                "indie bookstore merchandising displays",
                "bookstore reading nooks atmosphere",
                "how independent bookstores build community",
            ]
        )
    if not queries:
        queries.append(objective.strip())
    return _dedupe_queries(queries)


def _strip_web_terms(value: str) -> str:
    if not value:
        return ""
    lowered = value.lower()
    web_terms = [
        "landing page",
        "web page",
        "webpage",
        "website",
        "web site",
        "web",
        "site",
        "page",
        "ui",
        "ux",
        "frontend",
        "front-end",
        "html",
        "css",
        "javascript",
        "design",
        "layout",
        "template",
        "hero",
        "cta",
    ]
    for term in web_terms:
        lowered = lowered.replace(term, " ")
    cleaned = re.sub(r"[^a-z0-9\\s-]+", " ", lowered)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


def _dedupe_queries(queries: list[str]) -> list[str]:
    seen = set()
    output: list[str] = []
    for query in queries:
        key = " ".join(query.split()).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(key)
    return output


def _run_search_query(
    http: Any,
    provider: str,
    query: str,
    endpoint: str | None,
    api_key: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    if provider == "duckduckgo":
        return _duckduckgo_search(http, query)
    if provider == "searxng":
        if not endpoint:
            return [], "Searxng provider selected but no endpoint configured."
        base = endpoint.rstrip("/")
        if base.endswith("/search"):
            url = f"{base}?q={_url_escape(query)}&format=json"
        else:
            url = f"{base}/search?q={_url_escape(query)}&format=json"
        payload, error = _fetch_json(http, url)
        if error:
            return [], error
        items = payload.get("results", []) if isinstance(payload, dict) else []
        return [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("content"),
            }
            for item in items
            if isinstance(item, dict)
        ], None
    if provider == "serpapi":
        if not api_key:
            return [], "SERPAPI_API_KEY is required for serpapi."
        url = (
            "https://serpapi.com/search.json?engine=google&q="
            + _url_escape(query)
            + "&api_key="
            + _url_escape(api_key)
        )
        payload, error = _fetch_json(http, url)
        if error:
            return [], error
        items = payload.get("organic_results", []) if isinstance(payload, dict) else []
        return [
            {
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet"),
            }
            for item in items
            if isinstance(item, dict)
        ], None
    if provider == "serper":
        if not api_key:
            return [], "SERPER_API_KEY is required for serper."
        payload, error = _fetch_json(
            http,
            "https://google.serper.dev/search",
            payload={"q": query},
            headers={"X-API-KEY": api_key},
        )
        if error:
            return [], error
        items = payload.get("organic", []) if isinstance(payload, dict) else []
        return [
            {
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet"),
            }
            for item in items
            if isinstance(item, dict)
        ], None
    if provider == "bing":
        if not api_key:
            return [], "BING_API_KEY is required for bing."
        url = "https://api.bing.microsoft.com/v7.0/search?q=" + _url_escape(query)
        payload, error = _fetch_json(
            http, url, headers={"Ocp-Apim-Subscription-Key": api_key}
        )
        if error:
            return [], error
        items = payload.get("webPages", {}).get("value", []) if isinstance(payload, dict) else []
        return [
            {
                "title": item.get("name"),
                "url": item.get("url"),
                "snippet": item.get("snippet"),
            }
            for item in items
            if isinstance(item, dict)
        ], None
    if provider == "brave":
        if not api_key:
            return [], "BRAVE_API_KEY is required for brave."
        url = "https://api.search.brave.com/res/v1/web/search?q=" + _url_escape(query)
        payload, error = _fetch_json(
            http, url, headers={"X-Subscription-Token": api_key}
        )
        if error:
            return [], error
        items = payload.get("web", {}).get("results", []) if isinstance(payload, dict) else []
        return [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("description"),
            }
            for item in items
            if isinstance(item, dict)
        ], None
    return [], f"Unknown search provider: {provider}"


def _resolve_search_settings(
    config: Any,
) -> tuple[str | None, str | None, str | None, int, str | None]:
    provider = getattr(config, "search_provider", None) or os.getenv("SWARM_SEARCH_PROVIDER") or os.getenv(
        "SEARCH_PROVIDER"
    )
    if provider:
        provider = provider.strip().lower()
        if provider == "ddg":
            provider = "duckduckgo"
        if provider == "auto":
            provider = None
    endpoint = getattr(config, "search_endpoint", None) or os.getenv("SEARXNG_URL") or os.getenv(
        "SEARCH_ENDPOINT"
    )
    max_results = _search_max_results(config)
    api_key = getattr(config, "search_api_key", None)

    if provider == "google":
        if api_key or os.getenv("SERPER_API_KEY"):
            provider = "serper"
        elif os.getenv("SERPAPI_API_KEY"):
            provider = "serpapi"
        elif os.getenv("BING_API_KEY"):
            provider = "bing"
        elif os.getenv("BRAVE_API_KEY"):
            provider = "brave"
        else:
            return None, endpoint, None, max_results, (
                "Google search requested but no API key found. "
                "Set SERPER_API_KEY, SERPAPI_API_KEY, BING_API_KEY, or BRAVE_API_KEY."
            )

    if provider is None:
        if endpoint:
            provider = "searxng"
        elif os.getenv("SERPER_API_KEY"):
            provider = "serper"
        elif os.getenv("SERPAPI_API_KEY"):
            provider = "serpapi"
        elif os.getenv("BRAVE_API_KEY"):
            provider = "brave"
        elif os.getenv("BING_API_KEY"):
            provider = "bing"
        else:
            provider = "duckduckgo"

    if provider in {"serper", "serpapi", "bing", "brave"} and not api_key:
        api_key = os.getenv(_provider_key_env(provider))
        if not api_key:
            return (
                None,
                endpoint,
                None,
                max_results,
                f"{_provider_key_env(provider)} is required for {provider}.",
            )

    return provider, endpoint, api_key, max_results, None


def _provider_key_env(provider: str) -> str:
    mapping = {
        "serper": "SERPER_API_KEY",
        "serpapi": "SERPAPI_API_KEY",
        "bing": "BING_API_KEY",
        "brave": "BRAVE_API_KEY",
    }
    return mapping.get(provider, "SEARCH_API_KEY")


def _search_max_results(config: Any) -> int:
    raw = getattr(config, "search_max_results", None) or os.getenv("SEARCH_MAX_RESULTS")
    try:
        value = int(raw) if raw is not None else 5
    except (TypeError, ValueError):
        value = 5
    return max(1, min(value, 10))


def _fetch_json(
    http: Any,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[dict[str, Any], str | None]:
    if payload is None:
        response = http.get(url, timeout=8.0, headers=headers)
    else:
        response = http.post(url, payload, timeout=10.0, headers=headers)
    if response.status < 200 or response.status >= 300:
        detail = response.text.replace("\n", " ").strip()
        detail = detail[:200] + "..." if len(detail) > 200 else detail
        return {}, f"HTTP {response.status} from {response.url}: {detail}"
    try:
        return json.loads(response.text), None
    except json.JSONDecodeError as exc:
        return {}, f"Invalid JSON from {response.url}: {exc}"


def _duckduckgo_search(http: Any, query: str) -> tuple[list[dict[str, str]], str | None]:
    headers = {"Accept-Language": "en-US,en;q=0.8"}
    html_url = "https://html.duckduckgo.com/html/?q=" + _url_escape(query)
    response = http.get(html_url, timeout=8.0, headers=headers)
    if response.status < 200 or response.status >= 300:
        lite_url = "https://lite.duckduckgo.com/lite/?q=" + _url_escape(query)
        response = http.get(lite_url, timeout=8.0, headers=headers)
    if response.status < 200 or response.status >= 300:
        return [], f"HTTP {response.status} from {response.url}"
    results = _duckduckgo_results_from_html(response.text)
    if not results:
        return [], "No results parsed from DuckDuckGo HTML."
    return results, None


def _duckduckgo_results_from_html(text: str) -> list[dict[str, str]]:
    parser = _DuckDuckGoParser()
    parser.feed(text)
    return parser.results


class _DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._capture_title = False
        self._capture_snippet = False
        self._current_href: str | None = None
        self._current_title_parts: list[str] = []
        self._snippet_target: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: (value or "") for key, value in attrs}
        class_value = attr_map.get("class", "")
        if tag == "a" and ("result__a" in class_value or "result-link" in class_value):
            href = attr_map.get("href")
            if href:
                self._current_href = href
                self._current_title_parts = []
                self._capture_title = True
        if tag in {"div", "span", "td", "a"} and (
            "result__snippet" in class_value or "result-snippet" in class_value
        ):
            self._capture_snippet = True
            self._snippet_target = self.results[-1] if self.results else None

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture_title:
            self._capture_title = False
            title = html.unescape("".join(self._current_title_parts)).strip()
            href = self._current_href or ""
            url = _clean_duckduckgo_url(href)
            if title and url:
                self.results.append({"title": title, "url": url, "snippet": ""})
            self._current_href = None
            self._current_title_parts = []
        if self._capture_snippet and tag in {"div", "span", "td", "a"}:
            self._capture_snippet = False
            self._snippet_target = None

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self._current_title_parts.append(data)
        elif self._capture_snippet and self._snippet_target is not None:
            self._snippet_target["snippet"] += data


def _clean_duckduckgo_url(value: str) -> str:
    if not value:
        return ""
    parsed = urllib.parse.urlparse(value)
    if parsed.netloc and parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        params = urllib.parse.parse_qs(parsed.query)
        target = params.get("uddg", [""])[0]
        return urllib.parse.unquote(target) if target else ""
    if value.startswith("/l/?"):
        params = urllib.parse.parse_qs(parsed.query)
        target = params.get("uddg", [""])[0]
        return urllib.parse.unquote(target) if target else ""
    if value.startswith("//"):
        return "https:" + value
    if value.startswith("/"):
        return "https://duckduckgo.com" + value
    return value


def _format_search_summary(
    provider: str, results: list[dict[str, Any]], max_results: int
) -> tuple[str, list[str], str | None]:
    lines = [f"Provider: {provider}"]
    references: list[str] = []
    for item in results[:max_results]:
        url = item.get("url")
        if not isinstance(url, str) or not url:
            continue
        title = _clean_line(item.get("title") or url)
        snippet = _clean_line(item.get("snippet") or "", limit=180)
        domain = _domain_from_url(url)
        if snippet:
            lines.append(f"- {title} ({domain}) - {snippet}")
        else:
            lines.append(f"- {title} ({domain})")
        references.append(url)
    if len(lines) == 1:
        return "", [], "No results found."
    return "\n".join(lines), references, None


def _clean_line(value: Any, limit: int = 120) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = " ".join(value.split())
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - 3].rstrip() + "..."
    return cleaned


def _domain_from_url(value: str) -> str:
    try:
        parsed = urllib.parse.urlparse(value)
        return parsed.netloc or value
    except Exception:
        return value


def _url_escape(value: str) -> str:
    return urllib.parse.quote(value.strip())
