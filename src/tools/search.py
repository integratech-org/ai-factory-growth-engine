"""
Tavily search wrapper.
Used by: Company Ingestion, Moat Analysis, Growth Forecast, Risk Adjustment agents.
"""

# TODO: init Tavily client (load API key via python-dotenv)
# TODO: def tavily_search(query: str, max_results: int = 5) -> list[dict]
#   - wrap Tavily API call
#   - return normalized list of {title, url, content} dicts
# TODO: consider caching repeated queries per company/ticker within a run
