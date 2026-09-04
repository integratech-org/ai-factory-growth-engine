"""
Results table component for Top 20 AI Factory Growth Ranking.

Displays ranked companies with key metrics in a paginated table.
"""

import streamlit as st


def render_results_table(results: list[dict] | None = None) -> None:
    """
    Render the Top 20 AI Factory Growth Ranking table.

    Args:
        results: List of company result dicts with rank, ticker, scores, etc.
                 None displays placeholder state.
    """

    # Container with border
    with st.container(border=True):
        # Header with trophy icon - centered alignment with tight text spacing
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; margin-left: 0.25rem; margin-top: -0.25rem;">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0;">
                    <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path>
                    <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path>
                    <path d="M4 22h16"></path>
                    <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"></path>
                    <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"></path>
                    <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"></path>
                </svg>
                <div style="flex: 1; padding: 0.1rem 0;">
                    <div style="margin: 0; font-size: 1.25rem; font-weight: 600; color: #1f2937; line-height: 1.4;">Top 20 AI Factory Growth Ranking</div>
                    <div style="margin: 0; margin-top: 0.1rem; font-size: 0.875rem; color: #6b7280; line-height: 1.4;">Companies ranked by Total AI Factory Growth Score (TAFGS).</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Show results or fallback message
        if results and len(results) > 0:
            # Display results table using st.dataframe with custom styling
            import pandas as pd

            # Prepare dataframe
            df = pd.DataFrame(
                [
                    {
                        "Rank": r.get("rank", "—"),
                        "Ticker": r.get("ticker", "—"),
                        "Name": r.get("company_name", "—"),
                        "Segment": r.get("ai_factory_segment", "—"),
                        "Moat": f"{r.get('moat_score', 0):.1f}"
                        if r.get("moat_score")
                        else "—",
                        "Margin": f"{r.get('margin_score', 0):.1f}%"
                        if r.get("margin_score")
                        else "—",
                        "CAGR (3Y)": f"{r.get('growth_cagr_3yr', 0) * 100:.1f}%"
                        if r.get("growth_cagr_3yr")
                        else "—",
                        "TAFGS": f"{r.get('tafgs_score', 0):.2f}"
                        if r.get("tafgs_score")
                        else "—",
                    }
                    for r in results[:20]  # Top 20 only
                ]
            )

            # Custom CSS for table styling with green header - adapts to light/dark mode
            st.markdown(
                """
                <style>
                /* Table header styling - teal background, always white text for contrast */
                div[data-testid="stDataFrame"] thead tr th {
                    background-color: #10b981 !important;
                    color: #ffffff !important;
                    font-weight: 600 !important;
                    font-size: 0.875rem !important;
                    padding: 12px 16px !important;
                    border-bottom: 2px solid #059669 !important;
                }

                /* Rank column - bold teal */
                div[data-testid="stDataFrame"] tbody tr td:first-child {
                    font-weight: 600 !important;
                    color: #10b981 !important;
                }

                /* Ticker column - colored and bold */
                div[data-testid="stDataFrame"] tbody tr td:nth-child(2) {
                    color: #3b82f6 !important;
                    font-weight: 600 !important;
                }

                /* Segment badges */
                div[data-testid="stDataFrame"] tbody tr td:nth-child(4) {
                    font-weight: 500 !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            # Display dataframe
            st.dataframe(
                df,
                width="stretch",
                hide_index=True,
                height=400,
            )

            # Pagination info
            st.markdown(
                f'<p style="text-align: right; color: #6b7280; font-size: 0.875rem; margin-top: 0.5rem;">Showing 1 to {min(len(results), 20)} of {len(results)}</p>',
                unsafe_allow_html=True,
            )

        elif results is not None and len(results) == 0:
            # API limit or error fallback
            st.warning(
                """
                **API Rate Limit Reached**

                The analysis could not be completed due to API rate limits. Please try again later or:
                - Reduce the number of tickers
                - Wait a few minutes before retrying
                - Check your API key quotas
                """
            )

        else:
            # Default placeholder - no results yet
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
