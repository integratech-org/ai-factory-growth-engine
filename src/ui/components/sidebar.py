"""
Sidebar component for AI Factory Growth Engine.

Renders brand, navigation tabs, agent list, and current run status card.
"""

import streamlit as st


# SVG icon definitions
ICONS = {
    "chart_line": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>',
    "building": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><path d="M9 22v-4h6v4M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01"></path></svg>',
    "file_text": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>',
    "globe": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
    "users": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
    "shield": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>',
    "pie_chart": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>',
    "trending_up": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>',
    "alert_triangle": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
    "award": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>',
    "file": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>',
}


def render_sidebar() -> None:
    """Render the sidebar with brand, tabs, agents, and current run card."""

    # Inject sidebar styles
    _inject_styles()

    # Brand header with custom AE logo
    col1, col2 = st.sidebar.columns([1, 4])

    with col1:
        st.image("src/assets/AE.svg", width=48)

    with col2:
        st.markdown(
            """
            <div style="margin-left: -0.5rem;">
              <h1 style="margin: 0; padding: 0; font-size: 2.1rem; font-weight: 700; letter-spacing: -0.05em; color: #1d2f2d; line-height: 1;">AI Growth Engine</h1>
              <div style="margin: 0; margin-top: 0.05rem; padding: 0; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.2em; color: #4a6b63; text-transform: uppercase; line-height: 1;">AI Factory Equity Research</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.sidebar.markdown(
        '<div style="margin-bottom: 0.75rem;"></div>', unsafe_allow_html=True
    )

    # Navigation tabs
    _render_tabs()

    # Agents list
    _render_agents()

    # Current run status card
    _render_current_run_card()


def _inject_styles() -> None:
    """Inject sidebar CSS styles."""
    st.markdown(
        """
        <style>
        /* ============================================
           SIDEBAR STYLING
           ============================================ */

        [data-testid="stSidebar"]:not([aria-expanded="false"]) {
            background: #f5f6f3;
            border-right: 1px solid #dfe7e2;
            width: 410px !important;
            min-width: 410px !important;
            max-width: 410px !important;
        }

        /* When sidebar is collapsed */
        [data-testid="stSidebar"][aria-expanded="false"] {
            width: 0 !important;
            min-width: 0 !important;
        }

        [data-testid="stSidebar"] > div {
            padding: 0.25rem 1.2rem 1rem 1.2rem;
        }

        .brand-lockup {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin-bottom: 0;
            margin-left: 0.25rem;
        }

        .brand-icon {
            width: 54px;
            height: 54px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 18px;
            border: 2px solid #1f8c79;
            background: rgba(31, 140, 121, 0.06);
        }

        .brand-icon svg {
            width: 42px;
            height: 42px;
        }

        .brand-text {
            line-height: 1.1;
        }

        .brand-text h1 {
            margin: 0;
            font-size: 2.1rem;
            font-weight: 700;
            letter-spacing: -0.05em;
            color: #1d2f2d;
            line-height: 1;
        }

        .brand-text div {
            margin-top: 0.05rem;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.2em;
            color: #4a6b63;
            text-transform: uppercase;
            line-height: 1.2;
        }

        .sidebar-section-label {
            margin: 0.8rem 0 0.8rem;
            font-size: 0.75rem;
            letter-spacing: 0.15em;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_tabs() -> None:
    """Render navigation tabs section."""
    # Initialize active tab in session state
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "research_control"

    tab_items = [
        ("research_control", "chart_line", "Research Control"),
        ("company_deep_dive", "building", "Company Deep Dive"),
        ("reports_center", "file_text", "Reports Center"),
    ]

    st.sidebar.markdown(
        '<div class="sidebar-section-label">TABS</div>', unsafe_allow_html=True
    )

    for key, icon_key, label in tab_items:
        is_active = st.session_state.active_tab == key

        # Create clickable button for each tab
        if st.sidebar.button(
            label,
            key=f"tab_{key}",
            width="stretch",
            type="primary" if is_active else "secondary",
        ):
            st.session_state.active_tab = key
            st.rerun()


def _render_agents() -> None:
    """Render agents list section."""
    st.sidebar.markdown(
        '<div class="sidebar-section-label">AGENTS</div>', unsafe_allow_html=True
    )
    agent_items = [
        ("market_mapping", "globe", "Market Mapping"),
        ("company_ingestion", "users", "Company Ingestion"),
        ("moat_analysis", "shield", "Moat Analysis"),
        ("margin_analysis", "pie_chart", "Margin Analysis"),
        ("growth_forecast", "trending_up", "Growth Forecast"),
        ("risk_adjustment", "alert_triangle", "Risk Adjustment"),
        ("ranking_agent", "award", "Ranking Agent"),
        ("report_agent", "file", "Report Agent"),
    ]

    # Create container for agents with custom styling
    agent_container = st.sidebar.container()

    with agent_container:
        for key, icon_key, label in agent_items:
            is_active = st.session_state.active_tab == f"agent_{key}"

            # Create clickable button for each agent
            if st.button(
                label,
                key=f"agent_btn_{key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.active_tab = f"agent_{key}"
                st.rerun()


def _render_current_run_card() -> None:
    """Render current run status card using Streamlit components with accurate data."""
    st.sidebar.markdown(
        '<div class="sidebar-section-label" style="margin-top: 1.5rem; margin-bottom: 0.75rem; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.05em; color: #6b7280; text-transform: uppercase;">CURRENT RUN</div>',
        unsafe_allow_html=True,
    )

    # Get real data from session state
    session_id = st.session_state.get("session_id", None)
    companies_data = st.session_state.get("companies_data", [])
    ticker_count = len(st.session_state.get("companies", []))  # Input tickers
    result_count = len(companies_data)  # Actual analyzed companies
    current_step = st.session_state.get("current_step", "idle")

    # Track session counter (increments each run)
    if "session_counter" not in st.session_state:
        st.session_state.session_counter = 0

    # Increment counter when a new session starts
    if session_id and not st.session_state.get("last_session_id"):
        st.session_state.session_counter += 1
        st.session_state.last_session_id = session_id
    elif session_id != st.session_state.get("last_session_id") and session_id:
        st.session_state.session_counter += 1
        st.session_state.last_session_id = session_id

    # Format session display like "session_12"
    if st.session_state.session_counter > 0:
        session_display = f"session_{st.session_state.session_counter}"
    else:
        session_display = "—"

    # Determine status
    if companies_data:
        status = "Completed"
        status_color = "#10b981"
    elif current_step and current_step != "idle":
        status = "Running"
        status_color = "#3b82f6"
    else:
        status = "Idle"
        status_color = "#6b7280"

    # Use native Streamlit container with border and compact padding
    with st.sidebar.container(border=True):
        # Row 1: Session (optimal spacing)
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0 0 0.375rem 0; margin-top: -0.68rem;">
                <span style="color: #6b7280; font-size: 0.8125rem; font-weight: 500;">Session</span>
                <span style="color: #1f2937; font-weight: 600; font-size: 0.8125rem;">{session_display}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Row 2: Ticker Count (input)
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.375rem 0;">
                <span style="color: #6b7280; font-size: 0.8125rem; font-weight: 500;">Input Tickers</span>
                <span style="color: #10b981; font-weight: 700; font-size: 0.9375rem;">{ticker_count}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Row 3: Result Count (analyzed companies)
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.375rem 0;">
                <span style="color: #6b7280; font-size: 0.8125rem; font-weight: 500;">Companies Analyzed</span>
                <span style="color: #10b981; font-weight: 700; font-size: 0.9375rem;">{result_count}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Row 4: Status (no extra padding)
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.375rem 0;">
                <span style="color: #6b7280; font-size: 0.8125rem; font-weight: 500;">Status</span>
                <span style="color: {status_color}; font-weight: 700; font-size: 0.875rem;">{status}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    """Main entry point for testing the sidebar component."""
    render_sidebar()


if __name__ == "__main__":
    main()
