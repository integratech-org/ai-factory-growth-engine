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

# from graph.workflow import build_graph

load_dotenv()

DB_URI = os.getenv("DATABASE_URL")


# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Factory Growth Engine",
    page_icon="📊",
    layout="centered",
)


def init_state():
    defaults = {
        "screen": "INPUT",
        "session_id": None,
        "companies": [],
        "result": None,
        "error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


# ── Graph interaction ─────────────────────────────────────────────
async def run_graph(companies: list, session_id: str):
    assert DB_URI is not None, "DATABASE_URL environment variable is not set"
    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        await checkpointer.setup()
        # app = build_graph(checkpointer=checkpointer)
