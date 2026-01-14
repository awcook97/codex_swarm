from types import SimpleNamespace

from swarm.agents.researcher import (
    _build_search_queries,
    _clean_duckduckgo_url,
    _duckduckgo_results_from_html,
    _resolve_search_settings,
)


def test_clean_duckduckgo_url():
    url = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fdocs"
    assert _clean_duckduckgo_url(url) == "https://example.com/docs"


def test_parse_duckduckgo_html_results():
    html = """
    <html>
      <body>
        <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com">Example Domain</a>
        <span class="result__snippet">Simple test snippet.</span>
        <a class="result-link" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org">Example Org</a>
        <td class="result-snippet">Another snippet.</td>
      </body>
    </html>
    """
    results = _duckduckgo_results_from_html(html)
    assert len(results) == 2
    assert results[0]["title"] == "Example Domain"
    assert results[0]["url"] == "https://example.com"
    assert "snippet" in results[0]
    assert results[1]["title"] == "Example Org"
    assert results[1]["url"] == "https://example.org"


def test_build_search_queries_includes_prompt_terms():
    queries = _build_search_queries(
        "Design a landing page for a small indie bookstore.", max_queries=5
    )
    assert queries
    joined = " ".join(queries)
    assert "landing page" in joined
    assert "bookstore" in joined


def test_resolve_search_defaults_to_duckduckgo(monkeypatch):
    for key in [
        "SWARM_SEARCH_PROVIDER",
        "SEARCH_PROVIDER",
        "SEARXNG_URL",
        "SEARCH_ENDPOINT",
        "SERPER_API_KEY",
        "SERPAPI_API_KEY",
        "BRAVE_API_KEY",
        "BING_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)
    config = SimpleNamespace(
        search_provider=None,
        search_endpoint=None,
        search_api_key=None,
        search_max_results=5,
    )
    provider, endpoint, api_key, max_results, error = _resolve_search_settings(config)
    assert provider == "duckduckgo"
    assert endpoint is None
    assert api_key is None
    assert max_results == 5
    assert error is None
