"""
src/agents/growth_forecast.py

The Growth Forecast agent.

Responsibility: for each company in state.companies, project a 3-year
AI-driven revenue CAGR, combining a historical baseline (yfinance) with
forward-looking signals synthesized from search results (Tavily + LLM).

Growth signals considered (per project scope):
  - AI Factory capex exposure
  - Order backlog growth
  - Hyperscaler / sovereign AI commitments
  - Product cycle timing (e.g. 800G networking, liquid cooling, AI servers)

This agent demonstrates the hybrid data + reasoning pattern: pull a
historical number (yfinance) as an anchor, then have the LLM adjust/
project forward based on qualitative signals from search — rather than
asking the LLM to invent a growth number from nothing.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from graph.state import AgentState, CompanyState, get_companies
from tools.financial import get_3yr_revenue_cagr
from tools.search import tavily_search

# ─────────────────────────────────────────────────────────────────────────────
# Model configuration
#
# Gemini chosen over Groq here: projecting growth requires synthesizing
# multiple qualitative signals (backlog commentary, hyperscaler
# commitments, product cycle timing) into one coherent forecast —
# higher reasoning load than Company Ingestion's structured extraction.
# ─────────────────────────────────────────────────────────────────────────────
MODEL_NAME = os.getenv("GOOGLE_MODEL_NAME", "gemini-3.1-flash-lite")


# ─────────────────────────────────────────────────────────────────────────────
# Growth forecast prompt
#
# Gives the LLM the historical CAGR as an anchor point, then asks it to
# adjust based on forward-looking signals — this keeps the forecast
# grounded in a real number rather than a pure guess, while still
# letting the LLM account for things a trailing-3-year number can't
# see (e.g. a new AI server contract just signed).
# ─────────────────────────────────────────────────────────────────────────────
GROWTH_FORECAST_PROMPT = ChatPromptTemplate.from_template(
    """
    You are an expert equity research analyst forecasting 3-year AI-driven revenue CAGR for companies in the AI Factory ecosystem.

    Target Company: {company_name} ({ticker})
    Segment: {segment}
    Historical 3-Yr Revenue CAGR: {historical_cagr}

    Analyze the following search results regarding the company's AI-driven growth factors:
    1. **Capex Exposure**: Direct exposure to hyperscaler AI infrastructure capex.
    2. **Order Backlog Growth**: Visibility into future revenues via expanding order book/backlog.
    3. **Hyperscaler Commitments**: Explicit design wins or procurement commitments from Tier-1 hyperscalers (e.g., Microsoft, AWS, Google, Meta).
    4. **Product Cycle Timing**: Upcoming or accelerating product cycles (e.g., next-gen GPUs, liquid cooling, high-bandwith networking).

    Search Context:
    {search_results}

    Task:
    Provide an estimated 3-Year Projected CAGR as a decimal (e.g., 0.35 for 35% projected annual growth). Consider the historical CAGR as a baseline and adjust higher or lower based on the capex trends, backlog expansion, hyperscaler pull-through, and product execution timing.
"""
)


class GrowthForecast(BaseModel):
    growth_cagr_3yr: float = Field(
        description="Projected 3-year forward revenue CAGR, as a decimal (0.25 = 25%)."
    )
    growth_narrative: str = Field(
        description="2-3 sentence explanation grounded in the search results."
    )


# ─────────────────────────────────────────────────────────────────────────────
# LLM factory
# ─────────────────────────────────────────────────────────────────────────────
def build_growth_forecast_llm() -> ChatGoogleGenerativeAI:
    """
    Create the Gemini LLM client for Growth Forecast.

    temperature=0.3 — same rationale as Moat Analysis: this is a
    qualitative judgment task (synthesizing multiple signals into one
    forecast), not pure structured extraction, but should stay
    reasonably consistent across companies.
    """

    return ChatGoogleGenerativeAI(
        model=MODEL_NAME, temperature=0.3, max_retries=5, timeout=60
    )


# ─────────────────────────────────────────────────────────────────────────────
# Per-company forecasting helper
#
# Separated from the node function so it can be tested independently
# without running the full company loop.
# ─────────────────────────────────────────────────────────────────────────────
async def forecast_growth(company: CompanyState) -> CompanyState:
    """
    Forecasts a single company's 3-year AI-driven revenue CAGR, using a
    historical yfinance baseline plus Tavily search + Gemini reasoning.

    Args:
        company: The company to forecast (must already have ticker,
                 company_name, ai_factory_segment populated).

    Returns:
        The same CompanyState, with growth_cagr_3yr filled in on
        success, or company.error set on failure (growth_cagr_3yr
        stays None — does not raise, so one company failing doesn't
        break the whole batch).
    """
    try:
        # Historical baseline — sync yfinance call, wrapped in a thread
        historical_cagr = await asyncio.to_thread(get_3yr_revenue_cagr, company.ticker)
        historical_display = (
            f"{historical_cagr:.1%}" if historical_cagr is not None else "not available"
        )

        # 2. Gather market intelligence search snippets
        query = f"{company.company_name} {company.ticker} AI capex backlog hyperscaler order growth product cycle"
        results = await asyncio.to_thread(tavily_search, query, max_results=5)

        if not results:
            company.error = "Growth Forecast: no search results found"
            return company

        results_text = "\n".join(
            f"- {r['title']}: {r['content'][:350]}" for r in results
        )

        llm = build_growth_forecast_llm()
        structured_llm = llm.with_structured_output(GrowthForecast)
        chain = GROWTH_FORECAST_PROMPT | structured_llm

        # 3. LLM forecast evaluation
        forecast = cast(
            GrowthForecast,
            await chain.ainvoke(
                {
                    "company_name": company.company_name,
                    "ticker": company.ticker,
                    "segment": company.ai_factory_segment,
                    "historical_cagr": historical_display,
                    "search_results": results_text,
                }
            ),
        )

        company.growth_cagr_3yr = forecast.growth_cagr_3yr
        company.growth_narrative = forecast.growth_narrative

    except Exception as e:  # noqa: BLE001
        print(f"[forecast_growth] Failed for '{company.ticker}': {e}")
        company.error = f"Growth Forecast failed: {e}"

    return company


# ─────────────────────────────────────────────────────────────────────────────
# The LangGraph node
# ─────────────────────────────────────────────────────────────────────────────
async def growth_forecast_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Growth Forecast

    Reads:
        state.companies: list of CompanyState, populated by earlier agents

    Writes:
        state.companies:    same list, with growth_cagr_3yr filled in
        state.current_step: "growth_forecast_complete"

    Flow:
        1. For each company in state.companies (concurrently, rate-limited):
           a. Fetch historical 3yr revenue CAGR (yfinance) as a baseline
           b. Search for forward-looking growth signals (Tavily)
           c. LLM projects a forward 3yr CAGR, anchored to the baseline
        2. Return partial state update with the enriched company list
    """

    companies = get_companies(state)

    if not companies:
        return {"error": "No companies found. Run Company Ingestion first."}

    print(f"\n[Growth Forecast] Forecasting 3yr CAGR for {len(companies)} companies...")

    forecasted = []
    for c in companies:
        forecasted.append(await forecast_growth(c))

    succeeded = sum(1 for c in forecasted if c.growth_cagr_3yr is not None)
    print(
        f"[Growth Forecast] Done. {succeeded}/{len(forecasted)} companies forecasted successfully."
    )

    return {
        "companies": forecasted,
        "current_step": "growth_forecast_complete",
    }
