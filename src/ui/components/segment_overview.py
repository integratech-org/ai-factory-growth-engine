"""
Segment Overview component.

Displays AI Factory infrastructure segments that will be analyzed.
Shows the automated company discovery approach.
"""

import streamlit as st


def render_segment_overview() -> None:
    """Render the AI Factory Segments overview panel."""

    with st.container(border=True):
        # Header with icon - match the weights panel structure
        col_title, col_spacer = st.columns([3, 1])
        with col_title:
            st.markdown(
                """
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="3" width="7" height="7"></rect>
                        <rect x="14" y="3" width="7" height="7"></rect>
                        <rect x="14" y="14" width="7" height="7"></rect>
                        <rect x="3" y="14" width="7" height="7"></rect>
                    </svg>
                    <span style="font-weight: 600; font-size: 1rem;">AI Factory Segments</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_spacer:
            # Empty column to match the Reset button column on the right
            st.write("")

        st.write("")  # Spacer

        # Segments list - vertical/stacked layout
        segments = [
            {"name": "Compute", "weight": "58%", "description": "GPUs, AI servers"},
            {
                "name": "Power",
                "weight": "16%",
                "description": "Generators, turbines, UPS",
            },
            {
                "name": "Cooling",
                "weight": "10%",
                "description": "Liquid cooling, HVAC systems",
            },
            {
                "name": "Networking",
                "weight": "9%",
                "description": "Switches, optical transceivers",
            },
            {
                "name": "Construction",
                "weight": "7%",
                "description": "Modular data centers, infrastructure",
            },
        ]

        for segment in segments:
            st.markdown(
                f"""
                <div style="margin-bottom: 1.3rem; padding: 0.3rem 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                        <span style="font-size: 0.875rem; font-weight: 600;">{segment["name"]}</span>
                        <span style="font-size: 0.875rem; font-weight: 700; color: #10b981;">{segment["weight"]}</span>
                    </div>
                    <div style="font-size: 0.75rem; opacity: 0.7; line-height: 1.4;">{segment["description"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Info box OUTSIDE the container - blue for info
    st.markdown(
        """
        <div style="padding: 0.75rem 1rem; background: #dbeafe; border-left: 3px solid #3b82f6; border-radius: 4px; margin-top: 1rem;">
            <p style="margin: 0; font-size: 0.8rem; color: #1e40af; line-height: 1.5;">
                <strong>Auto-Discovery:</strong> The Company Ingestion agent automatically discovers relevant companies across all segments.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
