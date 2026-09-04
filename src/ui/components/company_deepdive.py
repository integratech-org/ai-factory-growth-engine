"""
Company Deep Dive Investigator component.

Displays detailed company analysis including TAFGS score, segment, growth forecast, and risk factors.
"""

import streamlit as st


def render_company_deepdive(company_data: dict | None = None) -> None:
    """
    Render the Company Deep Dive Investigator panel.

    Args:
        company_data: Dict with company details (ticker, name, tafgs, segment, narratives, etc.)
                     None displays placeholder state.
    """

    # Company selector dropdown
    if company_data:
        companies = company_data if isinstance(company_data, list) else [company_data]

        # Create selector options
        company_options = [
            f"{c.get('ticker', '')} - {c.get('company_name', '')}" for c in companies
        ]

        selected = st.selectbox(
            "Select company",
            options=company_options,
            label_visibility="collapsed",
            key="company_selector",
        )

        # Get selected company data
        selected_idx = (
            company_options.index(selected) if selected in company_options else 0
        )
        company = companies[selected_idx]

    else:
        # Placeholder selector
        st.selectbox(
            "Select company",
            options=["NVIDIA - NVIDIA Corp."],
            label_visibility="collapsed",
            disabled=True,
            key="company_selector_placeholder",
        )

    # Get company data from session state
    companies_data = st.session_state.get("companies_data", [])

    if not companies_data:
        st.info("No data available. Run deep search to view results.")
        return

    # If company_data was passed, use the selected company from the selector
    if company_data:
        # Company was already set from the selector above
        company_dict = company
    else:
        # Use first company as fallback
        company_dict = companies_data[0]

    # Convert to dict if needed
    if hasattr(company_dict, "to_dict"):
        company = company_dict.to_dict()
    elif isinstance(company_dict, dict):
        company = company_dict
    else:
        st.error("Invalid company data format")
        return

    st.write("")  # Spacer

    # Company details card
    with st.container(border=True):
        # Add CSS to fix padding - more aggressive selectors
        st.markdown(
            """
            <style>
            /* Fix container padding for company deep dive */
            div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
                gap: 0.75rem;
            }
            /* Reduce container padding globally within this section */
            div[data-testid="stVerticalBlock"] > div {
                padding-top: 0.25rem !important;
            }
            /* Target the first element specifically */
            div[data-testid="stVerticalBlock"] > div:first-child {
                padding-top: 0 !important;
                margin-top: 0 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Company title
        st.markdown(
            f"""
            <h3 style="margin: 0; margin-top: -1rem; font-size: 1.5rem; font-weight: 600; line-height: 1.2;">
                {company.get("ticker", "N/A")} - {company.get("company_name", "N/A")}
            </h3>
            """,
            unsafe_allow_html=True,
        )

        st.write("")  # Small spacer

        # Metrics - stacked vertically
        st.markdown(
            f"""
            <div style="margin-bottom: 0.5rem;">
                <span style="font-size: 0.875rem; opacity: 0.7; font-weight: 500;">Segment :</span>
                <span style="font-size: 0.875rem; font-weight: 600; margin-left: 0.5rem;">{company.get("ai_factory_segment", "N/A")}</span>
            </div>
            <div style="margin-bottom: 0.5rem;">
                <span style="font-size: 0.875rem; opacity: 0.7; font-weight: 500;">TAFGS :</span>
                <span style="font-size: 0.875rem; font-weight: 600; margin-left: 0.5rem;">{company.get("tafgs_score", 0):.2f}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")  # Spacer

        # Growth Forecast section
        st.markdown(
            """
            <div style="margin-bottom: 0.75rem;">
                <span style="font-size: 0.9rem; font-weight: 600;">Growth Forecast</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Use native Streamlit success box with green border
        st.success(company.get("growth_narrative", "No growth forecast available."))

        # Risk Factors section
        st.markdown(
            """
            <div style="margin-bottom: 0.75rem;">
                <span style="font-size: 0.9rem; font-weight: 600;">Risk Factors</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Use native Streamlit error box with red border
        st.error(company.get("risk_notes", "No risk factors identified."))
