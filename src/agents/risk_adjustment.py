"""
src/agents/risk_adjustment.py

The Risk Adjustment agent.

Responsibility: apply execution, cyclicality, and customer-concentration
discounts to each company's growth profile *before* the Ranking agent
computes the Total AI Factory Growth Score (TAFGS).

TAFGS = (Moat Score × Operating Margin Score) × Forecast AI-Driven Growth

This agent does not change Moat, Margin, or Growth themselves — it
produces a separate `risk_adjustment_factor` (0.65–1.00) per company
that the Ranking agent multiplies onto TAFGS:

    Risk-Adjusted TAFGS = TAFGS × risk_adjustment_factor

Why a multiplier and not a subtractive penalty: TAFGS is already a
product of three terms, so a multiplicative discount composes cleanly
without needing to renormalize the other scores.

ASSUMPTIONS ABOUT UPSTREAM STATE (flag/confirm against teammates' code):
  - state["companies"] is a list[dict] populated by Company Ingestion
    and enriched by Moat / Margin / Growth Forecast agents by the time
    this node runs.
  - Each company dict may contain (all optional, degrade gracefully
    if missing):
        "revenue_exposure_pct"      float, 0-100
        "customer_concentration_pct" float, 0-100  (top-customer /
                                       top-hyperscaler share of AI
                                       Factory-related revenue)
        "cyclicality_tag"           str, one of
                                       "low" | "moderate" | "high"
        "execution_flags"          list[str], free-text risk notes
                                       written by earlier agents
                                       (e.g. "capacity constrained",
                                       "new market entrant",
                                       "single-fab dependency")
  If your team's actual field names differ, only SCORING_INPUTS below
  needs to change — the discount math is independent of field naming.

No search/LLM calls by design: this agent normalizes signals other
agents already gathered, the same way Margin Analysis normalizes a
reported operating margin. If your team wants LLM-driven qualitative
risk narratives (e.g. reading 10-K risk-factor sections), that's a
natural extension point — see `_execution_risk_score()` below for
where a call would slot in.
"""

from __future__ import annotations

from typing import Any

from graph.state import AgentState, CompanyState, get_companies

# ─────────────────────────────────────────────────────────────────────────────
# Risk → discount mapping
#
# Each of the three risk dimensions is scored 0 (no risk) to 5 (severe
# risk), same convention as Moat Score / Operating Margin Score. The
# composite average maps to a discount multiplier applied to TAFGS.
# ─────────────────────────────────────────────────────────────────────────────
MAX_DISCOUNT = 0.35  # worst case: TAFGS × 0.65
MIN_DISCOUNT = 0.0  # best case:  TAFGS × 1.00

# Relative weight of each dimension in the composite risk score.
# Execution risk weighted highest — it's the dimension most directly
# tied to whether forecasted growth actually converts to revenue.
RISK_WEIGHTS = {
    "cyclicality": 0.25,
    "concentration": 0.30,
    "execution": 0.45,
}

CYCLICALITY_SCORES = {
    "low": 1,
    "moderate": 3,
    "high": 5,
}

# Execution-flag keyword → severity, added and capped at 5.
# Extend this list as your team identifies more recurring risk phrases
# in company research notes.
EXECUTION_FLAG_SEVERITY = {
    "capacity constrained": 2,
    "single-fab dependency": 3,
    "single-source dependency": 3,
    "new market entrant": 2,
    "management transition": 2,
    "regulatory exposure": 2,
    "supply chain risk": 2,
    "customer ramp delay": 3,
}


# ─────────────────────────────────────────────────────────────────────────────
# Per-dimension scoring
# ─────────────────────────────────────────────────────────────────────────────
def _get_value(
    company: CompanyState | dict[str, Any], field: str, default: Any = None
) -> Any:
    if isinstance(company, CompanyState):
        return getattr(company, field, default)
    return company.get(field, default)


def _cyclicality_risk_score(company: CompanyState | dict[str, Any]) -> float:
    """0-5. Falls back to 'moderate' if untagged upstream."""
    tag = str(_get_value(company, "cyclicality_tag", "moderate")).lower()
    return CYCLICALITY_SCORES.get(tag, CYCLICALITY_SCORES["moderate"])


def _concentration_risk_score(company: CompanyState | dict[str, Any]) -> float:
    """
    0-5, scaled off top-customer / hyperscaler revenue concentration.
    A company earning most of its AI Factory revenue from 1-2
    hyperscalers is structurally higher risk than one with a
    diversified customer base, regardless of how strong its moat is.
    """
    pct = _get_value(company, "customer_concentration_pct")
    if pct is None:
        return 2.5  # neutral default when data isn't available yet
    if pct >= 70:
        return 5
    if pct >= 50:
        return 4
    if pct >= 30:
        return 3
    if pct >= 15:
        return 2
    return 1


def _execution_risk_score(company: CompanyState | dict[str, Any]) -> float:
    """
    0-5, derived from free-text execution_flags written by earlier
    agents (Company Ingestion / Growth Forecast notes, analyst
    commentary, etc.).

    Extension point: replace/augment this keyword match with an LLM
    call that reads a company's latest 10-K "Risk Factors" section or
    recent earnings-call transcript and returns a structured 0-5
    execution-risk score with a short justification. Keeping it
    keyword-based for now keeps this agent deterministic and free of
    external API dependencies, matching the request for cross-agent
    validation without single-factor bias.
    """
    flags = _get_value(company, "execution_flags") or []
    if not flags:
        return 1.5  # neutral-low default when no flags were raised

    score = 0.0
    for flag in flags:
        flag_lower = str(flag).lower()
        for keyword, severity in EXECUTION_FLAG_SEVERITY.items():
            if keyword in flag_lower:
                score += severity
                break
        else:
            score += 1  # unrecognized flag still counts as mild risk

    return min(score, 5.0)


# ─────────────────────────────────────────────────────────────────────────────
# Composite discount
# ─────────────────────────────────────────────────────────────────────────────
def _risk_adjustment_factor(risk_scores: dict[str, float]) -> float:
    """
    Combine weighted risk dimensions (each 0-5) into a single discount
    multiplier in [1 - MAX_DISCOUNT, 1 - MIN_DISCOUNT].
    """
    weighted_sum = sum(
        risk_scores[dim] * weight for dim, weight in RISK_WEIGHTS.items()
    )
    normalized = weighted_sum / 5.0  # 0.0 (no risk) - 1.0 (max risk)
    discount = MIN_DISCOUNT + normalized * (MAX_DISCOUNT - MIN_DISCOUNT)
    return round(1.0 - discount, 3)


def _assess_company(company: CompanyState | dict[str, Any]) -> dict[str, Any]:
    risk_scores = {
        "cyclicality": _cyclicality_risk_score(company),
        "concentration": _concentration_risk_score(company),
        "execution": _execution_risk_score(company),
    }
    factor = _risk_adjustment_factor(risk_scores)

    return {
        "cyclicality_risk_score": risk_scores["cyclicality"],
        "concentration_risk_score": risk_scores["concentration"],
        "execution_risk_score": risk_scores["execution"],
        "risk_adjustment_factor": factor,
    }


# ─────────────────────────────────────────────────────────────────────────────
# The LangGraph node
# ─────────────────────────────────────────────────────────────────────────────
async def risk_adjustment_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Risk Adjustment

    Reads:
        state.companies: list of company dicts, enriched by upstream
                          agents (Company Ingestion, Moat Analysis,
                          Margin Analysis, Growth Forecast).

    Writes:
                state.companies:  same list, each CompanyState receives the
                                                     multiplicative factor in ``risk_discount``
                                                     and a concise breakdown in ``risk_notes``.
        state.current_step: "risk_adjustment_complete"

    Flow:
        1. For each company, score cyclicality / concentration /
           execution risk (0-5 each).
        2. Combine into a single risk_adjustment_factor (0.65-1.00).
          3. Store the factor for the Ranking agent to apply:
              risk_adjusted_tafgs = tafgs * risk_discount
    """
    companies = get_companies(state)

    if not companies:
        return {
            "current_step": "risk_adjustment_failed",
            "error": "No companies available for risk adjustment.",
        }

    print(
        f"\n[Risk Adjustment] Scoring cyclicality, concentration, and "
        f"execution risk for {len(companies)} companies..."
    )

    updated_companies: list[CompanyState] = []
    for company in companies:
        assessment = _assess_company(company)
        company.risk_discount = assessment["risk_adjustment_factor"]
        company.risk_notes = (
            f"Cyclicality risk: {assessment['cyclicality_risk_score']}/5; "
            f"customer concentration risk: "
            f"{assessment['concentration_risk_score']}/5; "
            f"execution risk: {assessment['execution_risk_score']}/5."
        )
        updated_companies.append(company)

        ticker = company.ticker
        print(
            f"  {ticker}: factor={assessment['risk_adjustment_factor']} "
            f"(cyclicality={assessment['cyclicality_risk_score']}, "
            f"concentration={assessment['concentration_risk_score']}, "
            f"execution={assessment['execution_risk_score']})"
        )

    return {
        "companies": updated_companies,
        "current_step": "risk_adjustment_complete",
    }
