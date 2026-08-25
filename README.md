# AI Factory Growth Engine (`ai-factory-growth-engine`)

An autonomous equity-research pipeline that identifies and ranks public companies by their exposure to global AI Factory infrastructure build-outs.

The engine maps the AI Factory value chain (compute, networking, power, cooling, construction), ingests eligible companies, scores each across moat, margin, growth, and risk dimensions, and produces an investor-ready Top 20 ranking based on the Total AI Factory Growth Score (TAFGS).

## Features

- **Multi-Agent Pipeline:** Eight specialized LangGraph agents run sequentially — market mapping, company ingestion, moat analysis, margin analysis, growth forecasting, risk adjustment, ranking, and reporting.
- **TAFGS Scoring & Ranking:** Computes the Total AI Factory Growth Score per company and produces the ordered Top 20 output.
- **Real-World Data Tools:** Tavily web search, Yahoo Finance market data (`yfinance`), and SEC EDGAR filings (`edgartools`).
- **Dual Interfaces:** Streamlit web app for interactive runs plus a LangGraph API server exposing the graph.
- **Durable Runs:** PostgreSQL-backed checkpointing enables resumable, long-running pipeline executions.

## Tech Stack

- **Language:** Python >= 3.14
- **Agent Orchestration:** LangGraph with LangGraph Server (`langgraph-cli`)
- **LLM Providers:** Google Gemini & Groq via LangChain integrations
- **UI:** Streamlit
- **Persistence:** PostgreSQL checkpointer (`langgraph-checkpoint-postgres`)
- **Dependency Management:** `uv`
- **Linting & Quality:** Ruff, Mypy, pre-commit hooks

## Project Structure

```text
ai-factory-growth-engine/
├── scripts/            # Utility & setup scripts
├── src/
│   ├── agents/         # One agent node per pipeline stage
│   ├── graph/          # Shared state schema & workflow wiring
│   └── tools/          # Tool wrappers (Tavily, yfinance, SEC EDGAR)
├── langgraph.json      # LangGraph graph & server configuration
├── streamlit_app.py    # Streamlit web interface
├── main.py             # CLI entry point
├── pyproject.toml
└── uv.lock
```
