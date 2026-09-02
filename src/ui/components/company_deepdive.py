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

    # Use first company as default (you could make this dynamic with a real selector)
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
            <h3 style="margin: 0; margin-top: -1rem; font-size: 1.5rem; font-weight: 600; color: #1f2937; line-height: 1.2;">
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
                <span style="font-size: 0.875rem; color: #6b7280; font-weight: 500;">Segment :</span>
                <span style="font-size: 0.875rem; color: #1f2937; font-weight: 600; margin-left: 0.5rem;">{company.get("ai_factory_segment", "N/A")}</span>
            </div>
            <div style="margin-bottom: 0.5rem;">
                <span style="font-size: 0.875rem; color: #6b7280; font-weight: 500;">TAFGS :</span>
                <span style="font-size: 0.875rem; color: #1f2937; font-weight: 600; margin-left: 0.5rem;">{company.get("tafgs_score", 0):.2f}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")  # Spacer

        # Growth Forecast section
        st.markdown(
            """
            <div style="margin-bottom: 0.75rem;">
                <span style="font-size: 0.9rem; color: #1f2937; font-weight: 600;">Growth Forecast</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div style="padding: 1rem; background: #f9fafb; border-radius: 8px; border-left: 3px solid #10b981; margin-bottom: 1rem;">
                <p style="margin: 0; font-size: 0.875rem; color: #374151; line-height: 1.6;">
                    {company.get("growth_narrative", "No growth forecast available.")}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Risk Factors section
        st.markdown(
            """
            <div style="margin-bottom: 0.75rem;">
                <span style="font-size: 0.9rem; color: #1f2937; font-weight: 600;">Risk Factors</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div style="padding: 1rem; background: #f9fafb; border-radius: 8px; border-left: 3px solid #ef4444; margin-bottom: 1rem;">
                <p style="margin: 0; font-size: 0.875rem; color: #374151; line-height: 1.6;">
                    {company.get("risk_notes", "No risk factors identified.")}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
