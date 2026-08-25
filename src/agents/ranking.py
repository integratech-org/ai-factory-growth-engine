"""
Ranking Agent — computes the Total AI Factory Growth Score (TAFGS)
and produces the ordered Top 20 ranking.
"""

from __future__ import annotations

from typing import Any

from graph.state import AgentState, CompanyState, get_companies


def _normalize_moat_score(company: CompanyState) -> float:
    """Normalize moat score (0-5 scale) to a 0-100 factor."""
    if company.moat_score is not None:
        return min(100.0, max(0.0, (company.moat_score / 5.0) * 100.0))
    return 50.0  # Default neutral score if not evaluated yet


def _normalize_margin_score(company: CompanyState) -> float:
    """Normalize margin score (0-5 scale or operating margin) to a 0-100 factor."""
    if company.margin_score is not None:
        return min(100.0, max(0.0, (company.margin_score / 5.0) * 100.0))

    if company.operating_margin is not None:
        # e.g., 0.30 (30% operating margin) -> 90/100, 0.10 (10%) -> 30/100
        return min(100.0, max(0.0, company.operating_margin * 300.0))

    return 50.0  # Default neutral score


def _normalize_growth_score(company: CompanyState) -> float:
    """Normalize 3-year revenue CAGR to a 0-100 factor."""
    if company.growth_cagr_3yr is not None:
        # e.g., 0.50 (50% CAGR) -> 100/100, 0.25 (25% CAGR) -> 50/100
        return min(100.0, max(0.0, company.growth_cagr_3yr * 200.0))
    return 50.0  # Default neutral score


def _normalize_exposure_score(
    company: CompanyState, segment_framework: dict[str, Any]
) -> float:
    """Normalize AI Factory revenue exposure and weight by segment share."""
    base_exposure = (
        company.revenue_exposure_pct if company.revenue_exposure_pct is not None else 50.0
    )
    base_exposure = min(100.0, max(0.0, base_exposure))

    # Apply segment capex allocation multiplier if available
    segment = company.ai_factory_segment
    if segment and segment in segment_framework:
        weight_pct = segment_framework[segment].get("weight_pct", 10)
        # Compute segment multiplier (e.g. compute with 58% spend gets ~1.29x boost)
        multiplier = 1.0 + (weight_pct / 200.0)
        base_exposure = min(100.0, base_exposure * multiplier)

    return base_exposure


def calculate_tafgs(company: CompanyState, segment_framework: dict[str, Any]) -> float:
    """
    Computes Total AI Factory Growth Score (TAFGS) on a 0-100 scale.

    Weights:
      - Moat / Differentiation: 30%
      - Operating Margin Quality: 25%
      - Revenue Growth CAGR (3-Yr): 25%
      - AI Factory Revenue Exposure: 20%

    Applies company-specific risk discount (if any).
    """
    moat_score = _normalize_moat_score(company)
    margin_score = _normalize_margin_score(company)
    growth_score = _normalize_growth_score(company)
    exposure_score = _normalize_exposure_score(company, segment_framework)

    base_score = (
        0.30 * moat_score
        + 0.25 * margin_score
        + 0.25 * growth_score
        + 0.20 * exposure_score
    )

    # Risk Adjustment
    if company.risk_discount is not None:
        # Cap risk discount to a maximum of 50%
        discount = min(0.50, max(0.0, company.risk_discount))
        final_score = base_score * (1.0 - discount)
    else:
        final_score = base_score

    return round(final_score, 2)


async def ranking_node(state: AgentState | dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: Ranking Agent

    Reads:
        state.companies: list of CompanyState records
        state.segment_framework: dict mapping AI Factory segments

    Writes:
        state.companies: list of CompanyState records updated with tafgs_score and rank
        state.current_step: "ranking_complete"
    """
    companies = get_companies(state)

    if isinstance(state, dict):
        segment_framework = state.get("segment_framework", {})
    else:
        segment_framework = getattr(state, "segment_framework", {})

    print(
        f"\n[Ranking Agent] Scoring and ranking {len(companies)} companies..."
    )

    # Compute TAFGS score for each company
    for company in companies:
        company.tafgs_score = calculate_tafgs(company, segment_framework)

    # Sort companies in descending order of TAFGS score (tie-breaking by ticker)
    sorted_companies = sorted(
        companies,
        key=lambda c: (c.tafgs_score if c.tafgs_score is not None else -1.0, c.ticker),
        reverse=True,
    )

    # Assign ranks (1-indexed)
    for index, company in enumerate(sorted_companies, start=1):
        company.rank = index

    print(
        f"[Ranking Agent] Successfully ranked {len(sorted_companies)} companies."
    )
    if sorted_companies:
        top_ticker = sorted_companies[0].ticker
        top_score = sorted_companies[0].tafgs_score
        print(f"               Top Ranked: #{1} {top_ticker} (TAFGS: {top_score})")

    return {
        "companies": sorted_companies,
        "current_step": "ranking_complete",
    }
