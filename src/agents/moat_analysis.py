"""
src/agents/moat_analysis.py

The Moat Analysis agent.

Responsibility: for each company in state.companies, assess its
competitive moat/defensibility within the AI Factory value chain and
produce a 0-5 moat_score plus a short narrative explaining the score.

Moat factors considered (per project scope):
  - Architectural lock-in (e.g. CUDA, proprietary networking)
  - Ecosystem dominance (design wins, reference architectures)
  - Switching costs / standard-setting influence
  - Scarcity or bottleneck position in the AI Factory supply chain

This agent demonstrates the search + reason + score pattern:
  read companies from state → search per company → LLM reasons about
  moat factors and produces a score + narrative → update company state
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from graph.state import AgentState, CompanyState, get_companies
from tools.search import tavily_search

# ─────────────────────────────────────────────────────────────────────────────
# Model configuration
#
# Gemini chosen over Groq here: moat assessment needs qualitative
# judgment (weighing multiple soft factors into one score + narrative),
# not just structured extraction — this benefits more from Gemini's
# deeper reasoning than from Groq's speed.
# ─────────────────────────────────────────────────────────────────────────────
MODEL_NAME = os.getenv("GOOGLE_MODEL_NAME", "gemini-3.1-flash-lite")


# ─────────────────────────────────────────────────────────────────────────────
# Moat assessment prompt
#
# Explicitly lists the 4 moat factors from the project scope so the LLM
# grounds its score in those specific dimensions, not a vague "how good
# is this company" judgment.
# ─────────────────────────────────────────────────────────────────────────────
MOAT_PROMPT = ChatPromptTemplate.from_template(
    """You are an equity research analyst assessing competitive moat
    strength for {company_name} ({ticker}), which operates in the
    "{segment}" segment of AI Factory / data center infrastructure.

    Based on the search results below, score this company's moat on a
    0-5 scale using these four factors:
      1. Architectural lock-in (e.g. proprietary tech/standards that
         make switching away costly or impractical)
      2. Ecosystem dominance (design wins, reference architectures,
         being the default choice in the industry)
      3. Switching costs / standard-setting influence
      4. Scarcity or bottleneck position in the supply chain

    Scoring guide:
      5 = Extremely strong moat across multiple factors (e.g. deep
          architectural lock-in + ecosystem dominance)
      3 = Moderate moat, some differentiation but real competition exists
      0 = No meaningful moat, commodity product/service

    Write a 2-3 sentence narrative explaining the score, grounded in
    what the search results actually say — do not invent specifics not
    supported by the text below.

    Search results:
    {search_results}
    """
)


class MoatAssessment(BaseModel):
    moat_score: float = Field(
        description="Moat strength score from 0 to 5, per the four factors described.",
        ge=0,
        le=5,
    )
    moat_narrative: str = Field(
        description="2-3 sentence explanation grounded in the search results."
    )


# ─────────────────────────────────────────────────────────────────────────────
# LLM factory
# ─────────────────────────────────────────────────────────────────────────────
def build_moat_analysis_llm() -> ChatGoogleGenerativeAI:
    """
    Create the Gemini LLM client for Moat Analysis.

    temperature=0.3 — higher than Company Ingestion's 0.2 since this is
    a qualitative judgment task (weighing soft factors into a score),
    not pure structured extraction. Still low enough to keep scoring
    reasonably consistent across companies.
    """
    return ChatGoogleGenerativeAI(
        model=MODEL_NAME, temperature=0.3, max_retries=5, timeout=60
    )


# ─────────────────────────────────────────────────────────────────────────────
# Per-company scoring helper
#
# Separated from the node function so it can be tested independently
# without running the full company loop.
# ─────────────────────────────────────────────────────────────────────────────
async def score_moat(company: CompanyState) -> CompanyState:
    """
    Scores a single company's moat strength via Tavily search + Gemini.

    Args:
        company: The company to score (must already have ticker,
                 company_name, ai_factory_segment populated).

    Returns:
        The same CompanyState, with moat_score/moat_narrative filled in
        on success, or company.error set on failure (score/narrative
        stay None — does not raise, so one company failing doesn't
        break the whole batch).
    """
    try:
        query = (
            f"{company.company_name} competitive advantage moat "
            f"AI infrastructure market position"
        )
        results = await asyncio.to_thread(tavily_search, query, max_results=8)

        if not results:
            company.error = "Moat Analysis: no search results found"
            return company

        results_text = "\n".join(
            f"- {r['title']} ({r['content'][:400]})" for r in results
        )

        llm = build_moat_analysis_llm()
        structured_llm = llm.with_structured_output(MoatAssessment)
        chain = MOAT_PROMPT | structured_llm

        assessment = cast(
            MoatAssessment,
            await chain.ainvoke(
                {
                    "company_name": company.company_name,
                    "ticker": company.ticker,
                    "segment": company.ai_factory_segment,
                    "search_results": results_text,
                }
            ),
        )

        company.moat_score = assessment.moat_score
        company.moat_narrative = assessment.moat_narrative

    except Exception as e:  # noqa: BLE001
        print(f"[score_moat] Failed for '{company.ticker}': {e}")
        company.error = f"Moat Analysis failed: {e}"

    return company


# ─────────────────────────────────────────────────────────────────────────────
# The LangGraph node
# ─────────────────────────────────────────────────────────────────────────────
async def moat_analysis_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Moat Analysis

    Reads:
        state.companies: list of CompanyState, populated by Company Ingestion

    Writes:
        state.companies:    same list, with moat_score/moat_narrative filled in
        state.current_step: "moat_analysis_complete"

    Flow:
        1. For each company in state.companies (concurrently, rate-limited):
           a. Search for competitive positioning info (Tavily)
           b. LLM scores moat strength 0-5 + writes narrative
        2. Return partial state update with the enriched company list
    """
    companies = get_companies(state)

    if not companies:
        return {"error": "No companies found. Run Company Ingestion first."}

    print(f"\n[Moat Analysis] Scoring moat strength for {len(companies)} companies...")

    scored = []
    for c in companies:
        scored.append(await score_moat(c))

    succeeded = sum(1 for c in scored if c.moat_score is not None)
    print(
        f"[Moat Analysis] Done. {succeeded}/{len(scored)} companies scored successfully."
    )

    return {
        "companies": scored,
        "current_step": "moat_analysis_complete",
    }
