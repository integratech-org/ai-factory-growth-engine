"""
src/agents/margin_analysis.py

The Margin Analysis agent.

Responsibility: for each company in state.companies, pull its operating
margin from yfinance and normalize it into a 0-5 margin_score using the
bracket formula from the project scope.

Bracket formula (per project scope, Section 2.2):
    >40%      -> 5
    30-40%    -> 4
    20-30%    -> 3
    10-20%    -> 2
    <10%      -> 1

This is the simplest scoring agent in the system:
  - No LLM call — pure deterministic computation
  - No search — just a yfinance lookup + bracket lookup
  - Fast and cheap compared to the LLM-driven agents

This agent demonstrates the pure-computation pattern: fetch data →
apply a fixed formula → update state. No prompt, no schema, no
reasoning — just math.
"""

from __future__ import annotations

import asyncio
from typing import Any

from graph.state import AgentState, CompanyState, get_companies
from tools.financial import get_operating_margin


# ─────────────────────────────────────────────────────────────────────────────
# Margin bracket formula
#
# Straight from the project scope (Section 2.2). Kept as a standalone,
# testable function — no LLM or external call involved, so this is
# trivially unit-testable with plain floats.
# ─────────────────────────────────────────────────────────────────────────────
def score_margin_bracket(operating_margin: float) -> float:
    """
    Normalizes a raw operating margin (decimal, e.g. 0.42 for 42%) into
    a 0-5 score using the project's fixed bracket formula.

    Args:
        operating_margin: Operating margin as a decimal (0.42 = 42%).

    Returns:
        Score from 1 to 5. Margins below 0% still score 1 (the lowest
        bracket) rather than 0 — the scope only defines 5 brackets,
        all with a floor of 1, so we don't invent a 0 bracket.
    """
    margin_pct = operating_margin * 100

    if margin_pct > 40.0:
        return 5.0
    elif margin_pct >= 30.0:
        return 4.0
    elif margin_pct >= 20.0:
        return 3.0
    elif margin_pct >= 10.0:
        return 2.0
    else:
        return 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Per-company scoring helper
#
# Separated from the node function so it can be tested independently
# without running the full company loop.
# ─────────────────────────────────────────────────────────────────────────────
async def score_company_margin(company: CompanyState) -> CompanyState:
    """
    Fetches a single company's operating margin and computes its
    margin_score.

    Args:
        company: The company to score (must already have ticker populated).

    Returns:
        The same CompanyState, with operating_margin/margin_score filled
        in on success, or company.error set on failure (score stays
        None — does not raise, so one company failing doesn't break
        the whole batch).
    """
    try:
        # yfinance is sync — wrap in a thread so it doesn't block the
        # event loop while other companies are being processed.
        margin = await asyncio.to_thread(get_operating_margin, company.ticker)

        if margin is None:
            company.error = (
                "Margin Analysis: operating margin unavailable from yfinance"
            )
            return company

        company.operating_margin = margin
        company.margin_score = score_margin_bracket(margin)

    except Exception as e:  # noqa: BLE001
        print(f"[score_company_margin] Failed for '{company.ticker}': {e}")
        company.error = f"Margin Analysis failed: {e}"

    return company


# ─────────────────────────────────────────────────────────────────────────────
# The LangGraph node
# ─────────────────────────────────────────────────────────────────────────────
async def margin_analysis_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Margin Analysis

    Reads:
        state.companies: list of CompanyState, populated by Company Ingestion

    Writes:
        state.companies:    same list, with operating_margin/margin_score filled in
        state.current_step: "margin_analysis_complete"

    Flow:
        1. For each company in state.companies:
           a. Fetch operating margin from yfinance
           b. Normalize into a 0-5 score using the bracket formula
        2. Return partial state update with the enriched company list
    """
    companies = get_companies(state)

    if not companies:
        return {"error": "No companies found. Run Company Ingestion first."}

    print(
        f"\n[Margin Analysis] Scoring operating margin for {len(companies)} companies..."
    )

    scored = []
    for c in companies:
        scored.append(await score_company_margin(c))

    succeeded = sum(1 for c in scored if c.margin_score is not None)
    print(
        f"[Margin Analysis] Done. {succeeded}/{len(scored)} companies scored successfully."
    )

    return {
        "companies": scored,
        "current_step": "margin_analysis_complete",
    }