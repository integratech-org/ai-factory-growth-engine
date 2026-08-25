"""
Gemini LLM wrapper (free tier).
Used by: Moat Analysis, Margin Analysis, Growth Forecast, Risk Adjustment, Report agents.
"""

from __future__ import annotations

import asyncio
import json
import os

from google import genai

# ─────────────────────────────────────────────────────────────────────────────
# Client init
#
# Reads API key/model from env (loaded via python-dotenv at the entry point).
# Single client instance, reused across all calls within a process.
# ─────────────────────────────────────────────────────────────────────────────
_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

DEFAULT_MODEL = os.getenv("GOOGLE_MODEL_NAME") or "gemini-2.5-flash"


async def generate_json(prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """
    Calls Gemini with a prompt and parses the response as JSON.

    The genai SDK is sync, so the call is wrapped in asyncio.to_thread()
    to avoid blocking the event loop (same pattern as edgartools/yfinance
    calls elsewhere in this project).

    Raises on failure (bad JSON, API error) — callers are expected to
    catch and write to CompanyState.error rather than crash the pipeline.
    """

    def _call() -> str:
        response = _client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        return response.text

    raw = await asyncio.to_thread(_call)
    return json.loads(raw)