from __future__ import annotations

from dataclasses import asdict, dataclass, field


# ─────────────────────────────────────────────────────────────────────
# Nested data structures
# ─────────────────────────────────────────────────────────────────────
# IMPORTANT: PLEASE ADJUST THE STATE MODEL AS NEEDED TO FIT YOUR USE CASE. THIS IS A TEMPLATE.
@dataclass
class CompanyState:
    """
    A single company being scored through the pipeline.

    Company Ingestion creates these.
    Moat/Margin/Growth/Risk agents fill in their respective fields.
    Ranking computes tafgs_score and rank.
    Report reads the fully-populated record.
    """

    ticker: str
    company_name: str

    # ── Market Mapping Agent / Company Ingestion Agent ────────────────
    ai_factory_segment: str | None = (
        None  # compute, networking, power, cooling, construction
    )
    revenue_exposure_pct: float | None = None

    # ── Moat Analysis Agent ───────────────────────────────────────────
    moat_score: float | None = None  # 0-5
    moat_narrative: str | None = None

    # ── Margin Analysis Agent ─────────────────────────────────────────
    operating_margin: float | None = None
    margin_score: float | None = None  # 0-5

    # ── Growth Forecast Agent ─────────────────────────────────────────
    growth_cagr_3yr: float | None = None

    # ── Risk Adjustment Agent ─────────────────────────────────────────
    risk_discount: float | None = None
    risk_notes: str | None = None

    # ── Ranking Agent ─────────────────────────────────────────────────
    tafgs_score: float | None = None
    rank: int | None = None

    # ── Error handling ────────────────────────────────────────────────
    # If a node fails, it writes the error message here instead of
    # raising an exception. The graph routes to an error handler node.
    # None during normal operation.
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert to plain dict for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CompanyState:
        """Reconstruct from a plain dict (e.g., after JSON round-trip)."""
        return cls(
            ticker=data["ticker"],
            company_name=data["company_name"],
            ai_factory_segment=data.get("ai_factory_segment"),
            revenue_exposure_pct=data.get("revenue_exposure_pct"),
            moat_score=data.get("moat_score"),
            moat_narrative=data.get("moat_narrative"),
            operating_margin=data.get("operating_margin"),
            margin_score=data.get("margin_score"),
            growth_cagr_3yr=data.get("growth_cagr_3yr"),
            risk_discount=data.get("risk_discount"),
            risk_notes=data.get("risk_notes"),
            tafgs_score=data.get("tafgs_score"),
            rank=data.get("rank"),
            error=data.get("error"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# The main state class
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class AgentState:
    # ── Market Mapping output ────────────────────────────────────────
    # Static AI Factory value-chain framework (segment -> weight/description).
    # Set once by market_mapping_node, read by Company Ingestion and Ranking.
    segment_framework: dict = field(default_factory=dict)

    # ── Company roster ────────────────────────────────────────────────
    # Populated by Company Ingestion, enriched by every agent after that.
    companies: list[CompanyState] = field(default_factory=list)

    # ── Pipeline tracking ─────────────────────────────────────────────
    current_step: str = ""

    # ── Error handling ────────────────────────────────────────────────
    # Pipeline-level errors (not tied to a specific company) go here —
    # e.g. Tavily rate limit hit, SEC EDGAR unreachable.
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert to plain dict for JSON serialization."""
        return {
            "segment_framework": self.segment_framework,
            "companies": [c.to_dict() for c in self.companies],
            "current_step": self.current_step,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentState:
        """Reconstruct from a plain dict (e.g., after JSON round-trip)."""
        return cls(
            segment_framework=data.get("segment_framework", {}),
            companies=[CompanyState.from_dict(c) for c in data.get("companies", [])],
            current_step=data.get("current_step", ""),
            error=data.get("error"),
        )


# ─────────────────────────────────────────────────────────────────────
# State factory function
#
# Always use this to create a new pipeline run.
# Never construct AgentState manually — the factory ensures all fields
# have sensible defaults.
# ─────────────────────────────────────────────────────────────────────
def initial_state() -> dict:
    """
    Create the initial state for a new quarterly refresh run.

    Returns a plain dict (not an AgentState instance) since that's what
    graph.ainvoke() expects as input — LangGraph validates/converts it
    against the AgentState schema internally.
    """
    return {
        "segment_framework": {},
        "companies": [],
        "current_step": "",
        "error": None,
    }


# ─────────────────────────────────────────────────────────────────────
# Utility: safe state accessors
#
# These helpers make it safe to read companies from state in agent
# nodes without crashing on dict-vs-dataclass ambiguity after a
# checkpoint resume.
# ─────────────────────────────────────────────────────────────────────
def get_companies(state: dict | AgentState) -> list[CompanyState]:
    """
    Get the company list as CompanyState instances, regardless of
    whether state.companies currently holds dataclass instances or
    plain dicts (post-checkpoint-resume).

    Usage in an agent node:
        for company in get_companies(state):
            ...
    """
    raw = state.get("companies", []) if isinstance(state, dict) else state.companies
    return [
        c if isinstance(c, CompanyState) else CompanyState.from_dict(c) for c in raw
    ]
