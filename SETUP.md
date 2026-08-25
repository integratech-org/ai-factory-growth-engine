# Setup Guide — AI Factory Growth Engine (`ai-factory-growth-engine`)

Follow these instructions to set up, configure, and run `ai-factory-growth-engine` locally.

## Prerequisites

- **Python**: Version 3.14 or higher
- **Package Manager**: `uv`
- **Database**: PostgreSQL (running locally or via Docker Compose)
- **API Keys**: Google Gemini or Groq (LLM), Tavily (search), SEC EDGAR identity string
- **Make**: (optional) For running Makefile shortcuts

## Installation & Configuration

1. Navigate to the project directory:
   ```bash
   cd ai-factory-growth-engine
   ```

2. Run the development environment setup. This checks system requirements and configures pre-commit hooks:
   ```bash
   make setup
   # or run the script directly:
   ./scripts/setup.sh
   ```

3. Copy the environment configuration template:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` with your LLM provider keys (Google Gemini / Groq), Tavily API key, SEC EDGAR identity strings, and `DATABASE_URL` pointing to your PostgreSQL instance.*

4. Install python dependencies using `uv`:
   ```bash
   uv sync
   ```

## Database Checkpointer Setup

Pipeline state is persisted with the Postgres checkpointer (`AsyncPostgresSaver`). The checkpoint tables are created automatically on first run — just make sure `DATABASE_URL` points to a reachable database.

## Running the Pipeline

Start the LangGraph development server (graph defined in `langgraph.json`):

```bash
uv run langgraph dev
```

The LangGraph API will be available at `http://localhost:2024`.

Alternatively, launch the Streamlit web interface:

```bash
uv run streamlit run streamlit_app.py
```

The app will be available at `http://localhost:8501`.

## Code Quality, Linting & Pre-commit

- **Pre-commit Hooks Management (via Makefile):**
  - Install pre-commit hooks:
    ```bash
    make pre-commit-install
    ```
  - Run pre-commit checks on all files:
    ```bash
    make pre-commit-all
    ```
  - Update pre-commit hooks to their latest versions:
    ```bash
    make pre-commit-update
    ```

- **Manual Code Quality Checks:**
  - **Linting (Ruff):**
    ```bash
    uv run ruff check .
    ```
  - **Type Checking (Mypy):**
    ```bash
    uv run mypy src/
    ```
