"""
The Market Mapping agent.

Responsibility: define the AI Factory value-chain segment framework —
the reference categories (compute, power, cooling, networking,
construction) and their share of AI Factory dollar spend — that every
downstream agent builds on.

This is the simplest agent in the system:
  - No LLM call
  - No search/data tools
  - Pure static lookup, attached to state as-is

It runs first, before any company list exists. Segment-level capex
share is a slow-moving industry statistic, not something that needs
real-time reasoning or search — update AI_FACTORY_SEGMENTS manually
each quarter if the underlying research changes.
"""

from __future__ import annotations

from typing import Any

from graph.state import AgentState

# ─────────────────────────────────────────────────────────────────────────────
# Segment framework
#
# % share of AI Factory dollar spend per infrastructure layer.
# Sourced from own research estimates — update quarterly as needed.
# Read by: Company Ingestion (search targeting), Ranking (segment context).
# ─────────────────────────────────────────────────────────────────────────────
AI_FACTORY_SEGMENTS = {
    "compute": {
        "weight_pct": 58,
        "description": "GPUs, AI servers",
    },
    "power": {
        "weight_pct": 16,
        "description": "Generators, turbines, UPS, switchgear",
    },
    "cooling": {
        "weight_pct": 10,
        "description": "Liquid cooling, chillers, CRAHs",
    },
    "networking": {
        "weight_pct": 8,
        "description": "Ethernet, InfiniBand, optical",
    },
    "construction": {
        "weight_pct": 8,
        "description": "Design, build, commissioning",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# The LangGraph node
# ─────────────────────────────────────────────────────────────────────────────
async def market_mapping_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Market Mapping

    Reads:
        (nothing — this is the first node, runs before any company data exists)

    Writes:
        state.segment_framework: the static AI_FACTORY_SEGMENTS dict
        state.current_step:      "market_mapping_complete"

    Flow:
        1. Attach the static segment framework to state
        2. Return partial state update
    """
    print(
        "\n[Market Mapping] Attaching AI Factory segment framework "
        f"({len(AI_FACTORY_SEGMENTS)} segments)..."
    )

    return {
        "segment_framework": AI_FACTORY_SEGMENTS,
        "current_step": "market_mapping_complete",
    }
