from __future__ import annotations

from dataclasses import dataclass, field


# IMPORTANT: PLEASE ADJUST THE STATE MODEL AS NEEDED TO FIT YOUR USE CASE. THIS IS A TEMPLATE.
@dataclass
class CompanyState:
    ticker: str
    company_name: str

    # Market Mapping Agent
    ai_factory_segment: str | None = (
        None  # compute, networking, power, cooling, construction
    )

    # Company Ingestion Agent
    revenue_exposure_pct: float | None = None

    # Moat Analysis Agent
    moat_score: float | None = None  # 0-5
    moat_narrative: str | None = None

    # Margin Analysis Agent
    operating_margin: float | None = None
    margin_score: float | None = None  # 0-5

    # Growth Forecast Agent
    growth_cagr_3yr: float | None = None

    # Risk Adjustment Agent
    risk_discount: float | None = None
    risk_notes: str | None = None

    # Ranking Agent
    tafgs_score: float | None = None
    rank: int | None = None


# IMPORTANT: PLEASE ADJUST THE STATE MODEL AS NEEDED TO FIT YOUR USE CASE. THIS IS A TEMPLATE.


@dataclass
class AgentState:
    companies: list[CompanyState] = field(default_factory=list)
    current_step: str = ""
