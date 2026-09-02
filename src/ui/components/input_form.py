"""
Input form component for ticker entry.

Allows users to add/remove ticker symbols for analysis.
"""

import streamlit as st


def render_input_tickers() -> None:
    """Render the Input Tickers section with tag-style ticker display."""

    # Use a container
    with st.container(border=True):
        # Header with icon
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
                <span style="font-weight: 600; font-size: 1rem; color: #1f2937;">Input Tickers</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Input field with Enter key support using form
        with st.form(key="add_ticker_form", clear_on_submit=True):
            col_input, col_btn = st.columns([4, 1])
            with col_input:
                new_ticker = st.text_input(
                    "Add ticker",
                    placeholder="e.g., NVDA",
                    label_visibility="collapsed",
                    key="new_ticker_input_form",
                )
            with col_btn:
                submitted = st.form_submit_button("Add", width="stretch")

            if submitted and new_ticker and new_ticker.strip():
                ticker_upper = new_ticker.strip().upper()
                if ticker_upper not in st.session_state.companies:
                    st.session_state.companies.append(ticker_upper)
                    st.rerun()

        st.write("")  # Small spacer

        # Display tickers using st.pills for clean tag-style display
        if st.session_state.companies:
            # Create options with × symbol
            options = [f"{ticker} ×" for ticker in st.session_state.companies]

            # Use pills component - returns the selected option
            selected = st.pills(
                "Tickers",
                options=options,
                label_visibility="collapsed",
                selection_mode="single",
            )

            # If a pill was clicked, remove that ticker
            if selected:
                # Extract ticker name (remove " ×" suffix)
                ticker_to_remove = selected.replace(" ×", "")
                if ticker_to_remove in st.session_state.companies:
                    st.session_state.companies.remove(ticker_to_remove)
                    st.rerun()

        st.write("")  # Spacer before footer

        # Footer
        col1, col_spacer, col2 = st.columns([2, 6, 2])
        with col1:
            st.markdown(
                f'<span style="color: #10b981; font-weight: 500; font-size: 0.875rem;">{len(st.session_state.companies)} tickers added</span>',
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("Clear All", key="clear_all_tickers", width="stretch"):
                st.session_state.companies = []
                st.rerun()
