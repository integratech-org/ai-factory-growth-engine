"""
src/tools/search.py

Tavily search wrapper.
Used by: Company Ingestion, Moat Analysis, Growth Forecast, Risk Adjustment agents.
"""

from __future__ import annotations

import os

from tavily import TavilyClient

# ─────────────────────────────────────────────────────────────────────────────
# Client init
#
# Reads API key from env (loaded via python-dotenv at the entry point —
# see streamlit_app.py / main.py). Single client instance, reused across
# all search calls within a process.
# ─────────────────────────────────────────────────────────────────────────────
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


# ─────────────────────────────────────────────────────────────────────────────
# Simple in-memory cache
#
# Avoids re-searching the same query multiple times within a single
# pipeline run (e.g. if two agents happen to search similar terms for
# the same ticker). Cleared automatically each time the process restarts —
# not persisted, since search results are only relevant within one run.
# ─────────────────────────────────────────────────────────────────────────────
_query_cache: dict[str, list[dict]] = {}


def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Runs a Tavily search and returns normalized results.

    Generic search utility used across multiple agents:
      - Company Ingestion: find public companies per segment
      - Moat Analysis: competitive positioning, ecosystem lock-in news
      - Growth Forecast: earnings calls, backlog, capex announcements
      - Risk Adjustment: customer concentration, execution risk news

    Args:
        query:       Search query string.
        max_results: Max number of results to return (default 5).

    Returns:
        List of dicts: [{"title": ..., "url": ..., "content": ...}, ...]
        Returns an empty list if the search fails (does not raise) —
        callers should treat "no results" as a normal, handleable case.
    """
    if query in _query_cache:
        return _query_cache[query]

    try:
        response = tavily_client.search(query=query, max_results=max_results)
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
            }
            for r in response.get("results", [])
        ]
    except Exception as e:  # noqa: BLE001
        print(f"[tavily_search] Tavily search failed for query '{query}': {e}")
        results = []

    _query_cache[query] = results
    return results
