"""
vendor/search_provider.py — Semantic Scholar API client.

Adapted from scholar-agent/src/scholar_agent/engine/search_providers/
(Semantic Scholar provider).

Stripped:
  - @mcp.tool decorators and FastMCP imports
  - BM25 index, caching, and daily-workflow dependencies
  - Server registration code

Retained:
  - DOI lookup via GET /paper/{doi}
  - Title search via GET /paper/search
  - HTTP 429 retry/backoff logic (max 3 retries, 5-second wait)
  - Field extraction: year, venue, citationCount, authors
"""

import os
import time
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://api.semanticscholar.org/graph/v1"
_FIELDS = "year,venue,citationCount,authors,title,abstract,externalIds"
_MAX_RETRIES = 3
_RETRY_WAIT_SECONDS = 5


def _get_headers() -> dict:
    """Return request headers, including the API key if set in the environment."""
    headers = {}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def _rate_limit_delay() -> float:
    """Return the pre-request delay: 1s with API key, 3s without."""
    return 1.0 if os.getenv("SEMANTIC_SCHOLAR_API_KEY", "") else 3.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_with_retry(url: str, params: dict | None = None) -> requests.Response | None:
    """
    Perform a GET request with automatic retry on HTTP 429 (rate limit).

    Retries up to _MAX_RETRIES times, waiting _RETRY_WAIT_SECONDS between
    each attempt. Returns the Response object on success (2xx), or None if
    all retries are exhausted or a non-429 error occurs.

    Non-429 HTTP errors are returned as-is so the caller can inspect the
    status code and emit an appropriate warning.
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        time.sleep(_rate_limit_delay())  # respect rate limit before every request
        try:
            response = requests.get(url, params=params, headers=_get_headers(), timeout=15)
        except requests.RequestException as exc:
            # Network-level error — treat as a non-retryable failure.
            raise RuntimeError(f"Network error contacting Semantic Scholar: {exc}") from exc

        if response.status_code == 429:
            wait = 60 * attempt  # 60s, 120s, 180s — matches AutoSci's escalating backoff
            if attempt < _MAX_RETRIES:
                time.sleep(wait)
                continue
            else:
                return None

        # Any other status code (success or non-429 error) — return immediately.
        return response

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def query_by_doi(doi: str) -> dict | None:
    """
    Look up a paper by DOI via the Semantic Scholar API.

    GET https://api.semanticscholar.org/graph/v1/paper/{doi}
        ?fields=year,venue,citationCount,authors

    Returns:
        A dict with keys ``year``, ``venue``, ``citationCount``, ``authors``
        on success, or ``None`` if the paper was not found, the API returned
        an error, or all 429 retries were exhausted.

    Raises:
        RuntimeError: on network-level failure.
    """
    url = f"{_BASE_URL}/paper/DOI:{doi}"
    params = {"fields": _FIELDS}

    response = _get_with_retry(url, params)
    if response is None:
        return None

    if response.status_code == 200:
        data = response.json()
        return _extract_fields(data)

    # Non-200, non-429 — signal the error status to the caller.
    response.raise_for_status()
    return None


def query_by_title(title: str) -> dict | None:
    """
    Search for a paper by title via the Semantic Scholar API.

    GET https://api.semanticscholar.org/graph/v1/paper/search
        ?query={title}&fields=year,venue,citationCount,authors&limit=1

    Returns:
        A dict with keys ``year``, ``venue``, ``citationCount``, ``authors``
        for the top result, or ``None`` if no results were found, the API
        returned an error, or all 429 retries were exhausted.

    Raises:
        RuntimeError: on network-level failure.
    """
    url = f"{_BASE_URL}/paper/search"
    params = {"query": title, "fields": _FIELDS, "limit": 1}

    response = _get_with_retry(url, params)
    if response is None:
        return None

    if response.status_code == 200:
        data = response.json()
        papers = data.get("data", [])
        if not papers:
            return None
        return _extract_fields(papers[0])

    response.raise_for_status()
    return None


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

def _extract_fields(paper_data: dict) -> dict:
    """
    Extract the required fields from a Semantic Scholar paper dict.

    Returns a dict with keys: year, venue, citationCount, authors, title.
    Missing fields default to None or [] for authors.
    """
    return {
        "year": paper_data.get("year"),
        "venue": paper_data.get("venue"),
        "citationCount": paper_data.get("citationCount"),
        "authors": paper_data.get("authors", []),
        "title": paper_data.get("title"),
        "externalIds": paper_data.get("externalIds") or {},
    }
