"""
Gemini LLM wrapper (free tier).
Used by: Moat Analysis, Margin Analysis, Growth Forecast, Risk Adjustment, Report agents.
"""

from __future__ import annotations

import asyncio
import json
import os

from google import genai

_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

DEFAULT_MODEL = os.getenv("GOOGLE_MODEL_NAME") or "gemini-2.5-flash"


async def generate_json(prompt: str, model: str = DEFAULT_MODEL) -> dict:
    def _call() -> str:
        response = _client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        return response.text

    raw = await asyncio.to_thread(_call)
    return json.loads(raw)