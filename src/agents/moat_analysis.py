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

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Moat Analysis Prompt
# ─────────────────────────────────────────────────────────────────────────────

MOAT_PROMPT_TEMPLATE = """You are a moat/competitive-advantage analyst
scoring a company in the AI Factory value chain.

Company: {company_name} ({ticker})
AI Factory segment: {segment}
All segments company touches: {all_segments}
Revenue exposure to this segment: {revenue_exposure_pct}

Evaluate the company's competitive moat using the following four dimensions.

Score EACH dimension from 0-5.

1. Architectural Lock-in
How difficult is it for customers to replace the company's technology,
architecture, interfaces, infrastructure, or deeply integrated systems?

Consider:
- Proprietary technology
- Deep technical integration
- Proprietary interfaces or architectures
- Infrastructure dependency
- Compatibility requirements

2. Ecosystem Dominance
How strong is the company's developer, partner, supplier, or customer
ecosystem?

Consider:
- Developer ecosystem
- Partner ecosystem
- Network effects
- Industry standards
- Platform adoption
- Customer ecosystem
- Ecosystem size and dependency

3. Switching Costs
How costly or difficult is it for customers to move from this company
to a competitor?

Consider:
- Technical migration
- Retraining
- Integration costs
- Downtime
- Contracts
- Existing investments
- Data migration
- Operational disruption

4. Supply Chain Scarcity
How much control or scarcity does the company have over critical inputs,
manufacturing capacity, specialized components, intellectual property,
or strategic supply relationships?

Consider:
- Scarce manufacturing capacity
- Critical components
- Specialized suppliers
- Proprietary intellectual property
- Strategic supplier relationships
- Control over critical inputs

SCORING GUIDE:

0 = No moat / fully commoditized
1 = Very weak moat
2 = Weak moat
3 = Moderate moat
4 = Strong moat
5 = Extremely durable / near-monopoly moat

IMPORTANT:
- Base the scores on the company's actual competitive position.
- Do not give a high score simply because the company is large or profitable.
- Evaluate the company's position specifically within the AI Factory value chain.
- Each score must be between 0 and 5.
- Provide a concise 1-2 sentence explanation for each dimension.
- The overall moat score will be calculated programmatically from the
  four dimension scores.
- Do not calculate or provide the overall score yourself.

Respond with ONLY a JSON object.
Do not include markdown.
Do not include explanations outside the JSON.

Return exactly this structure:

{{
  "architectural_lock_in_score": <float between 0 and 5>,
  "architectural_lock_in_narrative": "<1-2 sentence justification>",

  "ecosystem_dominance_score": <float between 0 and 5>,
  "ecosystem_dominance_narrative": "<1-2 sentence justification>",

  "switching_costs_score": <float between 0 and 5>,
  "switching_costs_narrative": "<1-2 sentence justification>",

  "supply_chain_scarcity_score": <float between 0 and 5>,
  "supply_chain_scarcity_narrative": "<1-2 sentence justification>"
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(company: CompanyState) -> str:
    """Build the moat-analysis prompt for a single company."""

    return MOAT_PROMPT_TEMPLATE.format(
        company_name=company.company_name,
        ticker=company.ticker,
        segment=company.ai_factory_segment or "unknown",
        all_segments=", ".join(company.all_segments) or "unknown",
        revenue_exposure_pct=(
            f"{company.revenue_exposure_pct:.1%}"
            if company.revenue_exposure_pct is not None
            else "unknown"
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Score One Company
# ─────────────────────────────────────────────────────────────────────────────

async def _score_company(company: CompanyState) -> CompanyState:
    """
    Scores a single company across the four moat dimensions.

    The four dimension scores are:
        1. Architectural Lock-in
        2. Ecosystem Dominance
        3. Switching Costs
        4. Supply Chain Scarcity

    The overall moat score is calculated as the arithmetic mean of
    the four dimension scores.

    Failures are stored in company.error instead of raising so that
    one failed company does not stop the entire pipeline.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Skip companies that failed upstream
    # ─────────────────────────────────────────────────────────────────────────

    if company.error:
        logger.info(
            "moat_analysis: skipping %s (%s), upstream error: %s",
            company.ticker,
            company.company_name,
            company.error,
        )
        return company

    try:
        # ─────────────────────────────────────────────────────────────────────
        # Ask Gemini to score the four moat dimensions
        # ─────────────────────────────────────────────────────────────────────

        result = await generate_json(_build_prompt(company))

        # ─────────────────────────────────────────────────────────────────────
        # Extract individual scores
        # ─────────────────────────────────────────────────────────────────────

        architectural_lock_in = float(
            result["architectural_lock_in_score"]
        )

        ecosystem_dominance = float(
            result["ecosystem_dominance_score"]
        )

        switching_costs = float(
            result["switching_costs_score"]
        )

        supply_chain_scarcity = float(
            result["supply_chain_scarcity_score"]
        )

        # ─────────────────────────────────────────────────────────────────────
        # Validate individual scores
        # ─────────────────────────────────────────────────────────────────────

        sub_scores = [
            architectural_lock_in,
            ecosystem_dominance,
            switching_costs,
            supply_chain_scarcity,
        ]

        if any(score < 0.0 or score > 5.0 for score in sub_scores):
            raise ValueError(
                f"Moat sub-score outside [0,5]: {sub_scores}"
            )

        # ─────────────────────────────────────────────────────────────────────
        # Calculate overall moat score
        # ─────────────────────────────────────────────────────────────────────
        #
        # Equal weighting:
        #
        # Overall Moat =
        #     (Architectural Lock-in
        #      + Ecosystem Dominance
        #      + Switching Costs
        #      + Supply Chain Scarcity) / 4
        #
        # ─────────────────────────────────────────────────────────────────────

        moat_score = sum(sub_scores) / len(sub_scores)

        # ─────────────────────────────────────────────────────────────────────
        # Store overall score
        # ─────────────────────────────────────────────────────────────────────

        company.moat_score = round(moat_score, 2)

        # ─────────────────────────────────────────────────────────────────────
        # Store Architectural Lock-in
        # ─────────────────────────────────────────────────────────────────────

        company.architectural_lock_in_score = round(
            architectural_lock_in,
            2,
        )

        company.architectural_lock_in_narrative = str(
            result["architectural_lock_in_narrative"]
        )

        # ─────────────────────────────────────────────────────────────────────
        # Store Ecosystem Dominance
        # ─────────────────────────────────────────────────────────────────────

        company.ecosystem_dominance_score = round(
            ecosystem_dominance,
            2,
        )

        company.ecosystem_dominance_narrative = str(
            result["ecosystem_dominance_narrative"]
        )

        # ─────────────────────────────────────────────────────────────────────
        # Store Switching Costs
        # ─────────────────────────────────────────────────────────────────────

        company.switching_costs_score = round(
            switching_costs,
            2,
        )

        company.switching_costs_narrative = str(
            result["switching_costs_narrative"]
        )

        # ─────────────────────────────────────────────────────────────────────
        # Store Supply Chain Scarcity
        # ─────────────────────────────────────────────────────────────────────

        company.supply_chain_scarcity_score = round(
            supply_chain_scarcity,
            2,
        )

        company.supply_chain_scarcity_narrative = str(
            result["supply_chain_scarcity_narrative"]
        )

        logger.info(
            "moat_analysis: %s (%s) scored %.2f/5",
            company.company_name,
            company.ticker,
            company.moat_score,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "moat_analysis: failed for %s (%s): %s",
            company.ticker,
            company.company_name,
            exc,
        )

        company.error = f"moat_analysis: {exc}"

    return company


# ─────────────────────────────────────────────────────────────────────────────
# Moat Analysis Node
# ─────────────────────────────────────────────────────────────────────────────

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
