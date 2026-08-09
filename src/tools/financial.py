"""
yfinance wrapper for market/financial data.
Used by: Company Ingestion, Margin Analysis (primary), Growth Forecast agents.
"""

from __future__ import annotations

import yfinance as yf


# ─────────────────────────────────────────────────────────────────────────────
# Company profile / ticker verification
#
# Used by Company Ingestion to confirm an LLM-extracted candidate is a
# real, public company before adding it to the pipeline.
# ─────────────────────────────────────────────────────────────────────────────
def get_company_profile(ticker: str) -> dict | None:
    """
    Basic company info + ticker verification.

    Args:
        ticker: Stock ticker symbol, e.g. "NVDA".

    Returns:
        Dict with ticker/company_name/sector/industry if valid,
        None if the ticker is invalid, delisted, or unverifiable.

    Note:
        This is a SYNC call (yfinance has no native async support).
        Callers running inside an async node must wrap it:
            info = await asyncio.to_thread(get_company_profile, ticker)
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or "longName" not in info:
            return None

        return {
            "ticker": ticker,
            "company_name": info.get("longName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
    except Exception as e:  # noqa: BLE001
        print(f"[get_company_profile] Failed to verify '{ticker}': {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Operating margin
#
# Used by Margin Analysis to compute margin_score (bracket-normalized
# 0-5 scale). operatingMargins from yfinance is already a decimal
# (e.g. 0.42 for 42%), not a percentage — no conversion needed.
# ─────────────────────────────────────────────────────────────────────────────
def get_operating_margin(ticker: str) -> float | None:
    """
    Operating margin as a decimal (e.g. 0.42 for 42%).

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Operating margin as a float, or None if unavailable.
    """
    try:
        stock = yf.Ticker(ticker)
        margin = stock.info.get("operatingMargins")
        return float(margin) if margin is not None else None
    except Exception as e:  # noqa: BLE001
        print(f"[get_operating_margin] Failed for '{ticker}': {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 3-year revenue CAGR
#
# Used by Growth Forecast as a historical baseline signal. stock.financials
# returns annual figures, most recent column first — we need at least
# 4 years of data to compute a 3-year CAGR.
# ─────────────────────────────────────────────────────────────────────────────
def get_3yr_revenue_cagr(ticker: str) -> float | None:
    """
    3-year revenue CAGR as a decimal (e.g. 0.28 for 28%).

    Args:
        ticker: Stock ticker symbol.

    Returns:
        CAGR as a float, or None if unavailable — either fewer than
        4 years of financial history, or the 3-years-ago revenue was
        zero/negative (CAGR undefined in that case).
    """
    try:
        stock = yf.Ticker(ticker)
        financials = stock.financials
        revenue = financials.loc["Total Revenue"]

        if len(revenue) < 4:
            return None

        latest, three_yrs_ago = revenue.iloc[0], revenue.iloc[3]

        if three_yrs_ago <= 0:
            return None

        cagr = (latest / three_yrs_ago) ** (1 / 3) - 1
        return float(cagr)
    except Exception as e:  # noqa: BLE001
        print(f"[get_3yr_revenue_cagr] Failed for '{ticker}': {e}")
        return None
