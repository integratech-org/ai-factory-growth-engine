"""yfinance helpers used by the AI Factory pipeline."""

from __future__ import annotations

import asyncio
from typing import Any

import yfinance as yf


def get_company_profile(
    ticker: str,
) -> dict[str, Any]:
    """Return basic public-company metadata from Yahoo Finance."""

    try:
        info = yf.Ticker(ticker).info

        if not info:
            return {}

        return {
            "symbol": info.get("symbol", ticker),
            "shortName": info.get("shortName"),
            "longName": info.get("longName"),
            "exchange": info.get("exchange"),
            "quoteType": info.get("quoteType"),
            "country": info.get("country"),
        }

    except Exception as exc:
        print(f"[get_company_profile] Failed for {ticker}: {exc}")
        return {}


async def get_company_profile_async(
    ticker: str,
) -> dict[str, Any]:
    """Async wrapper around the synchronous yfinance call."""

    return await asyncio.to_thread(
        get_company_profile,
        ticker,
    )
