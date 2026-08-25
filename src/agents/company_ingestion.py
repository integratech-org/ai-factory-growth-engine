"""
src/agents/company_ingestion.py

The Company Ingestion agent.

Responsibility: given the AI Factory segment framework (from Market
Mapping), search for and verify public companies with revenue exposure
to each segment, producing a deduplicated list of CompanyState records.

This agent demonstrates the search + extract + verify + dedupe pattern:
  read segments from state → search per segment (multiple query angles)
  → LLM extracts structured candidates → verify each ticker against
  yfinance → dedupe across segments → return populated company list
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, cast

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_message,
    stop_after_attempt,
    wait_exponential,
)

from graph.state import AgentState, AIFactorySegment, CompanyState
from tools.financial import get_company_profile
from tools.search import tavily_search

# TODO: revenue_exposure_pct is always null for now — not yet implemented.
# Tried two ways to get this number, both failed:
#   1. SEC EDGAR (10-K filings) — too slow (~5 min) and almost never found
#      the number, because the exact % is usually buried deep in the filing,
#      not near the top where we were looking.
#   2. Tavily search snippets — fast, but news articles rarely state the
#      exact % either, so this also came back empty most of the time.
# Plan: revisit this after all 8 agents are done. Probably need to fetch
# the FULL 10-K and search for the specific section (segment revenue
# breakdown) instead of just grabbing the first few pages.

# ─────────────────────────────────────────────────────────────────────────────
# Model configuration
#
# Groq chosen over Gemini here: this is a high-volume screening task
# across multiple segments, so inference speed matters more than deep
# reasoning quality.
# ─────────────────────────────────────────────────────────────────────────────
MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-120b")


# ─────────────────────────────────────────────────────────────────────────────
# Extraction prompt
#
# Single-shot extraction, not a conversation. Key decisions:
#   1. Explicitly require a stock ticker — filters out private companies
#      at the LLM reasoning stage, before we even hit yfinance
#   2. Segment description passed in for grounding, not just the key
#   3. Target 10-15+ per segment since multiple query angles feed more
#      search results into this prompt
# ─────────────────────────────────────────────────────────────────────────────
EXTRACTION_PROMPT = ChatPromptTemplate.from_template(
    """
    You are screening public companies for the "{segment}" segment of AI
    Factory / data center infrastructure ({description}).

    From the search results below, extract EVERY public company mentioned
    that has direct revenue exposure to this segment — not just the one or
    two most obvious market leaders. Aim to identify as many distinct,
    verifiable companies as the search results actually support — target
    10-15+ per segment if the results contain that many, including mid-cap
    and smaller/niche players alongside large-cap leaders.
    Rules:
    1. Only include companies that are PUBLICLY TRADED with a real stock
       ticker you can identify from the search results or your own
       knowledge (e.g. NVDA, VRT, ETN). Exclude private companies,
       subsidiaries without their own ticker, and startups.
    2. If you are not confident a company has a valid, real ticker, DO NOT
       include it — do not guess, and never use placeholder values like
       "NONE", "N/A", "UNKNOWN", or "TBD".
    3. Do not list the same company twice under different name variants.
    4. Do not invent companies that are not supported by the search
       results — only extract what is actually mentioned or clearly
       implied there.
    5. Prefer primary US-listed tickers when a company trades on multiple
       exchanges.

    Search results:
    {search_results}
    """
)


# ─────────────────────────────────────────────────────────────────────────────
# Structured output schema
#
# Local to this agent — NOT part of AgentState/CompanyState. Used only
# to constrain LLM output via .with_structured_output().
# ─────────────────────────────────────────────────────────────────────────────
class CompanyCandidate(BaseModel):
    ticker: str = Field(description="Stock ticker symbol, e.g. NVDA")
    company_name: str = Field(description="Full company name")


class CompanyCandidateList(BaseModel):
    companies: list[CompanyCandidate] = Field(
        description="List of public companies found relevant to this segment"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Extraction retry wrapper
#
# Groq's forced tool-calling (via with_structured_output) occasionally
# fails non-deterministically — the model responds with plain text
# instead of calling the tool, or a 429 rate limit hits mid-run. Both
# are usually transient, so retry with exponential backoff rather than
# letting one bad segment eat the whole run.
# ─────────────────────────────────────────────────────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_message(
        match=".*(did not call a tool|rate_limit_exceeded).*"
    ),
    reraise=True,
)
async def _extract_with_retry(chain, payload: dict) -> CompanyCandidateList:
    return cast(CompanyCandidateList, await chain.ainvoke(payload))


# ─────────────────────────────────────────────────────────────────────────────
# LLM factory
#
# New instance per call rather than a module-level singleton — avoids
# subtle state issues in long-running processes, easier to test with
# different configurations.
# ─────────────────────────────────────────────────────────────────────────────
def build_ingestion_llm() -> ChatGroq:
    """
    Create the Groq LLM client for Company Ingestion.

    temperature=0.2, low temperature for structured extraction tasks —
    we're extracting company names/tickers from search results, which
    needs consistency, not creativity. Higher temperature risks the LLM
    inventing plausible-sounding but incorrect ticker symbols.
    """
    return ChatGroq(model=MODEL_NAME, temperature=0.2)


# ─────────────────────────────────────────────────────────────────────────────
# Verification helper
#
# Separated from the node function so it can be tested independently
# without running the full segment loop.
# ─────────────────────────────────────────────────────────────────────────────
async def verify_candidate(
    candidate: CompanyCandidate, segment_key: AIFactorySegment
) -> CompanyState | None:
    """
    Verify a single LLM-extracted candidate against yfinance.

    Args:
        candidate:   The LLM's extracted ticker + company name.
        segment_key: Which AI Factory segment this candidate was found under.

    Returns:
        A populated CompanyState if the ticker is a real public company,
        None if the ticker is invalid/unverifiable (LLM hallucination).
    """
    # Guard against LLM hallucinated placeholder tickers
    if not candidate.ticker or candidate.ticker.strip().upper() in {
        "NONE",
        "N/A",
        "UNKNOWN",
        "",
    }:
        return None

    info = await asyncio.to_thread(get_company_profile, candidate.ticker)
    if info is None:
        return None

    return CompanyState(
        ticker=info["ticker"],
        company_name=info["company_name"],
        ai_factory_segment=segment_key,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dedup helper
#
# A company can legitimately appear under multiple segments (e.g.
# Vertiv makes both power infrastructure AND cooling systems). Per the
# project scope ("Primary AI Factory role", one score set "for each
# company", distinct companies in the Top 20), we merge these into one
# record per ticker rather than keeping duplicate entries. Primary
# segment = the one with the highest weight_pct, since that's where
# the company's AI Factory exposure is most concentrated by dollar share.
# ─────────────────────────────────────────────────────────────────────────────
def dedupe_companies(
    companies: list[CompanyState],
    segment_framework: dict[AIFactorySegment, dict],
) -> list[CompanyState]:
    """
    Merge duplicate tickers (found under multiple segments) into single
    records, tracking all matched segments while keeping one as primary.

    Args:
        companies:         Raw list, may contain duplicate tickers across segments.
        segment_framework: segment -> {weight_pct, description}, used to
                            decide which segment is "primary" when a
                            company spans multiple.

    Returns:
        Deduplicated list, one CompanyState per unique ticker.
    """
    merged: dict[str, CompanyState] = {}

    for company in companies:
        ticker = company.ticker

        if ticker not in merged:
            # First time seeing this ticker — start tracking it
            if company.ai_factory_segment is not None:
                company.all_segments = [company.ai_factory_segment]
            merged[ticker] = company
            continue

        # Already seen this ticker under a different segment — merge
        existing = merged[ticker]
        new_segment = company.ai_factory_segment

        if new_segment is not None and new_segment not in existing.all_segments:
            existing.all_segments.append(new_segment)

        # Re-decide primary segment: whichever has the highest weight_pct
        existing_weight = (
            segment_framework.get(existing.ai_factory_segment, {}).get("weight_pct", 0)
            if existing.ai_factory_segment is not None
            else 0
        )
        new_weight = (
            segment_framework.get(new_segment, {}).get("weight_pct", 0)
            if new_segment is not None
            else 0
        )

        if new_weight > existing_weight:
            existing.ai_factory_segment = new_segment

    return list(merged.values())


# ─────────────────────────────────────────────────────────────────────────────
# The LangGraph node
# ─────────────────────────────────────────────────────────────────────────────
async def company_ingestion_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Company Ingestion

    Reads:
        state.segment_framework: segment -> {weight_pct, description},
                                  set by Market Mapping

    Writes:
        state.companies:    deduplicated list of verified CompanyState records
        state.current_step: "company_ingestion_complete"
        state.error:        semicolon-joined per-segment errors, or None

    Flow:
        1. For each segment in segment_framework:
           a. Run 3 varied Tavily search queries for broader coverage
           b. Dedupe search results by URL before feeding to the LLM
           c. LLM extracts structured {ticker, company_name} list
           d. Verify each candidate against yfinance
        2. Collect all verified companies across segments
        3. Dedupe by ticker (a company can span multiple segments)
        4. Return partial state update
    """
    if not state.segment_framework:
        return {"error": "No segment_framework found. Run Market Mapping first."}

    print("\n[Company Ingestion] Starting company search across segments...")

    llm = build_ingestion_llm()
    structured_llm = llm.with_structured_output(CompanyCandidateList)
    chain = EXTRACTION_PROMPT | structured_llm

    all_companies: list[CompanyState] = []
    errors: list[str] = []

    for segment_key, segment_info in state.segment_framework.items():
        print(f"[Company Ingestion] Searching segment: {segment_key}...")
        try:
            # Multiple query angles per segment for broader coverage —
            # a single query often isn't enough to surface 10-15+
            # distinct companies, especially for niche segments.
            queries = [
                f"public companies {segment_info['description']} AI data center",
                f"top {segment_key} companies stocks AI infrastructure",
                f"{segment_info['description']} market leaders publicly traded",
            ]

            raw_results = []
            for q in queries:
                r = await asyncio.to_thread(tavily_search, q, max_results=3)
                raw_results.extend(r)

            # Dedupe search results by URL before feeding to the LLM —
            # avoids the same article/page appearing multiple times and
            # skewing the extraction toward whatever it repeats most.
            seen_urls = set()
            results = []
            for r in raw_results:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    results.append(r)

            if not results:
                print(f"[Company Ingestion] {segment_key}: no search results, skipping")
                continue

            results_text = "\n".join(
                f"- {r['title']} ({r['content'][:300]})" for r in results
            )

            extracted = await _extract_with_retry(
                chain,
                {
                    "segment": segment_key,
                    "description": segment_info["description"],
                    "search_results": results_text,
                },
            )

            verified = []
            for c in extracted.companies:
                verified.append(await verify_candidate(c, segment_key))

            found = [c for c in verified if c is not None]
            all_companies.extend(found)

            print(
                f"[Company Ingestion] {segment_key}: "
                f"{len(extracted.companies)} candidates, {len(found)} verified "
                f"(from {len(results)} unique search results)"
            )

        except Exception as e:  # noqa: BLE001
            print(f"[Company Ingestion] {segment_key} failed: {e}")
            errors.append(f"{segment_key}: {e}")

    print(f"[Company Ingestion] {len(all_companies)} raw entries before dedup.")

    deduped = dedupe_companies(all_companies, state.segment_framework)

    print(
        f"[Company Ingestion] Done. {len(deduped)} unique companies "
        f"(from {len(all_companies)} raw entries)."
    )

    return {
        "companies": deduped,
        "current_step": "company_ingestion_complete",
        "error": "; ".join(errors) if errors else None,
    }
