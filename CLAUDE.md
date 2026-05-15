# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & Commands

```bash
# Install dependencies
pip install -r requirements.txt

# One-time setup (must be run in order before launching the UI)
python scripts/generate_data.py      # generates data/raw/*.csv
python metrics/compute_metrics.py    # produces data/processed/metrics.csv
python rag/build_vectorstore.py      # builds rag/vectorstore/ FAISS index

# Launch the Streamlit UI
streamlit run ui/app.py

# Run the FastAPI backend (for Next.js / Vercel frontend)
uvicorn api.main:app --reload --port 8000

# Run the agent interactively in the terminal
python agent/agent.py

# Run anomaly detection standalone
python agent/alerts.py
```

## Environment

Copy `.env.example` to `.env` and set one LLM key:
- `ANTHROPIC_API_KEY` — uses the model specified by `LLM_MODEL` (defaults to `claude-haiku-4-5-20251001`)
- `OPENAI_API_KEY` — falls back to `gpt-4o` if Anthropic key is absent

`VECTOR_STORE` can be `faiss` (default, local) or `chroma`.

`FRONTEND_URL` sets the allowed CORS origin for the FastAPI backend in production.

## Architecture

**Data flow (must run in order):**
1. `scripts/generate_data.py` → `data/raw/*.csv` (simulated SaaS accounts, opportunities, usage, leads, subscriptions)
2. `metrics/compute_metrics.py` → `data/processed/metrics.csv` (dbt-style Pandas transforms)
3. `rag/build_vectorstore.py` → `rag/vectorstore/` (FAISS index from `rag/docs/*.md` using HuggingFace `all-MiniLM-L6-v2`)
4. Agent and UI depend on all three outputs being present

**Agent layer (`agent/`):**
- `agent.py` — Singleton graph built with `create_react_agent` (LangGraph prebuilt ReAct). Entry points: `ask(question, chat_history)` for chat and `generate_full_analysis()` for a full report. The LLM is selected at runtime via `get_llm()` using env vars.
- `prompts.py` — All system and insight generation prompts.
- `alerts.py` — Anomaly detection by comparing current `metrics.csv` against a noise-simulated previous period. Severity logic: unfavorable changes ≥25% = High, ≥15% = Medium.

**Tools (`tools/mcp_tools.py`):**
Five LangChain `@tool`-decorated functions registered in `ALL_TOOLS`:
- `get_metric` — keyword-maps plain English queries to `metrics.csv` rows
- `get_pipeline_by_segment` — segments opportunity pipeline by region/industry/stage
- `get_product_usage` — usage analytics with at-risk detection (inactive >30 days)
- `get_deals_by_stage` — CRM deals filtered by closing-this-month, high-value, or stalled
- `get_company_context` — RAG retrieval over `rag/docs/` playbooks

**RAG (`rag/`):**
Three markdown playbooks in `rag/docs/` (ICP, growth strategy, pricing rules) are chunked at 800 chars/100 overlap and stored as a FAISS index. `retrieve_context(query)` returns top-4 chunks as a formatted string; used by `get_company_context` tool.

**REST API (`api/main.py`):**
FastAPI backend designed for a Next.js frontend on Vercel. Endpoints: `GET /api/metrics`, `GET /api/pipeline`, `GET /api/usage`, `GET /api/alerts`, `POST /api/ask`, `POST /api/analyze`. Deployed via `vercel.json` routing all `/api/*` traffic to this single file as a serverless function (max duration 300 s on Vercel Pro). CORS is pre-configured for `localhost:3000`, `*.vercel.app`, and `FRONTEND_URL`.

**UI (`ui/app.py`):**
Streamlit app. Adds project root to `sys.path` so all internal imports work. Uses `st.session_state` for chat history, alerts cache, and deferred analysis runs. Charts built with Plotly Express/Graph Objects.

## Key Constraints

- All tools call `_load(filename)` which raises `FileNotFoundError` with a clear message if raw data is missing — always run `generate_data.py` first.
- `get_company_context` catches all RAG exceptions and degrades gracefully with an error string rather than crashing the agent.
- The agent is a module-level singleton (`_agent_instance`) — it is built once and reused across calls in the same process.
- Account IDs follow the format `ACC\d+` (e.g., `ACC0042`); the `get_product_usage` tool parses this pattern from natural language queries.
- `api/main.py` re-appends the repo root to `sys.path` at import time so tools and agent modules resolve correctly when running as a Vercel serverless function.
