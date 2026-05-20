# Growth Intelligence Agent

An AI agent that acts as a virtual revenue analyst — monitoring SaaS growth metrics, detecting anomalies, identifying root causes, and recommending actions. Built as a portfolio project demonstrating production-grade AI agent design.

**Live demo:** [growth-intelligence-agent.vercel.app](https://growth-intelligence-agent.vercel.app)  
**Article:** [growth-intelligence-agent.vercel.app](https://growth-intelligence-agent.vercel.app) (root)  
**Dashboard:** [growth-intelligence-agent.vercel.app/dashboard](https://growth-intelligence-agent.vercel.app/dashboard)

---

## What it does

Ask it natural-language questions about a SaaS company's metrics:

> *"What's driving our EMEA win rate decline?"*

The agent pulls metrics from the warehouse, fetches CRM pipeline data, retrieves product usage signals, looks up your growth strategy from a RAG knowledge base, and synthesises a structured answer with root cause analysis and recommended actions.

---

## Architecture

```
Browser / REST client
        │
        ▼
FastAPI backend  (api/main.py · Vercel serverless)
        │
        ▼
LangGraph ReAct agent  (agent/agent.py · Claude or GPT-4)
        │
   ┌────┼──────────────────────────────────────┐
   ▼    ▼                ▼              ▼       ▼
get_   get_pipeline_  get_product_  get_deals_  get_company_
metric  by_segment     usage         by_stage    context (RAG)
   │         │              │             │           │
metrics.csv  opps+accts  usage.csv    opps.csv   FAISS index
                                                (rag/docs/)
```

---

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| LLM | Claude (Haiku/Sonnet) or GPT-4o | Tool-use reliability |
| Agent | LangGraph `create_react_agent` | ReAct loop, streaming-ready |
| Tools | LangChain `@tool` (MCP-pattern) | Clear docstrings drive tool selection |
| Vector DB | FAISS (local) | No server needed for 18-chunk knowledge base |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` | Free, fast, good English quality |
| Data | CSV + Pandas | Simulates a data warehouse without overhead |
| API | FastAPI + Vercel | Serverless, zero-ops deployment |
| UI (local) | Streamlit | Rapid prototyping |
| UI (deployed) | Vanilla HTML/JS + Chart.js | No React needed; embedded in FastAPI |

---

## Quickstart

```bash
git clone https://github.com/ShrikantLambe/growth_intelligence_agent
cd growth_intelligence_agent

pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY or OPENAI_API_KEY

# One-time setup (in order)
python scripts/generate_data.py
python metrics/compute_metrics.py
python rag/build_vectorstore.py

# Local dashboard
streamlit run ui/app.py

# Local API
uvicorn api.main:app --reload --port 8000
```

---

## Project structure

```
├── agent/
│   ├── agent.py              # LangGraph ReAct agent, ask() and generate_full_analysis()
│   ├── alerts.py             # Anomaly detection (prior-period comparison, severity tiers)
│   └── prompts.py            # SYSTEM_PROMPT and INSIGHT_GENERATION_PROMPT
├── api/
│   ├── main.py               # FastAPI routes + embedded HTML dashboard (~1 200 lines)
│   └── requirements.txt      # Vercel-only deps (excludes PyTorch/Streamlit)
├── data/
│   ├── raw/                  # Committed CSVs (300 accounts, 800 deals, …)
│   └── processed/            # metrics.csv (recomputed from raw)
├── metrics/
│   └── compute_metrics.py    # dbt-style metric models → metrics.csv
├── rag/
│   ├── docs/                 # 3 markdown playbooks (ICP, growth strategy, pricing)
│   ├── build_vectorstore.py  # Chunks, embeds, and saves FAISS index
│   └── vectorstore/          # Committed FAISS index (index.faiss + index.pkl)
├── scripts/
│   └── generate_data.py      # Synthetic SaaS data generator (seed=42)
├── tools/
│   └── mcp_tools.py          # 5 LangChain tools used by the agent
├── ui/
│   └── app.py                # Streamlit dashboard (local only)
├── index.html                # Portfolio article (served at /)
├── pyproject.toml            # Vercel build config (uv, Python 3.12)
├── requirements.txt          # Full local dev deps
├── runtime.txt               # Python 3.12 pin
└── vercel.json               # Vercel env vars
```

---

## Dashboard features (deployed)

- **Filter bar** — slice all KPIs by Region, Tier, Industry, and Quarter
- **KPI cards** — 8 metrics with QoQ delta; click any card for a drill-down modal
- **Drill-downs** — 3-section breakdown per KPI (trend chart + segment chart + data table)
- **Performance vs Target** — normalised % of target for all KPIs at a glance
- **AI Chat** — tool-call traces visible per response; "Ask agent" CTA on every chart
- **Alerts** — auto-scans on load; one-click "Investigate with agent" per anomaly
- **Pipeline tab** — by region, stage, and industry with filter state applied

---

## Deployment

The project deploys to Vercel with a single command:

```bash
vercel --prod
```

Key constraints:
- `sentence-transformers` / `faiss-cpu` are excluded from `pyproject.toml` — PyTorch (~2 GB) exceeds the 500 MB Lambda limit. The RAG tool degrades gracefully.
- Data files and vectorstore are committed to git so Vercel has them at runtime.
- `maxDuration: 300` requires Vercel Pro; Hobby plan caps at 60s (fine for most queries).
