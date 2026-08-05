"""
yfinance wrapper for market/financial data.
Used by: Company Ingestion, Margin Analysis (primary), Growth Forecast agents.
"""

# TODO: def get_operating_margin(ticker: str) -> float
#   - pull from yfinance, wrap sync call in asyncio.to_thread()
# TODO: def get_3yr_revenue_cagr(ticker: str) -> float
#   - used for Growth Forecast Score component
# TODO: def get_company_profile(ticker: str) -> dict
#   - basic info for Company Ingestion agent
