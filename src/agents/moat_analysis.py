"""
src/agents/moat_analysis.py

The Moat Analysis agent.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from graph.state import AgentState, CompanyState, get_companies
from tools.search import tavily_search

MODEL_NAME = os.getenv("GOOGLE_MODEL_NAME", "gemini-3.5-flash-lite")

# ─────────────────────────────────────────────────────────────────────────────
# Rate limiting
#
# Gemini free tier caps gemini-3.1-flash-lite at 15 requests/minute
# (RPM), per the 429 RESOURCE_EXHAUSTED errors this agent was hitting.
# score_moat() is one Gemini call per company, run sequentially in the
# node loop, but with zero throttling the loop blew straight past the
# 15/min ceiling well before it finished a ~40-company batch.
#
# _GeminiRateLimiter enforces a floor between calls so we never submit
# more than GEMINI_RPM requests in any rolling 60s window. This is the
# root-cause fix (staying under the limit); the retry decorator below
# is the backstop for the odd 429 that still slips through (e.g. quota
# shared with other agents/processes running concurrently).
# ─────────────────────────────────────────────────────────────────────────────
GEMINI_RPM = int(os.getenv("GEMINI_RPM", "15"))


class _GeminiRateLimiter:
    def __init__(self, rpm: int) -> None:
        self._min_interval = 60.0 / rpm
        self._lock = asyncio.Lock()
        self._last_call: float = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_call = asyncio.get_event_loop().time()


_gemini_limiter = _GeminiRateLimiter(GEMINI_RPM)


def _is_rate_limit_error(exc: BaseException) -> bool:
    # google.api_core raises ResourceExhausted; also guard on message text
    # in case a differently-wrapped exception type reaches us.
    return "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc)


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


def build_moat_analysis_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.3)


@retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_random_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def _invoke_with_retry(
    chain: Runnable, payload: dict[str, Any]
) -> MoatAssessment:
    """
    Gemini call wrapped with backoff for the residual 429s that get past
    the rate limiter (e.g. quota shared with another process). Backs off
    exponentially (1s -> up to 60s, 5 attempts) rather than the fixed
    45s the API suggests, since jitter avoids every retry landing on
    the same second across concurrent runs.
    """
    await _gemini_limiter.wait()
    return cast(MoatAssessment, await chain.ainvoke(payload))


async def score_moat(company: CompanyState, chain: Runnable) -> CompanyState:
    """
    Scores a single company's moat strength via Tavily search + Gemini.
    Rate-limited and retried on 429s so one company failing doesn't
    break the whole batch, and transient quota exhaustion resolves
    itself instead of permanently marking companies as errored.
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

        assessment = await _invoke_with_retry(
            chain,
            {
                "company_name": company.company_name,
                "ticker": company.ticker,
                "segment": company.ai_factory_segment or "unknown",
                "search_results": results_text,
            },
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

async def moat_analysis_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Moat Analysis

    Reads:
        state.companies: list of CompanyState, populated by Company Ingestion
        (or, on retry, the previous Moat Analysis pass — see below)

    Writes:
        state.companies:    same list, with moat_score/moat_narrative filled in
        state.current_step: "moat_analysis_complete"

    Flow:
        1. Build the Gemini chain once (shared across all companies)
        2. Split into already-scored vs needs-scoring, so a rerun after
           a quota exhaustion only re-spends calls on the companies
           that actually failed last time
        3. For each company needing scoring (sequentially, rate-limited
           to GEMINI_RPM, each call retried with backoff on 429):
           a. Search for competitive positioning info (Tavily)
           b. LLM scores moat strength 0-5 + writes narrative
        4. Return partial state update with the enriched company list
    """
    companies = get_companies(state)

    if not companies:
        return {"error": "No companies found. Run Company Ingestion first."}

    already_scored = [c for c in companies if c.moat_score is not None]
    needs_scoring = [c for c in companies if c.moat_score is None]

    print(
        f"\n[Moat Analysis] {len(already_scored)} already scored, "
        f"scoring {len(needs_scoring)} companies "
        f"(rate-limited to {GEMINI_RPM} req/min)..."
    )

    llm = build_moat_analysis_llm()
    structured_llm = llm.with_structured_output(MoatAssessment)
    chain = MOAT_PROMPT | structured_llm

    scored: list[CompanyState] = []
    for company in needs_scoring:
        scored.append(await score_moat(company, chain))

    all_companies = already_scored + scored
    succeeded = sum(1 for c in all_companies if c.moat_score is not None)
    print(
        f"[Moat Analysis] Done. {succeeded}/{len(all_companies)} companies scored successfully."
    )

    return {
        "companies": all_companies,
        "current_step": "moat_analysis_complete",
    }
