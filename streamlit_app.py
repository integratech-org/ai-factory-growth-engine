"""
streamlit_app.py

Streamlit web interface for AI Factory Growth Engine.

Run:
    streamlit run streamlit_app.py
"""

import os

import streamlit as st
from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.ui.components.sidebar import render_sidebar

# from graph.workflow import build_graph

load_dotenv()

DB_URI = os.getenv("DATABASE_URL")


# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Factory Growth Engine",
    page_icon="📊",
    layout="wide",
)


def init_state():
    defaults = {
        "screen": "INPUT",
        "session_id": None,
        "companies": ["NVDA", "ANET", "VRT"],  # Default tickers
        "result": None,
        "error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


def main():
    from src.ui.components.header import render_header
    from src.ui.components.input_form import render_input_tickers
    from src.ui.components.weights_panel import render_weights_panel

    # Render header styling
    render_header()

    # Render sidebar
    render_sidebar()

    # Add custom CSS for button and layout
    st.markdown(
        """
        <style>
        /* Reduce top padding */
        .block-container {
            padding-top: 2rem !important;
        }

        /* Style the Run Deep Search button */
        button[key="run_search_btn"] {
            height: 40px !important;
            padding: 8px 16px 8px 12px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            border: 2px solid #10b981 !important;
            border-radius: 8px !important;
            background: white !important;
            color: #10b981 !important;
            float: right !important;
            margin-top: -3rem !important;
        }

        button[key="run_search_btn"]:hover {
            background: #ecfdf5 !important;
        }

        /* Add chevron icon before text */
        button[key="run_search_btn"]::before {
            content: '';
            display: inline-block;
            width: 0;
            height: 0;
            border-left: 6px solid #10b981;
            border-top: 5px solid transparent;
            border-bottom: 5px solid transparent;
            margin-right: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Check active tab from session state
    active_tab = st.session_state.get("active_tab", "research_control")

    if active_tab == "research_control":
        # ===== RESEARCH CONTROL TAB =====
        st.title("AI Research Control")
        st.caption(
            "Configure your research pipeline, set strategic weights, and run deep equity research across AI factory infrastructure."
        )

        # Button - will float to the right at title level due to CSS
        if st.button("Run Deep Search", key="run_search_btn"):
            # Get tickers and weights from session state
            tickers = st.session_state.get("companies", [])
            weights = st.session_state.get(
                "weights",
                {
                    "moat": 0.3,
                    "margin": 0.2,
                    "growth": 0.3,
                    "risk": 0.2,
                },
            )

            if not tickers:
                st.error(
                    "Please add at least one company ticker before running search."
                )
            else:
                # Generate session ID
                import uuid

                session_id = str(uuid.uuid4())
                st.session_state.session_id = session_id

                # Show progress
                with st.spinner("Running AI Factory Growth Engine pipeline..."):
                    import asyncio
                    import sys

                    # Fix for Windows: Use SelectorEventLoop instead of ProactorEventLoop
                    # This is required for psycopg async to work on Windows
                    if sys.platform == "win32":
                        asyncio.set_event_loop_policy(
                            asyncio.WindowsSelectorEventLoopPolicy()
                        )

                    # Run the graph
                    try:
                        final_state = asyncio.run(
                            run_graph(tickers, weights, session_id)
                        )

                        # Store results in session state
                        st.session_state.result = final_state
                        st.session_state.companies_data = final_state.get(
                            "companies", []
                        )

                        st.success(
                            f"✓ Analysis complete! Processed {len(final_state.get('companies', []))} companies."
                        )
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error running pipeline: {str(e)}")
                        st.exception(e)

        # Main content - Input Tickers and Strategic Weights
        col1, col2 = st.columns([1, 1])

        with col1:
            render_input_tickers()

        with col2:
            weights = render_weights_panel()

        # Top 20 Results Table
        st.markdown("<br>", unsafe_allow_html=True)

        from src.ui.components.results_table import render_results_table

        # Check if we have results in session state from LangGraph
        results = st.session_state.get("companies_data")

        if results:
            # Convert CompanyState objects to dict format for the table
            table_data = []
            for company in results:
                if isinstance(company, dict):
                    c = company
                else:
                    c = company.to_dict()

                table_data.append(
                    {
                        "rank": c.get("rank", 0),
                        "ticker": c.get("ticker", ""),
                        "company_name": c.get("company_name", ""),
                        "ai_factory_segment": c.get("ai_factory_segment", ""),
                        "moat_score": c.get("moat_score", 0),
                        "margin_score": c.get("margin_score", 0),
                        "growth_cagr_3yr": c.get("growth_cagr_3yr", 0),
                        "tafgs_score": c.get("tafgs_score", 0),
                    }
                )

            render_results_table(table_data)
        else:
            # No results yet - show info message
            st.info(
                "📊 Click 'Run Deep Search' to analyze companies and view results..."
            )

    elif active_tab == "company_deep_dive":
        # ===== COMPANY DEEP DIVE TAB =====
        st.title("Company Deep Dive")
        st.caption(
            "Investigate individual company fundamentals, competitive moats, and growth trajectories."
        )

        # Spacer to match Research Control button area
        st.markdown('<div style="height: 56px;"></div>', unsafe_allow_html=True)

        from src.ui.components.company_deepdive import render_company_deepdive

        # Get results data from LangGraph
        results = st.session_state.get("companies_data")

        if results:
            # Convert CompanyState objects to dict format
            company_data = []
            for company in results:
                if isinstance(company, dict):
                    c = company
                else:
                    c = company.to_dict()

                company_data.append(
                    {
                        "rank": c.get("rank", 0),
                        "ticker": c.get("ticker", ""),
                        "company_name": c.get("company_name", ""),
                        "ai_factory_segment": c.get("ai_factory_segment", ""),
                        "moat_score": c.get("moat_score", 0),
                        "margin_score": c.get("margin_score", 0),
                        "growth_cagr_3yr": c.get("growth_cagr_3yr", 0),
                        "tafgs_score": c.get("tafgs_score", 0),
                        "growth_narrative": c.get(
                            "growth_narrative", "No growth forecast available."
                        ),
                        "risk_notes": c.get(
                            "risk_notes", "No risk factors identified."
                        ),
                    }
                )

            render_company_deepdive(company_data)
        else:
            # No results yet
            st.info(
                "🏢 Click 'Run Deep Search' to analyze companies and view detailed insights..."
            )

    elif active_tab == "reports_center":
        # ===== REPORTS CENTER TAB =====
        st.title("Reports Center")
        st.caption(
            "Access generated investment reports, agent insights, and comprehensive analysis summaries."
        )

        # Spacer to match Research Control button area
        st.markdown('<div style="height: 56px;"></div>', unsafe_allow_html=True)

        from src.ui.components.reports_center import render_reports_center

        # Get results from session state
        results = st.session_state.get("companies_data")

        # Convert CompanyState objects to dict format if needed
        if results:
            table_data = []
            for company in results:
                if isinstance(company, dict):
                    c = company
                else:
                    c = company.to_dict() if hasattr(company, "to_dict") else company

                table_data.append(
                    {
                        "rank": c.get("rank", 0),
                        "ticker": c.get("ticker", ""),
                        "company_name": c.get("company_name", ""),
                        "ai_factory_segment": c.get("ai_factory_segment", ""),
                        "moat_score": c.get("moat_score", 0),
                        "margin_score": c.get("margin_score", 0),
                        "growth_cagr_3yr": c.get("growth_cagr_3yr", 0),
                        "tafgs_score": c.get("tafgs_score", 0),
                    }
                )
            render_reports_center(results=table_data)
        else:
            render_reports_center(results=None)

    elif active_tab.startswith("agent_"):
        # ===== AGENT DETAIL TABS =====
        agent_titles = {
            "agent_market_mapping": "Market Mapping Agent",
            "agent_company_ingestion": "Company Ingestion Agent",
            "agent_moat_analysis": "Moat Analysis Agent",
            "agent_margin_analysis": "Margin Analysis Agent",
            "agent_growth_forecast": "Growth Forecast Agent",
            "agent_risk_adjustment": "Risk Adjustment Agent",
            "agent_ranking_agent": "Ranking Agent",
            "agent_report_agent": "Report Agent",
        }

        agent_descriptions = {
            "agent_market_mapping": "Explore AI factory market segments, identify emerging opportunities, and track sector dynamics.",
            "agent_company_ingestion": "Review raw company data ingestion, validation processes, and data quality metrics.",
            "agent_moat_analysis": "Deep dive into competitive advantages, moat sustainability, and defensive positioning.",
            "agent_margin_analysis": "Analyze unit economics, margin structures, and profitability trajectories over time.",
            "agent_growth_forecast": "Examine revenue projections, growth assumptions, and forward-looking estimates.",
            "agent_risk_adjustment": "Assess risk factors, probability distributions, and uncertainty quantification.",
            "agent_ranking_agent": "Inspect TAFGS score calculations and company ranking methodology.",
            "agent_report_agent": "Access generated reports, insights summaries, and investment recommendations.",
        }

        st.title(agent_titles.get(active_tab, "Agent Details"))
        st.caption(
            agent_descriptions.get(
                active_tab, "View agent execution history and performance data."
            )
        )

        # Spacer to match Research Control button area
        st.markdown('<div style="height: 56px;"></div>', unsafe_allow_html=True)

        from src.ui.components.agent_detail import render_agent_detail

        # Map agent keys to display names
        agent_names = {
            "agent_market_mapping": "Market Mapping",
            "agent_company_ingestion": "Company Ingestion",
            "agent_moat_analysis": "Moat Analysis",
            "agent_margin_analysis": "Margin Analysis",
            "agent_growth_forecast": "Growth Forecast",
            "agent_risk_adjustment": "Risk Adjustment",
            "agent_ranking_agent": "Ranking Agent",
            "agent_report_agent": "Report Agent",
        }

        agent_key = active_tab.replace("agent_", "")
        agent_name = agent_names.get(active_tab, agent_key.replace("_", " ").title())

        render_agent_detail(agent_key, agent_name)


# ── Graph interaction ─────────────────────────────────────────────
async def run_graph(tickers: list[str], weights: dict, session_id: str):
    """
    Execute the AI Factory Growth Engine pipeline.

    Args:
        tickers: List of ticker symbols to analyze
        weights: Strategic weights for TAFGS scoring
        session_id: Unique session ID for checkpointing

    Returns:
        Final AgentState with company rankings and report
    """
    from src.graph.workflow import build_graph
    from src.graph.state import initial_state

    # Check if PostgreSQL is available
    checkpointer = None
    if DB_URI:
        try:
            async with AsyncPostgresSaver.from_conn_string(DB_URI) as cp:
                await cp.setup()
                checkpointer = cp
                print("[run_graph] PostgreSQL checkpointer initialized")
        except Exception as e:
            print(f"[run_graph] Warning: Could not connect to PostgreSQL: {e}")
            print(
                "[run_graph] Running without checkpointing (state won't be persisted)"
            )

    # Build graph with or without checkpointing
    app = build_graph(checkpointer=checkpointer)

    # Create initial state
    state = initial_state()

    # Store tickers and weights in session state for Company Ingestion to use
    state["input_tickers"] = tickers
    state["weights"] = weights

    # Execute graph
    config = {"configurable": {"thread_id": session_id}} if checkpointer else {}

    final_state = await app.ainvoke(state, config=config)

    return final_state


if __name__ == "__main__":
    main()
