"""
SEC EDGAR wrapper via edgartools.
Used by: Moat Analysis, Margin Analysis (backup), Risk Adjustment agents.
"""

from __future__ import annotations

import os

from edgar import set_identity

# SEC EDGAR requires a real identifying user-agent string (name + email)
# on every request — this is a compliance requirement, not optional.
set_identity(f"{os.getenv('SEC_EDGAR_NAME')} {os.getenv('SEC_EDGAR_EMAIL')}")

# TODO: def get_latest_10k(ticker: str) -> dict
#   - use edgartools to fetch latest 10-K filing
#   - wrap in asyncio.to_thread() since edgartools is sync
# TODO: def get_risk_factors_section(ticker: str) -> str
#   - extract Item 1A (Risk Factors) for Risk Adjustment agent
# TODO: def get_segment_margins(ticker: str) -> dict
#   - fallback for Margin Analysis when yfinance data is incomplete
