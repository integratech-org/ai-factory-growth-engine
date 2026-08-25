"""
Report Agent — produces the investor-ready Top 20 output
(Markdown report, exportable to PDF).
"""

from __future__ import annotations

from typing import Any

from graph.state import AgentState, get_companies


async def report_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Report Agent

    Reads:
        state.companies: The ranked and scored roster of companies.

    Writes:
        - Prints a markdown report to the terminal.
        - Updates current_step to "report_complete".
    """
    print("\n[Report Agent] Generating AI Factory Growth Portfolio Report...")

    companies = get_companies(state)

    if not companies:
        print("[Report Agent] Warning: No companies found in state to report on.")
        return {
            "current_step": "report_failed",
            "report_markdown": None,
            "error": "No companies available for reporting.",
        }

    ranked_companies = sorted(
        [c for c in companies if c.rank is not None or c.tafgs_score is not None],
        key=lambda x: (x.rank if x.rank is not None else 999, -(x.tafgs_score or 0)),
    )
    top_companies = ranked_companies[:20]

    report_lines = [
        "# AI Factory Growth Portfolio Report",
        "## Final Ranked Roster (Top 20 Scored Companies)",
        "",
        "| Rank | Ticker | Name | Segment | Moat Score | Margin Score | CAGR % | TAFGS |",
        "|------|--------|------|---------|------------|--------------|--------|-------|",
    ]

    for i, company in enumerate(top_companies, start=1):
        rank_value = company.rank if company.rank is not None else i
        report_lines.append(
            f"| {rank_value} | {company.ticker} | {company.company_name} | "
            f"{company.ai_factory_segment or 'N/A'} | "
            f"{company.moat_score if company.moat_score is not None else 'N/A'}/5 | "
            f"{company.margin_score if company.margin_score is not None else 'N/A'}/5 | "
            f"{company.growth_cagr_3yr if company.growth_cagr_3yr is not None else 'N/A'}% | "
            f"{company.tafgs_score if company.tafgs_score is not None else 'N/A'} |"
        )

    report_lines.extend(["", "### Key Insights & Competitive Notes"])
    for company in top_companies:
        if company.moat_narrative:
            report_lines.append(f"- **{company.ticker}**: {company.moat_narrative}")
        if company.risk_notes:
            report_lines.append(f"  - *Risk Factors*: {company.risk_notes}")

    report_content = "\n".join(report_lines)

    print("\n" + "=" * 50)
    print(report_content)
    print("=" * 50 + "\n")

    # with open("ai_factory_portfolio_report.md", "w", encoding="utf-8") as file:
    #     file.write(report_content)

    return {
        "current_step": "report_complete",
        "report_markdown": report_content,
    }
