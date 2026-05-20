# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & Commands

```bash
# Install all dependencies (local development — UI + data generation + API)
pip install -r requirements.txt

# One-time setup (must run in order)
python scripts/generate_data.py      # → data/raw/*.csv  (seed=42, deterministic)
python metrics/compute_metrics.py    # → data/processed/metrics.csv
python rag/build_vectorstore.py      # → rag/vectorstore/ (FAISS + HuggingFace embeddings)

# Run the Streamlit dashboard locally
streamlit run ui/app.py

# Run the FastAPI backend locally
uvicorn api.main:app --reload --port 8000

# Run the agent interactively in the terminal
python agent/agent.py

# Deploy to Vercel (requires `npm install -g vercel` and login)
vercel --prod
```

## Environment

Copy `.env.example` to `.env` and set one LLM key:
- `ANTHROPIC_API_KEY` — uses the model in `LLM_MODEL` (defaults to `claude-haiku-4-5-20251001`)
- `OPENAI_API_KEY` — falls back to `gpt-4o` if Anthropic key is absent
- `FRONTEND_URL` — (optional) production CORS origin for the FastAPI backend

## Architecture

### Data flow (must run in order)
1. `scripts/generate_data.py` → `data/raw/*.csv` — 300 accounts, 800 deals, 2 000 leads, 300 subscriptions, 5 product-usage entries per account, 8-quarter metrics history. Deterministic with `seed=42`.
2. `metrics/compute_metrics.py` → `data/processed/metrics.csv` — dbt-style transforms: win rate (overall + by region via accounts join), pipeline coverage ($7M quota), NRR (30% expansion uplift, 2.5% churn), attach rate, seat expansion, at-risk rate.
3. `rag/build_vectorstore.py` → `rag/vectorstore/` — FAISS index from `rag/docs/*.md` (3 playbooks: ICP, growth strategy, pricing) using HuggingFace `all-MiniLM-L6-v2`. 18 chunks at 800-char / 100-overlap.

All three outputs are **committed to git** so Vercel has data at runtime without running setup scripts.

### Agent layer (`agent/`)
- `agent.py` — Singleton graph built with `create_react_agent` (LangGraph prebuilt ReAct). Entry points: `ask(question, chat_history)` for chat and `generate_full_analysis()` for a full report. LLM selected at runtime via `get_llm()`.
- `prompts.py` — `SYSTEM_PROMPT` and `INSIGHT_GENERATION_PROMPT`.
- `alerts.py` — Anomaly detection: compares current `metrics.csv` against a noise-simulated prior period. Severity: unfavorable Δ ≥25% = High, ≥15% = Medium.

### Tools (`tools/mcp_tools.py`)
Five LangChain `@tool`-decorated functions registered in `ALL_TOOLS`:
- `get_metric` — keyword-maps plain English to `metrics.csv` rows (9 KPIs, regional segments)
- `get_pipeline_by_segment` — segments 800 deals by region/industry/stage (NA is ~56% of pipeline)
- `get_product_usage` — usage analytics with at-risk detection (51/300 accounts at-risk = 17%)
- `get_deals_by_stage` — CRM deals filtered by closing-this-month, high-value, or stalled
- `get_company_context` — RAG retrieval over `rag/docs/` playbooks (degrades gracefully on Vercel where `faiss-cpu` / `sentence-transformers` are not installed)

### RAG (`rag/`)
Three markdown playbooks chunked and stored as a FAISS index. `retrieve_context(query)` returns top-4 chunks. The `get_company_context` tool catches all RAG exceptions and returns an error string rather than crashing.

### REST API (`api/main.py`)
FastAPI backend deployed to Vercel as a single serverless function. Key endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /` | Serves `index.html` (portfolio article) |
| `GET /dashboard` | Serves the live HTML analytics dashboard |
| `GET /architecture` | System architecture page |
| `GET /api/health` | Health check |
| `GET /api/metrics` | Current KPI values from `metrics.csv` |
| `GET /api/metrics-history` | 8-quarter historical KPIs for delta cards |
| `GET /api/kpis` | Filtered KPI recomputation (`regions`, `industries`, `tiers`, `period` params) |
| `GET /api/pipeline` | Pipeline segmented by region/industry/stage (accepts filter params) |
| `GET /api/usage` | Product usage analytics |
| `GET /api/alerts` | Anomaly detection results |
| `GET /api/drill/{kpi}` | Drill-down data for 8 KPI slugs: `win-rate`, `pipeline-coverage`, `nrr`, `deal-size`, `product-attach`, `seat-expansion`, `at-risk`, `sales-cycle` |
| `POST /api/ask` | Chat with the agent (returns `{answer, steps}`) |
| `POST /api/analyze` | Full growth analysis (calls LLM directly) |

### HTML dashboard (`/dashboard`)
The dashboard HTML is embedded as `_DASHBOARD_HTML` in `api/main.py` (~700 lines). Key features:
- **Filter bar** — Region pills, Tier pills, Industry dropdown, Period dropdown. Calls `/api/kpis` with filter params; re-renders all charts on change.
- **KPI cards** — 8 cards with QoQ delta vs Q4 2025. Click any card → drill-down modal.
- **Drill-down modal** — 3 sections per KPI (stats / chart / table). Generic renderer; data from `/api/drill/{kpi}`. "Ask agent" CTA pre-wired per KPI.
- **Trends & Targets section** — Win Rate by Region (bar) + Performance vs Target (horizontal bar).
- **Tabs**: AI Chat | Pipeline | Alerts.
- **Chat** — Tool-call traces collapsible per response. "Ask agent" CTAs on every chart.
- **Alerts** — Auto-scans on load. "Investigate with agent" CTA per anomaly.
- **Chart registry** (`_chartReg`) — Prevents "canvas already in use" errors on filter-change re-renders.

### Streamlit UI (`ui/app.py`)
Local-only dashboard — runs on `localhost:8501`. Same data as the API. Adds a sidebar with global filters that recompute KPIs live. Not deployed to Vercel (Streamlit is not serverless-compatible and `plotly` + `streamlit` would blow the 500 MB Lambda limit).

## Dependency Layout

| File | Purpose |
|------|---------|
| `requirements.txt` | Full local dev: UI + data generation + API + RAG |
| `api/requirements.txt` | API-only (no Streamlit, Plotly, Faker) — used for reference |
| `pyproject.toml` | **Vercel build file** — intentionally excludes `sentence-transformers` / `faiss-cpu` (PyTorch = ~2 GB, breaks Lambda) |

## Key Constraints

- All tools call `_load(filename)` which raises `FileNotFoundError` with a clear message if raw data is missing — always run `generate_data.py` first.
- `get_company_context` catches all RAG exceptions gracefully — the agent works without RAG (just less context-grounded).
- The agent is a module-level singleton (`_agent_instance`) — built once and reused across calls in the same process.
- Account IDs follow `ACC\d+` (ACC0001–ACC0300). `get_product_usage` parses this from natural language.
- `api/main.py` inserts the repo root into `sys.path` at import time so `agent/`, `tools/`, and `rag/` resolve correctly in the Vercel Lambda.
- The `/api/kpis` filter endpoint applies period filters only to closed-deal metrics (Win Rate, Avg Deal Size, Sales Cycle). Pipeline Coverage, NRR, Attach, Expansion, and At-Risk always reflect the current snapshot filtered by account attributes only.
