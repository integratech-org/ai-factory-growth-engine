"""
Strategic Factor Weights panel component.

Allows users to adjust weights for Moat, Margin, Growth, and Risk factors.
"""

import streamlit as st


def render_weights_panel() -> dict[str, float]:
    """
    Render the Strategic Factor Weights panel with sliders.

    Returns:
        dict with factor weights: {"moat": float, "margin": float, "growth": float, "risk": float}
    """

    # Initialize weights in session state
    if "weights" not in st.session_state:
        st.session_state.weights = {
            "moat": 1.0,
            "margin": 1.0,
            "growth": 1.0,
            "risk": 1.0,
        }

    # Use a container with border - matching segment panel style
    with st.container(border=True):
        # Header with icon and Reset button
        col_title, col_reset = st.columns([3, 1])
        with col_title:
            st.markdown(
                """
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="12" y1="3" x2="12" y2="21"></line>
                        <polyline points="8 8 12 4 16 8"></polyline>
                        <polyline points="16 16 12 20 8 16"></polyline>
                        <line x1="3" y1="12" x2="21" y2="12"></line>
                    </svg>
                    <span style="font-weight: 600; font-size: 1rem;">Strategic Factor Weights</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_reset:
            # Use markdown button with SVG icon instead of emoji
            st.markdown(
                """
                <style>
                div[data-testid="column"]:has(button[key="reset_weights_btn"]) button {
                    display: flex;
                    align-items: center;
                    gap: 0.25rem;
                    justify-content: center;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "↻ Reset to Default", key="reset_weights_btn", width="stretch"
            ):
                st.session_state.weights = {
                    "moat": 1.0,
                    "margin": 1.0,
                    "growth": 1.0,
                    "risk": 1.0,
                }
                st.rerun()

        st.write("")  # Spacer

        # Two columns for the sliders - now single column for more height
        # Moat slider
        moat_val = st.slider(
            "Moat",
            min_value=0.0,
            max_value=5.0,
            value=st.session_state.weights["moat"],
            step=0.1,
            format="%.1f",
            key="moat_slider",
        )
        st.session_state.weights["moat"] = moat_val

        # Margin slider
        margin_val = st.slider(
            "Margin",
            min_value=0.0,
            max_value=5.0,
            value=st.session_state.weights["margin"],
            step=0.1,
            format="%.1f",
            key="margin_slider",
        )
        st.session_state.weights["margin"] = margin_val

        # Growth slider
        growth_val = st.slider(
            "Growth",
            min_value=0.0,
            max_value=5.0,
            value=st.session_state.weights["growth"],
            step=0.1,
            format="%.1f",
            key="growth_slider",
        )
        st.session_state.weights["growth"] = growth_val

        # Risk slider
        risk_val = st.slider(
            "Risk",
            min_value=0.0,
            max_value=5.0,
            value=st.session_state.weights["risk"],
            step=0.1,
            format="%.1f",
            key="risk_slider",
        )
        st.session_state.weights["risk"] = risk_val

    # Info box OUTSIDE the container - blue for info
    st.markdown(
        """
        <div style="padding: 0.75rem 1rem; background: #dbeafe; border-left: 3px solid #3b82f6; border-radius: 4px; margin-top: 1rem;">
            <p style="margin: 0; font-size: 0.8rem; color: #1e40af; line-height: 1.5;">
                <strong>Weight Impact:</strong> Higher values increase the importance of that factor in the final TAFGS ranking score.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return st.session_state.weights
