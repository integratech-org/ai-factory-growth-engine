"""
Company Ingestion Agent — identifies eligible public companies globally
with exposure to AI Factory infrastructure build-outs.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Literal

from graph.state import AgentState, CompanyState
from tools.financial import get_company_profile_async
from tools.search import tavily_search


# ─────────────────────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────────────────────

Segment = Literal[
    "compute",
    "networking",
    "power",
    "cooling",
    "construction",
]


# ─────────────────────────────────────────────────────────────────────
# Global public-company seed universe
# ─────────────────────────────────────────────────────────────────────

COMPANY_UNIVERSE: dict[str, tuple[str, Segment]] = {
    # Compute
    "NVDA": ("NVIDIA", "compute"),
    "AMD": ("Advanced Micro Devices", "compute"),
    "AVGO": ("Broadcom", "compute"),
    "ARM": ("Arm Holdings", "compute"),
    "TSM": ("Taiwan Semiconductor Manufacturing Company", "compute"),
    "MU": ("Micron Technology", "compute"),
    "005930.KS": ("Samsung Electronics", "compute"),
    "000660.KS": ("SK hynix", "compute"),
    "INTC": ("Intel", "compute"),
    # Networking
    "ANET": ("Arista Networks", "networking"),
    "CSCO": ("Cisco Systems", "networking"),
    "MRVL": ("Marvell Technology", "networking"),
    "LITE": ("Lumentum", "networking"),
    "COHR": ("Coherent", "networking"),
    "CIEN": ("Ciena", "networking"),
    "NOK": ("Nokia", "networking"),
    "ERIC": ("Ericsson", "networking"),
    # Power
    "VRT": ("Vertiv", "power"),
    "ETN": ("Eaton", "power"),
    "GEV": ("GE Vernova", "power"),
    "PWR": ("Quanta Services", "power"),
    "SU.PA": ("Schneider Electric", "power"),
    "ABB": ("ABB", "power"),
    "SIEMENS.DE": ("Siemens", "power"),
    "HUBB": ("Hubbell", "power"),
    # Cooling
    "CARR": ("Carrier Global", "cooling"),
    "TT": ("Trane Technologies", "cooling"),
    "JCI": ("Johnson Controls", "cooling"),
    "XYL": ("Xylem", "cooling"),
    "NIBE-B.ST": ("NIBE Industrier", "cooling"),
    # Construction / Data-center infrastructure
    "EQIX": ("Equinix", "construction"),
    "DLR": ("Digital Realty", "construction"),
    "V": ("Vinci", "construction"),
    "ACM": ("AECOM", "construction"),
    "J": ("Jacobs Solutions", "construction"),
    "EME": ("EMCOR Group", "construction"),
    "FLR": ("Fluor", "construction"),
}


# ─────────────────────────────────────────────────────────────────────
# AI Factory evidence keywords
# ─────────────────────────────────────────────────────────────────────

SEGMENT_TERMS: dict[Segment, tuple[str, ...]] = {
    "compute": (
        "gpu",
        "accelerator",
        "ai server",
        "data center server",
        "hbm",
        "ai compute",
    ),
    "networking": (
        "ai networking",
        "ethernet",
        "infiniband",
        "optical",
        "data center network",
    ),
    "power": (
        "data center power",
        "switchgear",
        "ups",
        "generator",
        "grid",
        "ai data center power",
    ),
    "cooling": (
        "liquid cooling",
        "data center cooling",
        "chiller",
        "thermal management",
        "crac",
        "crah",
    ),
    "construction": (
        "data center construction",
        "hyperscale",
        "data center build",
        "data center campus",
        "commissioning",
    ),
}


# ─────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────


def _evidence_score(
    text: str,
    segment: Segment,
) -> int:
    """Count segment-specific AI Factory terms in search evidence."""

    normalized = text.lower()

    return sum(1 for term in SEGMENT_TERMS[segment] if term in normalized)


def _extract_exposure_pct(
    text: str,
) -> float | None:
    """
    Extract an explicitly stated revenue/exposure percentage.

    This does not estimate exposure. If no explicit percentage
    is found, None is returned.
    """

    patterns = (
        r"(?:approximately|about|roughly|around|over|more than)?\s*"
        r"(\d+(?:\.\d+)?)\s*%\s*(?:of|revenue|sales)",
        r"(\d+(?:\.\d+)?)\s*%\s*"
        r"(?:revenue|sales).*?"
        r"(?:data center|ai)",
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match is None:
            continue

        try:
            value = float(match.group(1))
        except TypeError, ValueError:
            continue

        if 0 <= value <= 100:
            return value

    return None


# ─────────────────────────────────────────────────────────────────────
# Company validation
# ─────────────────────────────────────────────────────────────────────


async def _validate_company(
    ticker: str,
    name: str,
    segment: Segment,
) -> CompanyState | None:
    """
    Validate one candidate company.

    The company must:
    1. Have a valid public-company profile.
    2. Have search evidence connecting it to the selected
       AI Factory infrastructure segment.
    """

    # Get company profile through the async wrapper.
    profile = await get_company_profile_async(ticker)

    if not profile:
        return None

    company_name = profile.get("longName") or profile.get("shortName") or name

    # Search for AI Factory exposure.
    queries = (
        f'"{company_name}" AI data center {segment}',
        f'"{company_name}" AI factory infrastructure {segment}',
    )

    results: list[dict[str, Any]] = []

    for query in queries:
        search_results = await asyncio.to_thread(
            tavily_search,
            query,
            5,
        )

        results.extend(search_results)

    # Combine search evidence.
    evidence_text = " ".join(
        f"{result.get('title', '')} {result.get('content', '')}" for result in results
    )

    # Require at least one relevant segment-specific term.
    if (
        _evidence_score(
            evidence_text,
            segment,
        )
        == 0
    ):
        return None

    exposure = _extract_exposure_pct(evidence_text)

    return CompanyState(
        ticker=ticker,
        company_name=company_name,
        ai_factory_segment=segment,
        all_segments=[segment],
        revenue_exposure_pct=exposure,
    )


# ─────────────────────────────────────────────────────────────────────
# Safe wrapper
# ─────────────────────────────────────────────────────────────────────


async def _safe_validate_company(
    ticker: str,
    name: str,
    segment: Segment,
) -> tuple[CompanyState | None, str | None]:
    """
    Validate a company without allowing one failure to break
    the entire asyncio.gather() operation.

    Returning a tuple instead of using return_exceptions=True
    prevents Pylance from producing CompanyState | BaseException
    type errors.
    """

    try:
        company = await _validate_company(
            ticker,
            name,
            segment,
        )

        return company, None

    except Exception as exc:
        return None, f"{ticker}: {exc}"


# ─────────────────────────────────────────────────────────────────────
# LangGraph node
# ─────────────────────────────────────────────────────────────────────


async def company_ingestion_node(
    state: AgentState,
) -> dict[str, Any]:
    """
    LangGraph node: Company Ingestion.

    Reads:
        state.segment_framework

    Writes:
        state.companies
        state.current_step
        state.error
    """

    framework = (
        state.get("segment_framework", {})
        if isinstance(state, dict)
        else state.segment_framework
    ) or {}

    # Keep the type as Segment rather than generic str.
    segments: list[Segment] = [
        segment for segment in SEGMENT_TERMS if segment in framework
    ]

    # Fallback when Market Mapping has not populated the framework.
    if not segments:
        segments = list(SEGMENT_TERMS.keys())

    print(
        "\n[Company Ingestion] "
        f"Validating public companies across "
        f"{len(segments)} segments..."
    )

    # Build candidates.
    candidates: list[tuple[str, str, Segment]] = [
        (
            ticker,
            name,
            segment,
        )
        for ticker, (name, segment) in COMPANY_UNIVERSE.items()
        if segment in segments
    ]

    # Validate companies concurrently.
    validation_results = await asyncio.gather(
        *(
            _safe_validate_company(
                ticker,
                name,
                segment,
            )
            for ticker, name, segment in candidates
        )
    )

    companies: list[CompanyState] = []
    errors: list[str] = []
    seen: set[str] = set()

    # validation_results contains ONLY:
    # tuple[CompanyState | None, str | None]
    for company, error in validation_results:
        if error is not None:
            errors.append(error)
            continue

        if company is None:
            continue

        if company.ticker in seen:
            continue

        companies.append(company)
        seen.add(company.ticker)

    # Deterministic ordering.
    companies.sort(
        key=lambda company: (
            company.ai_factory_segment or "",
            company.ticker,
        )
    )

    print(f"[Company Ingestion] Ingested {len(companies)} eligible companies.")

    if errors:
        print(f"[Company Ingestion] {len(errors)} candidates could not be validated.")

    return {
        "companies": companies,
        "current_step": "company_ingestion_complete",
        "error": (
            None
            if companies or not errors
            else "No eligible companies could be validated."
        ),
    }
