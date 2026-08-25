"""
src/tools/sec.py

SEC EDGAR wrapper via edgartools.
Used by: Company Ingestion (revenue exposure), Moat Analysis,
Margin Analysis (backup), Risk Adjustment agents.
"""

from __future__ import annotations

import os
from typing import Any, cast

from edgar import Company, set_identity

# SEC EDGAR requires a real identifying user-agent string (name + email)
# on every request — this is a compliance requirement, not optional.
set_identity(f"{os.getenv('SEC_EDGAR_NAME')} {os.getenv('SEC_EDGAR_EMAIL')}")


# ─────────────────────────────────────────────────────────────────────────────
# Latest 10-K fetch
#
# Shared base function — other functions below slice/extract specific
# sections from this. All edgartools calls are SYNC; callers running
# inside an async node must wrap with asyncio.to_thread().
# ─────────────────────────────────────────────────────────────────────────────


def get_latest_10k(ticker: str) -> dict | None:
    """
    Fetches metadata + full text of a company's most recent 10-K filing.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Dict with {ticker, filing_date, text}, or None if no 10-K found
        or the fetch failed.
    """
    try:
        company = Company(ticker)
        filings = company.get_filings(form="10-K")
        if not filings:
            return None

        latest = filings.latest()
        if latest is None:
            return None

        # edgartools' .latest() is loosely typed — it can come back as a
        # single EntityFiling OR as a collection (EntityFilings/list)
        # depending on version/call signature. hasattr() alone doesn't
        # narrow the type for Pyright here, so we normalize at runtime
        # AND cast() to tell the type checker we've confirmed the shape.
        if not hasattr(latest, "text"):
            try:
                latest = latest[0]  # type: ignore[index]
            except TypeError, IndexError, KeyError:
                return None

        filing = cast(Any, latest)

        text = filing.text()
        if not text:
            return None

        return {
            "ticker": ticker,
            "filing_date": str(filing.filing_date),
            "text": text,
        }
    except Exception as e:  # noqa: BLE001
        print(f"[get_latest_10k] Failed for '{ticker}': {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Revenue exposure excerpt (for Company Ingestion)
#
# Returns a truncated excerpt of the 10-K — business/segment discussion
# sections tend to appear early in the document. An LLM (in the calling
# agent) then interprets this text to extract an AI Factory revenue
# exposure estimate.
# ─────────────────────────────────────────────────────────────────────────────


def get_revenue_context_excerpt(ticker: str, max_chars: int = 15000) -> str | None:
    """
    Fetches the most recent 10-K and returns a truncated text excerpt
    for revenue/segment exposure analysis.

    Args:
        ticker:    Stock ticker symbol.
        max_chars: Max characters to return.

    Returns:
        Filing text excerpt, or None if unavailable.
    """
    filing = get_latest_10k(ticker)
    if filing is None:
        return None
    return filing["text"][:max_chars]


# ─────────────────────────────────────────────────────────────────────────────
# Risk Factors section (Item 1A) — for Risk Adjustment agent
#
# 10-Ks are structured with standard item numbers. Item 1A is always
# "Risk Factors". We do a simple text-boundary search between "Item 1A"
# and the next item marker since edgartools returns the filing as flat
# text, not pre-split by section.
# ─────────────────────────────────────────────────────────────────────────────


def get_risk_factors_section(ticker: str, max_chars: int = 20000) -> str | None:
    """
    Extracts the Item 1A (Risk Factors) section from a company's latest 10-K.

    Args:
        ticker:    Stock ticker symbol.
        max_chars: Max characters to return from the extracted section.

    Returns:
        Risk Factors section text, or None if the filing/section
        couldn't be found.

    Note:
        Section boundary detection via string search is best-effort —
        10-K formatting varies enough that this won't be 100% reliable
        across every filer. Falls back to None rather than returning
        garbled text if the markers aren't found.
    """
    filing = get_latest_10k(ticker)
    if filing is None:
        return None

    text = filing["text"]
    start_markers = ["Item 1A.", "Item 1A ", "ITEM 1A."]
    end_markers = ["Item 1B.", "Item 1B ", "Item 2.", "ITEM 1B.", "ITEM 2."]

    start_idx = None
    for marker in start_markers:
        idx = text.find(marker)
        if idx != -1:
            start_idx = idx
            break

    if start_idx is None:
        return None

    end_idx = len(text)
    for marker in end_markers:
        idx = text.find(marker, start_idx + len(marker))
        if idx != -1:
            end_idx = min(end_idx, idx)

    section = text[start_idx:end_idx]
    return section[:max_chars] if section else None


# ─────────────────────────────────────────────────────────────────────────────
# Segment margins — fallback for Margin Analysis
#
# yfinance sometimes lacks segment-level margin breakdowns. When that's
# insufficient, this pulls raw MD&A / segment reporting text for an LLM
# to interpret instead. We don't parse structured numbers here — 10-K
# segment tables aren't consistently machine-readable across filers.
# ─────────────────────────────────────────────────────────────────────────────


def get_segment_margins(ticker: str, max_chars: int = 15000) -> str | None:
    """
    Fetches MD&A-adjacent text likely to contain segment margin
    discussion, for LLM interpretation. Used as a fallback when
    yfinance's operatingMargins is missing or insufficiently granular.

    Args:
        ticker:    Stock ticker symbol.
        max_chars: Max characters to return.

    Returns:
        Filing text excerpt, or None if unavailable. Callers should
        pass this to an LLM with a structured output schema to extract
        an actual margin figure — this function only returns raw text.
    """
    filing = get_latest_10k(ticker)
    if filing is None:
        return None
    return filing["text"][:max_chars]
