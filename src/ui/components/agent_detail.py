"""
Agent detail component for AI Factory Growth Engine.

Displays agent execution history in ChatGPT-style conversation view.
"""

import streamlit as st
from typing import Any


def render_agent_detail(agent_key: str, agent_name: str) -> None:
    """
    Render agent detail view with ChatGPT-style execution history.

    Args:
        agent_key: Agent identifier (e.g., 'market_mapping')
        agent_name: Display name (e.g., 'Market Mapping')
    """

    # Recent Executions Header
    st.markdown(
        '<h2 style="margin: 0 0 1rem 0; font-size: 1.25rem; font-weight: 600; color: #1d2f2d;">Recent Executions</h2>',
        unsafe_allow_html=True,
    )

    # Get execution history from session state
    # TODO: Replace with actual LangGraph checkpoint queries
    executions = _get_agent_executions(agent_key)

    if not executions:
        st.markdown(
            """
            <div style="padding: 0.75rem 1rem; background-color: #f0f7ff; border: 1px solid #d0e4ff; border-radius: 6px; margin: 1rem 0;">
                <p style="margin: 0; color: #1f2937; font-size: 0.875rem; line-height: 1.5;">
                    No data available. Run deep search to view results.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Render executions in ChatGPT-style
    for execution in executions:
        _render_execution_item(execution, agent_key)


def _get_agent_executions(agent_key: str) -> list[dict[str, Any]]:
    """
    Get execution history for a specific agent from LangGraph state.

    Uses real data from st.session_state.companies_data after pipeline execution.
    """
    # Get current session data
    session_counter = st.session_state.get("session_counter", 0)
    session_id = f"session_{session_counter}" if session_counter > 0 else "session_1"
    companies_data = st.session_state.get("companies_data", [])

    # If we have actual results, build execution from that
    if companies_data and len(companies_data) > 0:
        return _build_executions_from_state(agent_key, session_id, companies_data)

    # No data yet - return empty list
    return []


def _build_executions_from_state(
    agent_key: str, session_id: str, companies: list
) -> list[dict]:
    """Build execution records from current state data."""

    # Convert CompanyState objects to dicts if needed
    companies_list = []
    for c in companies:
        if isinstance(c, dict):
            companies_list.append(c)
        else:
            companies_list.append(c.to_dict())

    # Extract relevant data based on agent type
    if agent_key == "market_mapping":
        # Get unique segments from companies
        segments = set(
            c.get("ai_factory_segment")
            for c in companies_list
            if c.get("ai_factory_segment")
        )
        return [
            {
                "session_id": session_id,
                "input": {"tickers": [c.get("ticker") for c in companies_list[:20]]},
                "output": {
                    "segments_identified": len(segments),
                    "segments": list(segments),
                    "total_companies": len(companies_list),
                },
            }
        ]

    elif agent_key == "company_ingestion":
        company_data = []
        for c in companies_list[:20]:
            company_data.append(
                {
                    "ticker": c.get("ticker"),
                    "company_name": c.get("company_name"),
                    "segment": c.get("ai_factory_segment"),
                    "revenue_exposure_pct": c.get("revenue_exposure_pct"),
                }
            )
        return [
            {
                "session_id": session_id,
                "input": {
                    "segments": list(
                        set(
                            c.get("ai_factory_segment")
                            for c in companies_list
                            if c.get("ai_factory_segment")
                        )
                    )
                },
                "output": {
                    "companies_processed": len(companies_list),
                    "companies": company_data,
                },
            }
        ]

    elif agent_key == "moat_analysis":
        moat_data = []
        for c in companies_list[:20]:
            if c.get("moat_score") is not None:
                moat_data.append(
                    {
                        "ticker": c.get("ticker"),
                        "company_name": c.get("company_name"),
                        "moat_score": c.get("moat_score"),
                        "moat_narrative": c.get(
                            "moat_narrative", "No narrative available"
                        ),
                    }
                )
        return [
            {
                "session_id": session_id,
                "input": {"companies": [c.get("ticker") for c in companies_list[:20]]},
                "output": {"companies_analyzed": len(moat_data), "results": moat_data},
            }
        ]

    elif agent_key == "margin_analysis":
        margin_data = []
        for c in companies_list[:20]:
            if (
                c.get("margin_score") is not None
                or c.get("operating_margin") is not None
            ):
                margin_data.append(
                    {
                        "ticker": c.get("ticker"),
                        "company_name": c.get("company_name"),
                        "operating_margin": c.get("operating_margin"),
                        "margin_score": c.get("margin_score"),
                    }
                )
        return [
            {
                "session_id": session_id,
                "input": {"companies": [c.get("ticker") for c in companies_list[:20]]},
                "output": {
                    "companies_analyzed": len(margin_data),
                    "results": margin_data,
                },
            }
        ]

    elif agent_key == "growth_forecast":
        growth_data = []
        for c in companies_list[:20]:
            if c.get("growth_cagr_3yr") is not None:
                growth_data.append(
                    {
                        "ticker": c.get("ticker"),
                        "company_name": c.get("company_name"),
                        "growth_cagr_3yr": c.get("growth_cagr_3yr"),
                        "growth_narrative": c.get(
                            "growth_narrative", "No narrative available"
                        ),
                    }
                )
        return [
            {
                "session_id": session_id,
                "input": {"companies": [c.get("ticker") for c in companies_list[:20]]},
                "output": {
                    "companies_analyzed": len(growth_data),
                    "results": growth_data,
                },
            }
        ]

    elif agent_key == "risk_adjustment":
        risk_data = []
        for c in companies_list[:20]:
            if c.get("risk_discount") is not None or c.get("risk_notes"):
                risk_data.append(
                    {
                        "ticker": c.get("ticker"),
                        "company_name": c.get("company_name"),
                        "risk_discount": c.get("risk_discount"),
                        "customer_concentration_pct": c.get(
                            "customer_concentration_pct"
                        ),
                        "cyclicality_tag": c.get("cyclicality_tag"),
                        "execution_flags": c.get("execution_flags", []),
                        "risk_notes": c.get("risk_notes", "No risk notes available"),
                    }
                )
        return [
            {
                "session_id": session_id,
                "input": {"companies": [c.get("ticker") for c in companies_list[:20]]},
                "output": {"companies_analyzed": len(risk_data), "results": risk_data},
            }
        ]

    elif agent_key == "ranking_agent":
        ranked = sorted(
            [c for c in companies_list if c.get("tafgs_score")],
            key=lambda x: x.get("tafgs_score", 0),
            reverse=True,
        )

        # Show top 20 with full details
        top_companies = []
        for c in ranked[:20]:
            top_companies.append(
                {
                    "rank": c.get("rank"),
                    "ticker": c.get("ticker"),
                    "company_name": c.get("company_name"),
                    "tafgs_score": c.get("tafgs_score"),
                    "moat_score": c.get("moat_score"),
                    "margin_score": c.get("margin_score"),
                    "growth_cagr_3yr": c.get("growth_cagr_3yr"),
                    "risk_discount": c.get("risk_discount"),
                    "ai_factory_segment": c.get("ai_factory_segment"),
                }
            )

        return [
            {
                "session_id": session_id,
                "input": {"companies_count": len(companies_list)},
                "output": {
                    "companies_ranked": len(ranked),
                    "top_20": top_companies,
                    "average_tafgs": sum(c.get("tafgs_score", 0) for c in ranked)
                    / len(ranked)
                    if ranked
                    else 0,
                    "highest_tafgs": ranked[0].get("tafgs_score") if ranked else 0,
                    "lowest_tafgs": ranked[-1].get("tafgs_score") if ranked else 0,
                },
            }
        ]

    elif agent_key == "report_agent":
        # Get report markdown from session state
        report_markdown = (
            st.session_state.get("result", {}).get("report_markdown")
            if isinstance(st.session_state.get("result"), dict)
            else None
        )

        # Calculate report statistics
        top_20 = sorted(
            [c for c in companies_list if c.get("tafgs_score")],
            key=lambda x: x.get("tafgs_score", 0),
            reverse=True,
        )[:20]

        # Segment breakdown
        segment_counts: dict[str, int] = {}
        for c in top_20:
            seg = c.get("ai_factory_segment", "unknown")
            segment_counts[seg] = segment_counts.get(seg, 0) + 1

        # Top 5 companies for quick reference
        top_5_summary = []
        for c in top_20[:5]:
            top_5_summary.append(
                {
                    "rank": c.get("rank"),
                    "ticker": c.get("ticker"),
                    "company_name": c.get("company_name"),
                    "tafgs_score": c.get("tafgs_score"),
                    "segment": c.get("ai_factory_segment"),
                }
            )

        return [
            {
                "session_id": session_id,
                "input": {"companies": len(companies_list), "top_n": 20},
                "output": {
                    "report_generated": True,
                    "companies_in_report": min(len(companies_list), 20),
                    "report_length_chars": len(report_markdown)
                    if report_markdown
                    else 0,
                    "report_length_words": len(report_markdown.split())
                    if report_markdown
                    else 0,
                    "segment_breakdown": segment_counts,
                    "top_5_companies": top_5_summary,
                    "average_tafgs_top20": sum(c.get("tafgs_score", 0) for c in top_20)
                    / len(top_20)
                    if top_20
                    else 0,
                    "report_sections": [
                        "Executive Summary",
                        "Top 20 Companies Table",
                        "Key Insights",
                        "Competitive Notes",
                    ],
                },
            }
        ]

    return []


def _render_execution_item(execution: dict, agent_key: str) -> None:
    """Render a single execution in ChatGPT-style format with markdown text."""
    session_id = execution.get("session_id", "Unknown session")
    input_data = execution.get("input", {})
    output_data = execution.get("output", {})

    # Get agent name for display
    agent_names = {
        "market_mapping": "Market Mapping Agent",
        "company_ingestion": "Company Ingestion Agent",
        "moat_analysis": "Moat Analysis Agent",
        "margin_analysis": "Margin Analysis Agent",
        "growth_forecast": "Growth Forecast Agent",
        "risk_adjustment": "Risk Adjustment Agent",
        "ranking_agent": "Ranking Agent",
        "report_agent": "Report Agent",
    }
    agent_name = agent_names.get(agent_key, "Agent")

    # Add CSS to fix border radius
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
            border-radius: 12px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Use st.container with border styling
    container = st.container(border=True)

    with container:
        # Header with border
        st.markdown(
            f"""
            <div style="margin: -1rem -1rem 1rem -1rem; padding: 0.75rem 1rem; background: #f9fafb; border: 1px solid #e5e7eb; border-left: none; border-right: none; border-top: none; display: flex; align-items: center; gap: 0.5rem;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                </svg>
                <span style="font-size: 0.875rem; color: #374151; font-weight: 600;">{agent_name}</span>
                <span style="font-size: 0.875rem; color: #6b7280; margin-left: auto;">{session_id}</span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Main content title
        st.markdown(
            f"""
            <div style="margin-bottom: 1rem;">
                <h3 style="margin: 0; padding: 0; font-size: 1.15rem; font-weight: 600; color: #10b981; line-height: 1.4;">
                    # {agent_name.replace(" Agent", "")} Results
                </h3>
                <p style="margin: 0.25rem 0 0 0; padding: 0; font-size: 0.875rem; color: #6b7280; line-height: 1.4;">
                    {_get_agent_description_short(agent_key)}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Recent Execution section
        st.markdown(
            f"""
            <div style="margin-bottom: 1rem;">
                <h4 style="margin: 0 0 0.5rem 0; padding: 0; font-size: 0.9rem; font-weight: 600; color: #10b981;">
                    ## Recent Execution
                </h4>
                <div style="font-size: 0.875rem; color: #374151; line-height: 1.6;">
                    Session: {session_id} - Completed: May 26, 2024 09:15 AM - Duration: 00:35:00
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # INPUT section
        st.markdown(
            """
            <h4 style="margin: 1rem 0 0.5rem 0; padding: 0; font-size: 0.9rem; font-weight: 600; color: #3b82f6;">
                ## INPUT
            </h4>
            """,
            unsafe_allow_html=True,
        )
        _render_as_markdown(input_data)

        # OUTPUT section
        st.markdown(
            """
            <h4 style="margin: 1.5rem 0 0.5rem 0; padding: 0; font-size: 0.9rem; font-weight: 600; color: #10b981;">
                ## OUTPUT
            </h4>
            """,
            unsafe_allow_html=True,
        )
        _render_as_markdown(output_data)


def _get_agent_description_short(agent_key: str) -> str:
    """Get short agent description."""
    descriptions = {
        "market_mapping": "Identifies and categorizes companies within AI factory infrastructure segments.",
        "company_ingestion": "Processes and validates company data including financial metrics and market positioning.",
        "moat_analysis": "Evaluates competitive advantages, barriers to entry, and long-term defensibility of business models.",
        "margin_analysis": "Analyzes profitability metrics, cost structures, and operational efficiency across segments.",
        "growth_forecast": "Projects revenue growth trajectories using historical data, market trends, and segment dynamics.",
        "risk_adjustment": "Assesses regulatory, operational, competitive, and financial risks to adjust valuation scores.",
        "ranking_agent": "Aggregates scores across moat, margin, growth, and risk factors to generate TAFGS rankings.",
        "report_agent": "Synthesizes analysis into comprehensive investment reports with key insights and recommendations.",
    }
    return descriptions.get(agent_key, "")


def _render_as_markdown(data: dict, indent: int = 0) -> None:
    """Render dict as clean, readable vertical markdown matching LangGraph output."""
    if not data:
        st.markdown("*No data*")
        return

    for key, value in data.items():
        # Format key nicely
        display_key = key.replace("_", " ").title()

        if isinstance(value, dict):
            # Nested dict - show as expandable section
            st.markdown(f"**{display_key}:**")
            _render_nested_dict(value, indent + 1)
            st.markdown("")  # Spacing

        elif isinstance(value, list):
            # List - show count and items vertically
            st.markdown(f"**{display_key}:** `{len(value)}` items")
            _render_list_items(value, indent + 1)
            st.markdown("")  # Spacing

        else:
            # Simple value - inline
            st.markdown(f"**{display_key}:** `{value}`")


def _render_nested_dict(data: dict, indent: int = 0) -> None:
    """Render nested dictionary with proper indentation."""
    prefix = "  " * indent

    for key, value in data.items():
        display_key = key.replace("_", " ").title()

        if isinstance(value, dict):
            st.markdown(f"{prefix}• **{display_key}:**")
            for k, v in value.items():
                st.markdown(f"{prefix}  - {k.replace('_', ' ').title()}: `{v}`")
        elif isinstance(value, list):
            st.markdown(f"{prefix}• **{display_key}:** `{len(value)}` items")
        else:
            st.markdown(f"{prefix}• {display_key}: `{value}`")


def _render_list_items(items: list, indent: int = 0) -> None:
    """Render list items vertically with proper structure."""
    for item in items:
        if isinstance(item, dict):
            _render_company_item(item, indent)
        else:
            st.markdown(f"{'  ' * indent}• `{item}`")


def _render_company_item(company: dict, indent: int = 0) -> None:
    """Render a company/item dict in vertical readable format."""
    prefix = "  " * indent

    # Check if this is a company record (has ticker)
    if "ticker" in company:
        ticker = company.get("ticker", "")
        company_name = company.get("company_name", "")

        # Header with rank if available
        if company.get("rank"):
            st.markdown(
                f"{prefix}**#{company.get('rank')} - {ticker}** - {company_name}"
            )
        else:
            st.markdown(f"{prefix}**{ticker}** - {company_name}")

        # Organization by agent responsibility
        # Market Mapping / Company Ingestion fields
        if "ai_factory_segment" in company or "revenue_exposure_pct" in company:
            segment_data = []
            if company.get("ai_factory_segment"):
                segment_data.append(f"Segment: `{company['ai_factory_segment']}`")
            if company.get("all_segments"):
                segment_data.append(
                    f"All Segments: `{', '.join(company['all_segments'])}`"
                )
            if company.get("revenue_exposure_pct") is not None:
                segment_data.append(
                    f"Revenue Exposure: `{company['revenue_exposure_pct']}%`"
                )
            if segment_data:
                st.markdown(f"{prefix}  - " + " - ".join(segment_data))

        # Moat Analysis fields
        if "moat_score" in company or "moat_narrative" in company:
            if company.get("moat_score") is not None:
                st.markdown(f"{prefix}  - Moat Score: `{company['moat_score']}/5.0`")
            if company.get("moat_narrative"):
                st.markdown(f"{prefix}  - Moat: {company['moat_narrative']}")

        # Margin Analysis fields
        if "operating_margin" in company or "margin_score" in company:
            margin_data = []
            if company.get("operating_margin") is not None:
                margin_data.append(
                    f"Operating Margin: `{company['operating_margin']}%`"
                )
            if company.get("margin_score") is not None:
                margin_data.append(f"Score: `{company['margin_score']}/5.0`")
            if margin_data:
                st.markdown(f"{prefix}  - " + " - ".join(margin_data))
            if company.get("margin_narrative"):
                st.markdown(f"{prefix}  - Margin: {company['margin_narrative']}")

        # Growth Forecast fields
        if "growth_cagr_3yr" in company or "growth_narrative" in company:
            if company.get("growth_cagr_3yr") is not None:
                st.markdown(
                    f"{prefix}  - Growth CAGR (3yr): `{company['growth_cagr_3yr'] * 100:.1f}%`"
                )
            if company.get("growth_narrative"):
                st.markdown(f"{prefix}  - Growth: {company['growth_narrative']}")

        # Risk Adjustment fields
        if any(
            k in company
            for k in [
                "customer_concentration_pct",
                "cyclicality_tag",
                "risk_discount",
                "risk_notes",
                "execution_flags",
            ]
        ):
            risk_data = []
            if company.get("risk_discount") is not None:
                risk_data.append(f"Risk Discount: `{company['risk_discount']}`")
            if company.get("customer_concentration_pct") is not None:
                risk_data.append(
                    f"Customer Concentration: `{company['customer_concentration_pct']}%`"
                )
            if company.get("cyclicality_tag"):
                risk_data.append(f"Cyclicality: `{company['cyclicality_tag']}`")
            if risk_data:
                st.markdown(f"{prefix}  - " + " - ".join(risk_data))
            if company.get("execution_flags"):
                st.markdown(
                    f"{prefix}  - Execution Flags: `{', '.join(company['execution_flags'])}`"
                )
            if company.get("risk_notes"):
                st.markdown(f"{prefix}  - Risk: {company['risk_notes']}")

        # Ranking fields - show TAFGS and component scores
        if "tafgs_score" in company:
            ranking_data = []
            if company.get("rank") is not None:
                ranking_data.append(f"Rank: `#{company['rank']}`")
            if company.get("tafgs_score") is not None:
                ranking_data.append(f"TAFGS: `{company['tafgs_score']:.2f}`")
            if ranking_data:
                st.markdown(f"{prefix}  - " + " - ".join(ranking_data))

        # Component scores if available
        if "component_scores" in company:
            st.markdown(f"{prefix}  - Component Scores:")
            for score_key, score_val in company["component_scores"].items():
                st.markdown(
                    f"{prefix}    - {score_key.replace('_', ' ').title()}: `{score_val}`"
                )

        # Error field if present
        if company.get("error"):
            st.markdown(f"{prefix}  - Error: {company['error']}")

        st.markdown("")  # Spacing between companies

    elif "segment" in company:
        # Simple segment entry (used in top_5_companies for Report Agent)
        ticker = company.get("ticker", "")
        name = company.get("company_name", "")
        rank = company.get("rank", "")
        tafgs = company.get("tafgs_score", 0)
        segment = company.get("segment", "")
        st.markdown(
            f"{prefix}**#{rank} - {ticker}** - {name} - TAFGS: `{tafgs:.2f}` - Segment: `{segment}`"
        )

    elif "weight_pct" in company:
        # Segment framework entry
        st.markdown(
            f"{prefix}• **{company.get('description', 'Segment')}:** `{company.get('weight_pct')}%`"
        )

    else:
        # Generic dict - show all fields vertically
        st.markdown(f"{prefix}•")
        for k, v in company.items():
            if not isinstance(v, (dict, list)):
                st.markdown(f"{prefix}  - {k.replace('_', ' ').title()}: `{v}`")
            elif isinstance(v, list):
                st.markdown(
                    f"{prefix}  - {k.replace('_', ' ').title()}: `{len(v)}` items"
                )
        st.markdown("")


def _format_value(value: Any) -> str:
    """Format a value for inline display."""
    if isinstance(value, dict):
        return f"({len(value)} fields)"
    elif isinstance(value, list):
        return f"[{len(value)} items]"
    else:
        return str(value)


def _summarize_dict(item: dict) -> str:
    """Summarize a dict item into a single line."""
    # Try to find key identifiers
    if "ticker" in item:
        parts = [f"`{item['ticker']}`"]
        if "company_name" in item:
            parts.append(item["company_name"])
        if "tafgs_score" in item:
            parts.append(f"TAFGS: {item['tafgs_score']}")
        if "moat_score" in item:
            parts.append(f"Moat: {item['moat_score']}")
        if "operating_margin" in item:
            parts.append(f"Margin: {item['operating_margin']}%")
        if "growth_cagr_3yr" in item:
            parts.append(f"Growth: {item['growth_cagr_3yr'] * 100:.1f}%")
        if "rank" in item:
            parts = [f"Rank {item['rank']}"] + parts
        return " - ".join(parts)
    elif "weight_pct" in item:
        return f"{item.get('weight_pct')}% - {item.get('description', '')}"
    else:
        # Generic: show first few fields
        parts = []
        for k, v in list(item.items())[:3]:
            if not isinstance(v, (dict, list)):
                parts.append(f"{k.replace('_', ' ').title()}: {v}")
        return " - ".join(parts) if parts else str(item)
