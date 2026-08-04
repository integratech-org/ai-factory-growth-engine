"""AI Factory Growth Engine — multi-agent graph wiring."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.company_ingestion import company_ingestion_node
from agents.growth_forecast import growth_forecast_node
from agents.margin_analysis import margin_analysis_node
from agents.market_mapping import market_mapping_node
from agents.moat_analysis import moat_analysis_node
from agents.ranking import ranking_node
from agents.report import report_node
from agents.risk_adjustment import risk_adjustment_node
from graph.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)

    # ── Register all nodes ────────────────────────────────────────────
    builder.add_node("market_mapping", market_mapping_node)
    builder.add_node("company_ingestion", company_ingestion_node)
    builder.add_node("moat_analysis", moat_analysis_node)
    builder.add_node("margin_analysis", margin_analysis_node)
    builder.add_node("growth_forecast", growth_forecast_node)
    builder.add_node("risk_adjustment", risk_adjustment_node)
    builder.add_node("ranking", ranking_node)
    builder.add_node("report", report_node)

    # ── Define edges between nodes ────────────────────────────────────
    builder.add_edge(START, "market_mapping")
    builder.add_edge("market_mapping", "company_ingestion")
    builder.add_edge("company_ingestion", "moat_analysis")
    builder.add_edge("moat_analysis", "margin_analysis")
    builder.add_edge("margin_analysis", "growth_forecast")
    builder.add_edge("growth_forecast", "risk_adjustment")
    builder.add_edge("risk_adjustment", "ranking")
    builder.add_edge("ranking", "report")
    builder.add_edge("report", END)

    return builder.compile(name="AI Factory Growth Engine")


graph = build_graph()
