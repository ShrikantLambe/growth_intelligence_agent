# 🧠 AI Growth Intelligence Agent

A portfolio project demonstrating how an AI agent acts as a virtual revenue analyst for a SaaS company — monitoring growth metrics, detecting anomalies, identifying root causes, and recommending actions.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Streamlit UI                         │
│         (Dashboard · Chat · Alerts · Insights)           │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Growth Intelligence Agent                    │
│         (LangChain Agent + Claude/OpenAI LLM)            │
└──────┬────────────────┬──────────────────┬──────────────┘
       │                │                  │
┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼──────┐
│  MCP Tools  │  │  RAG System │  │  Metrics DB  │
│  (4 tools)  │  │ (FAISS/Chroma│  │ (SQLite/CSV) │
└─────────────┘  └─────────────┘  └──────────────┘
       │                │                  │
┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼──────┐
│ CRM/Usage   │  │  Company    │  │  dbt-style   │
│   Data      │  │  Playbooks  │  │  SQL Metrics │
└─────────────┘  └─────────────┘  └──────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Claude (claude-3-5-sonnet) or OpenAI GPT-4 |
| Agent framework | LangChain |
| Vector DB | FAISS (local) or Chroma |
| Data | SQLite + CSV (simulated SaaS data) |
| UI | Streamlit |
| Metrics | dbt-style SQL models via Pandas |

## Project Structure

```
growth-intelligence-agent/
├── data/
│   ├── raw/                  # Simulated SaaS CSVs
│   └── processed/            # Cleaned & joined data
├── metrics/
│   ├── sql_models.py         # dbt-style metric SQL
│   └── compute_metrics.py    # Metric computation engine
├── rag/
│   ├── docs/                 # Company context markdown docs
│   ├── build_vectorstore.py  # Embed & store docs
│   └── retriever.py          # RAG retrieval logic
├── agent/
│   ├── agent.py              # Core LangChain agent
│   ├── prompts.py            # All agent prompts
│   └── alerts.py             # Anomaly detection & alerting
├── tools/
│   └── mcp_tools.py          # MCP-compatible tool definitions
├── ui/
│   └── app.py                # Streamlit dashboard
├── scripts/
│   └── generate_data.py      # Dataset generation script
├── .env.example
├── requirements.txt
└── README.md
```

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY or OPENAI_API_KEY

# 3. Generate simulated SaaS data
python scripts/generate_data.py

# 4. Build RAG knowledge base
python rag/build_vectorstore.py

# 5. Launch the Streamlit app
streamlit run ui/app.py
```

## Development Phases

| Phase | Description | Files |
|-------|-------------|-------|
| 1 | Data generation | `scripts/generate_data.py` |
| 2 | Metrics layer | `metrics/` |
| 3 | RAG knowledge base | `rag/` |
| 4 | MCP tools | `tools/mcp_tools.py` |
| 5 | Agent core | `agent/` |
| 6 | Streamlit UI | `ui/app.py` |

## 🌐 Live Article
[Read the full project write-up →](https://shrikantlambe.github.io/growth_intelligence_agent/)
