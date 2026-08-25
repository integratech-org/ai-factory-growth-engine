"""
Growth Forecast Agent — projects AI-driven 3-year CAGR based on
capex exposure, order backlog growth, hyperscaler commitments, and product cycle timing.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from graph.state import AgentState, CompanyState, get_companies
from tools.financial import get_3yr_revenue_cagr
from tools.search import tavily_search

# Model Config
MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

# Extraction & Forecast Prompt
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

# Structured Output Schema
class GrowthForecastAssessment(BaseModel):
    projected_cagr_3yr: float = Field(
        description="Estimated 3-year revenue CAGR as a decimal percentage (e.g., 0.25 for 25% annual growth, 0.40 for 40% growth)."
    )
    growth_drivers_summary: str = Field(
        description="Brief narrative explanation of the growth projection based on capex, backlog, hyperscaler demands, and product cycle."
    )

def build_growth_llm() -> ChatGroq:
    """Create the Groq LLM client for Growth Forecasting."""
    return ChatGroq(model=MODEL_NAME, temperature=0.2)




# Helper: Process a single company forecast
async def evaluate_company_growth(company: CompanyState, chain: Any) -> tuple[CompanyState, str | None]:
    """
    Collects growth indicators and invokes the LLM growth forecast chain for one company
    """
    ticker = company.ticker
    company_name = company.company_name
    segment = company.ai_factory_segment or "Unknown Segment"

    try:
        # 1. Fetch historical CAGR
        hist_cagr_val = await asyncio.to_thread(get_3yr_revenue_cagr, ticker)
        historical_cagr_str = (
            f"{hist_cagr_val * 100:.1f}%"if hist_cagr_val is not None else "N/A"
        )

        # 2. Gather market intelligence search snippets
        query = f"{company_name} {ticker} AI capex backlog hyperscaler order growth product cycle"
        search_results = await asyncio.to_thread(tavily_search, query, max_results=5)

        if search_results:
            search_text = "\n".join(
                f"- {r['title']}: {r['content'][:350]}" for r in search_results
            )
        else:
            search_text = "No recent search findings available"

        # 3. LLM forecast evaluation
        assessment = cast(
            GrowthForecastAssessment,
            await chain.ainvoke(
                {
                "company_name": company_name,
                "ticker": ticker,
                "segment": segment,
                "historical_cagr": historical_cagr_str,
                "search_results": search_text,
                }
            ),
        )

        # 4. Populate company state
        company.growth_cagr_3yr = round(float(assessment.projected_cagr_3yr), 4)
        return company, None

    except Exception as e:
        error_msg = f"{ticker}: {e}"
        print(f"[Growth Forecast] Error processing {ticker}: {e}")
        company.error = error_msg
        return company, error_msg

# LangGraph node
async def growth_forecast_node(state: AgentState | dict) -> dict[str, Any]:
    """
    LangGraph node: Growth Forecast Agent
    
    Reads:
        state.companies: List of CompanyState records populated by prior agents.
        
    Writes:
        company.growth_cagr_3yr: Projected 3-Year CAGR decimal.
        state.current_step: "growth_forecast_complete"
        state.error: Semicolon-joined string of non-fatal comapny processing errors.
        """
    companies = get_companies(state)

    if not companies:
        return {
            "current_step": "growth_forecast_complete",
            "error": "No companies found in state to evaluate",
        }

    print(f"\n[Growth Forecast] Starting growth forecasting for {len(companies)} companies...")

    llm = build_growth_llm()
    structured_llm = llm.with_structured_output(GrowthForecastAssessment)
    chain = GROWTH_FORECAST_PROMPT | structured_llm

    # Execute growth analysis concurrently across companies
    results = await asyncio.gather(
        *[evaluate_company_growth(company, chain) for company in companies]
    )

    updated_companies: list[CompanyState] = []
    errors: list[str] = []

    for company, error in results:
        updated_companies.append(company)
        if error:
            errors.append(error)

    print(f"[Growth Forecast] Completed forecasting for {len(updated_companies)} companies.")

    return {
        "companies": updated_companies,
        "current_step": "growth_forecast_complete",
        "error": "; ".join(errors) if errors else None,
    }
