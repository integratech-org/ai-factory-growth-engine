"""
Moat Analysis Agent — scores differentiation and ecosystem lock-in.

Evaluates four moat dimensions:
- Architectural Lock-in
- Ecosystem Dominance
- Switching Costs
- Supply Chain Scarcity

The overall moat score is calculated as the average of the four
dimension scores.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from graph.state import AgentState, CompanyState, get_companies
from llm.gemini import generate_json

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

async def moat_analysis_node(state: AgentState) -> dict[str, Any]:
    """
    Scores every company in state.companies for moat/differentiation
    strength.

    Companies are scored in parallel.

    Each company receives:

        moat_score

        architectural_lock_in_score
        architectural_lock_in_narrative

        ecosystem_dominance_score
        ecosystem_dominance_narrative

        switching_costs_score
        switching_costs_narrative

        supply_chain_scarcity_score
        supply_chain_scarcity_narrative

    Companies with an existing error are passed through unscored.
    Individual scoring failures are stored on company.error.
    """

    companies = get_companies(state)

    if not companies:
        logger.warning(
            "moat_analysis: no companies in state, nothing to score"
        )

        return {
            "companies": [],
            "current_step": "moat_analysis",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Score all companies concurrently
    # ─────────────────────────────────────────────────────────────────────────

    scored = await asyncio.gather(
        *(_score_company(company) for company in companies)
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Return updated companies to the graph
    # ─────────────────────────────────────────────────────────────────────────

    return {
        "companies": [company.to_dict() for company in scored],
        "current_step": "moat_analysis",
    }