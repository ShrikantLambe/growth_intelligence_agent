"""
FastAPI backend for the Growth Intelligence Agent.
Exposes REST endpoints + serves the HTML dashboard and architecture page.

Local dev:  uvicorn api.main:app --reload --port 8000
Vercel:     entrypoint declared in pyproject.toml; all /api/* routes handled here.
"""

import os
import sys
import logging
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Growth Intelligence Agent API", version="1.0.0")

_frontend_url = os.getenv("FRONTEND_URL", "")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in ["http://localhost:3000", _frontend_url] if o],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    chat_history: Optional[list[tuple[str, str]]] = None
    filter_summary: Optional[str] = None

class AskResponse(BaseModel):
    answer: str
    steps: list[dict]

class AnalyzeResponse(BaseModel):
    analysis: str


# ── HTML pages ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def root():
    html_path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content='<meta http-equiv="refresh" content="0;url=/dashboard"/>')


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(content=_DASHBOARD_HTML)


@app.get("/architecture", response_class=HTMLResponse)
def architecture():
    return HTMLResponse(content=_ARCHITECTURE_HTML)


# ── Health ───────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Metrics ──────────────────────────────────────────────────────────────────────

@app.get("/api/metrics")
def get_metrics(metric_name: Optional[str] = None, segment: Optional[str] = None):
    import pandas as pd
    path = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "metrics.csv")
    if not os.path.exists(path):
        raise HTTPException(status_code=503, detail="Metrics not computed yet. Run metrics/compute_metrics.py first.")
    df = pd.read_csv(path)
    if metric_name:
        df = df[df["metric_name"].str.lower() == metric_name.lower()]
    if segment:
        df = df[df["segment"] == segment]
    return df.to_dict(orient="records")


@app.get("/api/metrics-history")
def get_metrics_history(metric_name: Optional[str] = None, quarter: Optional[str] = None):
    import pandas as pd
    path = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "metrics_history.csv")
    if not os.path.exists(path):
        raise HTTPException(status_code=503, detail="Metrics history not found. Run scripts/generate_data.py first.")
    df = pd.read_csv(path)
    if metric_name:
        df = df[df["metric_name"].str.lower() == metric_name.lower()]
    if quarter:
        df = df[df["quarter"] == quarter]
    return df.to_dict(orient="records")


# ── Pipeline ─────────────────────────────────────────────────────────────────────

@app.get("/api/pipeline")
def get_pipeline(segment: str = "region"):
    try:
        from tools.mcp_tools import get_pipeline_by_segment
        return {"data": get_pipeline_by_segment.invoke(f"by {segment}")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Product usage ────────────────────────────────────────────────────────────────

@app.get("/api/usage")
def get_usage(query: str = "summary"):
    try:
        from tools.mcp_tools import get_product_usage
        return {"data": get_product_usage.invoke(query)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Alerts ───────────────────────────────────────────────────────────────────────

@app.get("/api/alerts")
def get_alerts(threshold_pct: float = 0.20):
    try:
        from agent.alerts import compute_alerts
        alerts = compute_alerts(threshold_pct=threshold_pct)
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Agent chat ───────────────────────────────────────────────────────────────────

@app.post("/api/ask", response_model=AskResponse)
def ask(body: AskRequest):
    try:
        from agent.agent import ask as agent_ask
        question = body.question
        if body.filter_summary:
            question = f"[Active data filters: {body.filter_summary}]\n\n{question}"
        result = agent_ask(question, body.chat_history or [])
        return AskResponse(answer=result["answer"], steps=result.get("steps", []))
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Agent error")
        raise HTTPException(status_code=500, detail=str(e))


# ── Full analysis ────────────────────────────────────────────────────────────────

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze():
    try:
        from agent.agent import generate_full_analysis
        analysis = generate_full_analysis()
        return AnalyzeResponse(analysis=analysis)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Analysis error")
        raise HTTPException(status_code=500, detail=str(e))


# ── Dashboard HTML ────────────────────────────────────────────────────────────────

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Growth Intelligence Agent · Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0f1e;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh}
a{color:#3b82f6;text-decoration:none}
/* Nav */
nav{background:#070d1a;border-bottom:1px solid #1e293b;padding:.8rem 2rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap}
.nav-brand{font-size:1rem;font-weight:700;color:#e2e8f0;display:flex;align-items:center;gap:.6rem}
.demo-badge{background:rgba(148,163,184,.1);border:1px solid rgba(148,163,184,.25);color:#94a3b8;padding:2px 9px;border-radius:20px;font-size:.7rem;font-weight:500;cursor:pointer}
.demo-badge:hover{border-color:#3b82f6;color:#e2e8f0}
.nav-links{display:flex;gap:1.2rem;font-size:.82rem;color:#64748b;align-items:center;flex-wrap:wrap}
.nav-links a{color:#64748b;transition:color .15s}.nav-links a:hover{color:#e2e8f0}
.nav-status{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);color:#4ade80;padding:3px 10px;border-radius:20px;font-size:.72rem;font-weight:600}
/* Layout */
.container{max-width:1320px;margin:0 auto;padding:1.5rem 2rem}
/* Hero */
.hero{background:linear-gradient(135deg,#0d1b2a,#1a2744 50%,#0d2137);border:1px solid #1e3a5f;border-radius:16px;padding:1.6rem 2rem;margin-bottom:1.4rem;position:relative;overflow:hidden}
.hero::after{content:'';position:absolute;top:-50%;right:-5%;width:350px;height:350px;background:radial-gradient(circle,rgba(59,130,246,.07) 0%,transparent 70%);pointer-events:none}
.hero h1{font-size:1.55rem;font-weight:700;color:#e2e8f0;margin-bottom:.3rem}
.hero p{color:#64748b;font-size:.88rem;max-width:600px}
/* KPI grid */
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.85rem;margin-bottom:1.4rem}
@media(max-width:900px){.kpi-grid{grid-template-columns:repeat(2,1fr)}}
.kpi-card{background:linear-gradient(145deg,#111827,#1a2035);border:1px solid #1e293b;border-radius:12px;padding:1rem 1.2rem;transition:border-color .2s}
.kpi-card:hover{border-color:#3b82f6}
.kpi-card.good{border-left:3px solid #22c55e}
.kpi-card.warn{border-left:3px solid #f59e0b}
.kpi-card.bad {border-left:3px solid #ef4444}
.kpi-label{color:#64748b;font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em}
.kpi-value{color:#f1f5f9;font-size:1.65rem;font-weight:700;font-family:monospace;margin:.15rem 0}
.kpi-meta{display:flex;justify-content:space-between;align-items:center;margin-top:.2rem}
.kpi-target{color:#475569;font-size:.68rem}
.kpi-delta{font-size:.7rem;font-weight:600;font-family:monospace}
.delta-up-good{color:#4ade80}.delta-up-bad{color:#f87171}
.delta-dn-good{color:#4ade80}.delta-dn-bad{color:#f87171}.delta-flat{color:#475569}
/* Section header */
.section-header{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#64748b;margin-bottom:.9rem;display:flex;align-items:center;justify-content:space-between}
.ask-cta{background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.25);color:#60a5fa;padding:3px 10px;border-radius:6px;font-size:.7rem;cursor:pointer;transition:all .15s}
.ask-cta:hover{background:rgba(59,130,246,.22);color:#93c5fd}
/* Trends section */
.trends-section{margin-bottom:1.4rem}
.charts-row{display:grid;grid-template-columns:1fr 1fr;gap:.85rem}
@media(max-width:720px){.charts-row{grid-template-columns:1fr}}
/* Card */
.card{background:#111827;border:1px solid #1e293b;border-radius:12px;padding:1.1rem 1.3rem}
/* Tabs */
.tabs{display:flex;gap:4px;margin-bottom:1.1rem}
.tab{background:#111827;border:1px solid #1e293b;border-radius:8px;padding:.42rem .95rem;cursor:pointer;font-size:.83rem;color:#64748b;font-weight:500;transition:all .15s;white-space:nowrap}
.tab.active,.tab:hover{background:#1d4ed8;border-color:#3b82f6;color:#fff}
.tab-content{display:none}.tab-content.active{display:block}
/* Chat */
.chat-messages{min-height:260px;max-height:400px;overflow-y:auto;padding:.4rem 0;margin-bottom:.8rem}
.msg{padding:.65rem .9rem;border-radius:10px;margin-bottom:.45rem;font-size:.86rem;line-height:1.55}
.msg-user{background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.2);color:#bfdbfe;border-radius:12px 12px 2px 12px}
.msg-agent{background:rgba(30,41,59,.8);border:1px solid #1e3a5f;color:#e2e8f0;border-radius:12px 12px 12px 2px}
.msg-label{font-size:.67rem;font-weight:600;color:#475569;margin-bottom:.3rem}
.trace-toggle{font-size:.7rem;color:#475569;cursor:pointer;margin-top:.5rem;padding:3px 0;border-top:1px solid #1e293b;display:flex;align-items:center;gap:.3rem}
.trace-toggle:hover{color:#94a3b8}
.trace-body{display:none;margin-top:.4rem;font-size:.75rem;font-family:monospace}
.trace-body.open{display:block}
.trace-step{background:#0a0f1e;border:1px solid #1e293b;border-radius:6px;padding:.5rem .7rem;margin-bottom:.35rem}
.trace-tool{color:#60a5fa;font-weight:600}
.trace-in{color:#94a3b8;margin-top:.2rem;white-space:pre-wrap;word-break:break-all}
.trace-out{color:#4ade80;margin-top:.2rem;white-space:pre-wrap;word-break:break-all;max-height:80px;overflow:hidden}
.chat-form{display:flex;gap:.6rem}
.chat-input{flex:1;background:#111827;border:1px solid #1e293b;color:#e2e8f0;border-radius:8px;padding:.58rem .9rem;font-size:.86rem;outline:none}
.chat-input:focus{border-color:#3b82f6}
.btn{background:linear-gradient(135deg,#1d4ed8,#2563eb);color:#fff;border:none;border-radius:8px;padding:.58rem 1.2rem;cursor:pointer;font-weight:600;font-size:.83rem;transition:opacity .15s;white-space:nowrap}
.btn:hover{opacity:.9}.btn:disabled{opacity:.45;cursor:not-allowed}
.btn-outline{background:transparent;border:1px solid #1e3a5f;color:#64748b;border-radius:8px;padding:.42rem .9rem;cursor:pointer;font-size:.78rem;transition:all .15s}
.btn-outline:hover{border-color:#3b82f6;color:#e2e8f0}
.suggestions{display:flex;flex-wrap:wrap;gap:.45rem;margin-bottom:.75rem}
.chip{background:#111827;border:1px solid #1e293b;color:#94a3b8;border-radius:20px;padding:.28rem .75rem;cursor:pointer;font-size:.75rem;transition:all .15s}
.chip:hover{border-color:#3b82f6;color:#e2e8f0}
/* Alerts */
.alert-item{border-radius:10px;padding:.85rem 1rem;margin-bottom:.55rem}
.alert-high{background:rgba(239,68,68,.06);border:1px solid rgba(239,68,68,.28)}
.alert-medium{background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.28)}
.alert-low{background:rgba(59,130,246,.06);border:1px solid rgba(59,130,246,.28)}
.sev-badge{font-size:.65rem;font-weight:700;padding:2px 7px;border-radius:4px;float:right}
.sev-high{background:rgba(239,68,68,.2);color:#f87171}
.sev-medium{background:rgba(245,158,11,.2);color:#fbbf24}
.sev-low{background:rgba(59,130,246,.2);color:#60a5fa}
.alert-title{font-weight:600;color:#e2e8f0;font-size:.86rem}
.alert-meta{color:#94a3b8;font-family:monospace;font-size:.76rem;margin-top:.22rem}
.alert-action{color:#64748b;font-size:.76rem;margin-top:.22rem}
.alert-investigate{background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.25);color:#60a5fa;padding:2px 9px;border-radius:5px;font-size:.7rem;cursor:pointer;margin-top:.35rem;display:inline-block}
.alert-investigate:hover{background:rgba(59,130,246,.22)}
.alerts-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:.9rem;flex-wrap:wrap;gap:.5rem}
.alerts-scan-info{font-size:.78rem;color:#64748b}
/* Tables */
table{width:100%;border-collapse:collapse;font-size:.81rem}
th{color:#64748b;font-weight:600;text-align:left;padding:.45rem .65rem;border-bottom:1px solid #1e293b;text-transform:uppercase;font-size:.67rem;letter-spacing:.05em}
td{padding:.5rem .65rem;border-bottom:1px solid #0f172a;color:#cbd5e1}
tr:hover td{background:rgba(59,130,246,.04)}
/* Spinner / loading */
.spinner{display:inline-block;width:14px;height:14px;border:2px solid #1e293b;border-top-color:#3b82f6;border-radius:50%;animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-cell{text-align:center;color:#475569;padding:2rem;grid-column:1/-1}
/* Data model modal */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal{background:#111827;border:1px solid #1e293b;border-radius:14px;padding:1.8rem 2rem;max-width:540px;width:90%;max-height:80vh;overflow-y:auto}
.modal h3{font-size:1rem;font-weight:700;color:#e2e8f0;margin-bottom:1rem}
.modal-close{float:right;cursor:pointer;color:#64748b;font-size:1.1rem;line-height:1}
.modal-close:hover{color:#e2e8f0}
.dm-row{display:flex;justify-content:space-between;padding:.4rem 0;border-bottom:1px solid #0f172a;font-size:.83rem}
.dm-label{color:#94a3b8}.dm-val{color:#e2e8f0;font-family:monospace}
/* Footer */
footer{border-top:1px solid #1e293b;margin-top:2rem;padding:1.2rem 2rem;display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap}
.footer-links{display:flex;gap:1.2rem;font-size:.78rem;color:#475569;flex-wrap:wrap}
.footer-links a{color:#475569;transition:color .15s}.footer-links a:hover{color:#94a3b8}
.footer-sep{color:#1e293b}
</style>
</head>
<body>

<!-- Nav -->
<nav>
  <div class="nav-brand">
    🧠 Growth Intelligence Agent
    <span class="demo-badge" onclick="document.getElementById('dm-modal').classList.add('open')">
      Demo · Synthetic SaaS data ↗
    </span>
  </div>
  <div class="nav-links">
    <span class="nav-status" id="status-badge">⏳ Loading…</span>
    <a href="/">← Article</a>
    <a href="/architecture">Architecture</a>
    <a href="/docs" target="_blank">API Docs</a>
  </div>
</nav>

<!-- Data model modal -->
<div class="modal-overlay" id="dm-modal" onclick="if(event.target===this)this.classList.remove('open')">
  <div class="modal">
    <span class="modal-close" onclick="document.getElementById('dm-modal').classList.remove('open')">✕</span>
    <h3>Demo Data Model</h3>
    <p style="color:#64748b;font-size:.82rem;margin-bottom:1rem">
      This is a portfolio demo. All data is synthetically generated — the agent's reasoning,
      tool calls, and RAG retrieval are real; the numbers are not.
    </p>
    <div class="dm-row"><span class="dm-label">Accounts</span><span class="dm-val">300 companies · 7 industries · 4 regions</span></div>
    <div class="dm-row"><span class="dm-label">Opportunities</span><span class="dm-val">800 deals · 7 stages · $15k–$220k range</span></div>
    <div class="dm-row"><span class="dm-label">Product Usage</span><span class="dm-val">~500 rows · 5 products · 17% at-risk</span></div>
    <div class="dm-row"><span class="dm-label">Marketing Leads</span><span class="dm-val">2,000 leads · 6 sources · 18.6% conv.</span></div>
    <div class="dm-row"><span class="dm-label">Subscriptions</span><span class="dm-val">300 ARR rows · 29% expansion</span></div>
    <div class="dm-row"><span class="dm-label">Metrics History</span><span class="dm-val">9 KPIs × 8 quarters (2024–2025)</span></div>
    <div style="margin-top:1rem">
      <a href="https://github.com/ShrikantLambe/growth_intelligence_agent" target="_blank"
         style="font-size:.8rem;color:#3b82f6">View data generation code on GitHub →</a>
    </div>
  </div>
</div>

<div class="container">

  <!-- Hero -->
  <div class="hero">
    <h1>Growth Intelligence Agent</h1>
    <p>Ask why EMEA win rate dropped — get an answer grounded in your strategy, in seconds.</p>
  </div>

  <!-- KPI Cards -->
  <div class="kpi-grid" id="kpi-grid">
    <div class="loading-cell"><div class="spinner"></div></div>
  </div>

  <!-- Trends & Targets (always visible — replaces Metrics tab) -->
  <div class="trends-section">
    <div class="section-header">
      Trends &amp; Targets
    </div>
    <div class="charts-row">
      <div class="card">
        <div class="section-header">
          WIN RATE BY REGION
          <span class="ask-cta" onclick="askAgent('What is driving regional win rate differences, and which region needs the most attention?')">🤖 Ask agent</span>
        </div>
        <canvas id="chart-wr-region" height="180"></canvas>
        <div id="wr-region-empty" style="display:none;color:#475569;font-size:.82rem;padding:1rem 0">No regional data available.</div>
      </div>
      <div class="card">
        <div class="section-header">
          PERFORMANCE VS TARGET
          <span class="ask-cta" onclick="askAgent('Which KPIs are furthest from target and what is the most impactful action I can take to close the gap?')">🤖 Ask agent</span>
        </div>
        <canvas id="chart-perf-target" height="180"></canvas>
      </div>
    </div>
  </div>

  <!-- Tabs -->
  <div class="tabs">
    <div class="tab active" onclick="switchTab('chat')">💬 AI Chat</div>
    <div class="tab" onclick="switchTab('pipeline')">🔀 Pipeline</div>
    <div class="tab" onclick="switchTab('alerts')">🚨 Alerts</div>
  </div>

  <!-- ── Tab: Chat ── -->
  <div class="tab-content active" id="tab-chat">
    <div class="card">
      <div class="suggestions" id="suggestions"></div>
      <div class="chat-messages" id="chat-messages"></div>
      <div class="chat-form">
        <input class="chat-input" id="chat-input"
               placeholder="e.g. What is driving pipeline decline in EMEA?"
               onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage()}"/>
        <button class="btn" id="send-btn" onclick="sendMessage()">Send ↑</button>
        <button class="btn-outline" id="clear-btn" onclick="clearChat()">Clear</button>
      </div>
    </div>
  </div>

  <!-- ── Tab: Pipeline ── -->
  <div class="tab-content" id="tab-pipeline">
    <div class="charts-row" style="margin-bottom:.85rem">
      <div class="card">
        <div class="section-header">
          PIPELINE BY REGION
          <span class="ask-cta" onclick="askAgent('Why is North America pipeline significantly larger than other regions, and is this healthy?')">🤖 Ask agent</span>
        </div>
        <canvas id="chart-pipeline-region" height="200"></canvas>
      </div>
      <div class="card">
        <div class="section-header">
          PIPELINE BY STAGE
          <span class="ask-cta" onclick="askAgent('How is our deal progression through the funnel and where are deals getting stuck?')">🤖 Ask agent</span>
        </div>
        <canvas id="chart-pipeline-stage" height="200"></canvas>
      </div>
    </div>
    <div class="card">
      <div class="section-header">
        PIPELINE BY INDUSTRY (Open Pipeline Value)
        <span class="ask-cta" onclick="askAgent('Which industry vertical has the strongest pipeline momentum and what should we prioritize?')">🤖 Ask agent</span>
      </div>
      <canvas id="chart-pipeline-industry" height="180"></canvas>
    </div>
  </div>

  <!-- ── Tab: Alerts ── -->
  <div class="tab-content" id="tab-alerts">
    <div class="card">
      <div class="alerts-header">
        <div>
          <div style="font-weight:600;color:#e2e8f0;font-size:.92rem;margin-bottom:.2rem">Anomaly Alerts</div>
          <div class="alerts-scan-info" id="alerts-scan-info">Scanning for anomalies…</div>
        </div>
        <button class="btn-outline" id="rescan-btn" onclick="runAlerts(true)">↺ Rescan</button>
      </div>
      <div id="alerts-container"><div class="loading-cell"><div class="spinner"></div> Analyzing metrics…</div></div>
    </div>
  </div>

</div><!-- /container -->

<!-- Footer -->
<footer>
  <div style="color:#334155;font-size:.75rem;font-weight:600">Shrikant Lambe</div>
  <div class="footer-links">
    <a href="https://github.com/ShrikantLambe/growth_intelligence_agent" target="_blank">GitHub</a>
    <span class="footer-sep">·</span>
    <a href="/" >Article</a>
    <span class="footer-sep">·</span>
    <a href="https://www.linkedin.com/in/shrikantlambe" target="_blank">LinkedIn</a>
    <span class="footer-sep">·</span>
    <a href="/architecture">Architecture</a>
    <span class="footer-sep">·</span>
    <a href="/docs" target="_blank">API Docs</a>
  </div>
</footer>

<script>
// ── Config ────────────────────────────────────────────────────────────────────
const SUGGESTIONS = [
  "What is our current win rate by region?",
  "Which accounts are at churn risk?",
  "How is our pipeline coverage vs target?",
  "What are the top expansion opportunities?",
  "Summarize our overall growth health",
];

const KPI_DEFS = [
  {name:'Win Rate',                key:'Win Rate',                  fmt:'pct', target:0.28, minimize:false, tgtLabel:'≥ 28%',   deltaUnit:'pp'},
  {name:'Pipeline Coverage',       key:'Pipeline Coverage',         fmt:'x',   target:3.5,  minimize:false, tgtLabel:'≥ 3.5x',  deltaUnit:'x'},
  {name:'Net Rev Retention',       key:'Net Revenue Retention',     fmt:'pct', target:1.20, minimize:false, tgtLabel:'≥ 120%',  deltaUnit:'pp'},
  {name:'Avg Deal Size',           key:'Average Deal Size',         fmt:'$',   target:55000,minimize:false, tgtLabel:'Maximize',deltaUnit:'$k'},
  {name:'Product Attach',          key:'Product Attach Rate',       fmt:'pct', target:0.35, minimize:false, tgtLabel:'≥ 35%',   deltaUnit:'pp'},
  {name:'Seat Expansion',          key:'Seat Expansion Rate',       fmt:'pct', target:0.25, minimize:false, tgtLabel:'≥ 25%',   deltaUnit:'pp'},
  {name:'Usage At-Risk',           key:'Usage At-Risk Rate',        fmt:'pct', target:0.10, minimize:true,  tgtLabel:'< 10%',   deltaUnit:'pp'},
  {name:'Sales Cycle (d)',         key:'Sales Cycle Length (days)', fmt:'d',   target:60,   minimize:true,  tgtLabel:'< 60d',   deltaUnit:'d'},
];

const PERF_TARGET_METRICS = KPI_DEFS.filter(d=>d.key!=='Average Deal Size');

// ── Tab switching ─────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t,i)=>{
    t.classList.toggle('active', ['chat','pipeline','alerts'][i]===name);
  });
  document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  if(name==='pipeline' && !_pipelineLoaded) loadPipeline();
  if(name==='alerts' && !_alertsLoaded) runAlerts(false);
}

// ── Formatting helpers ────────────────────────────────────────────────────────
function fmtKpi(d, v) {
  if(v==null) return '—';
  if(d.fmt==='pct') return (v*100).toFixed(1)+'%';
  if(d.fmt==='x')   return v.toFixed(2)+'x';
  if(d.fmt==='$')   return '$'+Number(v).toLocaleString('en-US',{maximumFractionDigits:0});
  return v.toFixed(1);
}
function fmtDelta(d, delta) {
  if(!delta && delta!==0) return '';
  const abs = Math.abs(delta);
  let str;
  if(d.fmt==='pct')      str = (abs*100).toFixed(1)+'pp';
  else if(d.fmt==='x')   str = abs.toFixed(2)+'x';
  else if(d.fmt==='$')   str = '$'+(abs/1000).toFixed(1)+'k';
  else                   str = abs.toFixed(1)+'d';
  const arrow = delta>0 ? '▲' : '▼';
  const favorable = d.minimize ? delta<0 : delta>0;
  const cls = delta>0 ? (favorable?'delta-up-good':'delta-up-bad') : (favorable?'delta-dn-good':'delta-dn-bad');
  return `<span class="${cls}">${arrow} ${str} vs Q4 2025</span>`;
}
function escHtml(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br>')}

// ── KPI Cards with deltas ─────────────────────────────────────────────────────
async function loadKPIs() {
  try {
    const [cur, hist] = await Promise.all([
      fetch('/api/metrics').then(r=>r.json()),
      fetch('/api/metrics-history?quarter=2025-Q4').then(r=>r.json()).catch(()=>[]),
    ]);
    document.getElementById('status-badge').textContent = '✅ Live Data';

    const byName = {}, q4 = {};
    cur.forEach(r=>{ if(r.segment==='All') byName[r.metric_name]=r.metric_value; });
    hist.forEach(r=>{ q4[r.metric_name]=r.metric_value; });

    const grid = document.getElementById('kpi-grid');
    grid.innerHTML = KPI_DEFS.map(d=>{
      const v = byName[d.key];
      const prior = q4[d.key];
      const delta = (v!=null && prior!=null) ? v - prior : null;
      const display = fmtKpi(d, v);
      const deltaHtml = fmtDelta(d, delta);

      let status = '';
      if(v!=null) {
        const good = d.minimize ? v <= d.target : v >= d.target;
        const warn = d.minimize ? v <= d.target*1.3 : v >= d.target*0.8;
        status = good ? 'good' : warn ? 'warn' : 'bad';
      }
      return `<div class="kpi-card ${status}">
        <div class="kpi-label">${d.name}</div>
        <div class="kpi-value">${display}</div>
        <div class="kpi-meta">
          <span class="kpi-target">Target: ${d.tgtLabel}</span>
          ${deltaHtml}
        </div>
      </div>`;
    }).join('');

    // Render always-visible trend charts after KPIs load
    renderTrendCharts(cur, hist);
  } catch(e) {
    document.getElementById('status-badge').textContent = '⚠️ Error';
    document.getElementById('kpi-grid').innerHTML =
      `<div class="loading-cell" style="color:#f87171">Failed to load metrics: ${e.message}</div>`;
  }
}

// ── Trends & Targets charts ───────────────────────────────────────────────────
function renderTrendCharts(metricsData, histData) {
  const BLUE = '#3b82f6';
  const GRID = '#1e293b';

  // Win Rate by Region from metrics.csv (regional rows computed by compute_metrics.py)
  const wrRegion = metricsData.filter(r=>r.metric_name==='Win Rate' && r.segment!=='All')
    .sort((a,b)=>b.metric_value-a.metric_value);
  const wrEl = document.getElementById('chart-wr-region');
  const emptyEl = document.getElementById('wr-region-empty');
  if(wrRegion.length) {
    new Chart(wrEl, {
      type:'bar',
      data:{
        labels: wrRegion.map(r=>r.segment),
        datasets:[{data:wrRegion.map(r=>+(r.metric_value*100).toFixed(1)), backgroundColor:BLUE, borderRadius:5}]
      },
      options:{
        plugins:{legend:{display:false}},
        scales:{
          y:{ticks:{callback:v=>v+'%'}, grid:{color:GRID}, min:0, max:50},
          x:{grid:{color:GRID}}
        },
        responsive:true
      }
    });
    // Target line annotation via afterDraw plugin
    Chart.register({
      id:'target-line',
      afterDraw(chart){
        if(chart.canvas.id!=='chart-wr-region') return;
        const {ctx,chartArea,scales} = chart;
        const y = scales.y.getPixelForValue(28);
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([5,4]);
        ctx.strokeStyle='#f59e0b';
        ctx.lineWidth=1.5;
        ctx.moveTo(chartArea.left,y);
        ctx.lineTo(chartArea.right,y);
        ctx.stroke();
        ctx.fillStyle='#f59e0b';
        ctx.font='10px monospace';
        ctx.fillText('Target 28%',chartArea.right-68,y-4);
        ctx.restore();
      }
    });
  } else {
    wrEl.style.display='none';
    emptyEl.style.display='block';
  }

  // Performance vs Target
  const byName = {};
  metricsData.forEach(r=>{ if(r.segment==='All') byName[r.metric_name]=r.metric_value; });
  const perfData = PERF_TARGET_METRICS.map(d=>{
    const v = byName[d.key];
    if(v==null) return {label:d.name, pct:0, color:'#475569'};
    const pct = Math.min(130, d.minimize ? (d.target/v)*100 : (v/d.target)*100);
    const color = pct>=100 ? '#22c55e' : pct>=80 ? '#f59e0b' : '#ef4444';
    return {label:d.name, pct:+pct.toFixed(1), color};
  }).reverse();

  new Chart(document.getElementById('chart-perf-target'), {
    type:'bar',
    data:{
      labels: perfData.map(d=>d.label),
      datasets:[{
        data: perfData.map(d=>d.pct),
        backgroundColor: perfData.map(d=>d.color),
        borderRadius:4
      }]
    },
    options:{
      indexAxis:'y',
      plugins:{legend:{display:false}},
      scales:{
        x:{ticks:{callback:v=>v+'%'}, grid:{color:GRID}, min:0, max:135},
        y:{grid:{color:GRID}}
      },
      responsive:true
    }
  });
  // Reference line at 100%
  Chart.register({
    id:'target-ref',
    afterDraw(chart){
      if(chart.canvas.id!=='chart-perf-target') return;
      const {ctx,chartArea,scales} = chart;
      const x = scales.x.getPixelForValue(100);
      ctx.save();
      ctx.beginPath();
      ctx.setLineDash([4,3]);
      ctx.strokeStyle='rgba(255,255,255,.25)';
      ctx.lineWidth=1.5;
      ctx.moveTo(x,chartArea.top);
      ctx.lineTo(x,chartArea.bottom);
      ctx.stroke();
      ctx.fillStyle='rgba(255,255,255,.35)';
      ctx.font='9px monospace';
      ctx.fillText('Target',x+4,chartArea.top+12);
      ctx.restore();
    }
  });
}

// ── Pipeline charts ───────────────────────────────────────────────────────────
let _pipelineLoaded = false;
async function loadPipeline() {
  if(_pipelineLoaded) return;
  _pipelineLoaded = true;
  const BLUE  = '#3b82f6';
  const GRID  = '#1e293b';
  const FUNNEL_ORDER = ['Prospecting','Discovery','Demo','Proposal','Negotiation','Closed Won','Closed Lost'];
  const STAGE_COLORS = {
    'Prospecting':'#3b82f6','Discovery':'#06b6d4','Demo':'#8b5cf6',
    'Proposal':'#f59e0b','Negotiation':'#f97316',
    'Closed Won':'#22c55e','Closed Lost':'#64748b',
  };

  try {
    const [regionRes, stageRes, industryRes] = await Promise.all([
      fetch('/api/pipeline?segment=region').then(r=>r.json()),
      fetch('/api/pipeline?segment=stage').then(r=>r.json()),
      fetch('/api/pipeline?segment=industry').then(r=>r.json()),
    ]);
    const parse = d=>{ try{return typeof d.data==='string'?JSON.parse(d.data):d.data;}catch(e){return [];} };
    const rData = parse(regionRes);
    const sDataRaw = parse(stageRes);
    const iData = parse(industryRes);

    // Pipeline by Region — single blue, sorted by value
    if(Array.isArray(rData) && rData.length) {
      const sorted = [...rData].sort((a,b)=>b.open_pipeline_value-a.open_pipeline_value);
      new Chart(document.getElementById('chart-pipeline-region'),{
        type:'bar',
        data:{
          labels:sorted.map(r=>r.segment),
          datasets:[{data:sorted.map(r=>r.open_pipeline_value),backgroundColor:BLUE,borderRadius:5}]
        },
        options:{
          plugins:{legend:{display:false}},
          scales:{
            y:{ticks:{callback:v=>'$'+Number(v/1e6).toFixed(1)+'M'},grid:{color:GRID}},
            x:{grid:{color:GRID}}
          },
          responsive:true
        }
      });
    }

    // Pipeline by Stage — funnel order, semantic colors
    if(Array.isArray(sDataRaw) && sDataRaw.length) {
      const byStage = {};
      sDataRaw.forEach(r=>{ byStage[r.segment]=r; });
      const ordered = FUNNEL_ORDER.filter(s=>byStage[s]);
      new Chart(document.getElementById('chart-pipeline-stage'),{
        type:'doughnut',
        data:{
          labels:ordered,
          datasets:[{
            data:ordered.map(s=>(byStage[s].open_pipeline_value||byStage[s].total_pipeline||0)),
            backgroundColor:ordered.map(s=>STAGE_COLORS[s]||BLUE),
            borderWidth:1,
            borderColor:'#0a0f1e'
          }]
        },
        options:{
          plugins:{legend:{position:'right',labels:{color:'#94a3b8',boxWidth:11,font:{size:11}}}},
          responsive:true
        }
      });
    }

    // Pipeline by Industry — horizontal bars, pipeline VALUE in $, sorted desc, single color
    if(Array.isArray(iData) && iData.length) {
      const sorted = [...iData].sort((a,b)=>b.open_pipeline_value-a.open_pipeline_value);
      new Chart(document.getElementById('chart-pipeline-industry'),{
        type:'bar',
        data:{
          labels:sorted.map(r=>r.segment),
          datasets:[{data:sorted.map(r=>r.open_pipeline_value),backgroundColor:BLUE,borderRadius:4}]
        },
        options:{
          indexAxis:'y',
          plugins:{legend:{display:false}},
          scales:{
            x:{ticks:{callback:v=>'$'+Number(v/1e6).toFixed(1)+'M'},grid:{color:GRID}},
            y:{grid:{color:GRID}}
          },
          responsive:true
        }
      });
    }
  } catch(e) { console.error('Pipeline load error:', e); }
}

// ── Alerts (auto-run) ─────────────────────────────────────────────────────────
let _alertsLoaded = false, _alertsTs = null;

async function runAlerts(force) {
  if(_alertsLoaded && !force) return;
  _alertsLoaded = true;
  _alertsTs = Date.now();
  document.getElementById('alerts-scan-info').textContent = 'Scanning…';
  document.getElementById('alerts-container').innerHTML =
    '<div class="loading-cell"><div class="spinner"></div> Analyzing metrics…</div>';
  try {
    const data = await fetch('/api/alerts').then(r=>r.json());
    const elapsed = ((Date.now()-_alertsTs)/1000).toFixed(0);
    const alerts = data.alerts||[];
    const counts = {High:0,Medium:0,Low:0};
    alerts.forEach(a=>counts[a.severity]=(counts[a.severity]||0)+1);
    document.getElementById('alerts-scan-info').innerHTML =
      `Last scanned ${elapsed}s ago &nbsp;·&nbsp; `+
      `<span style="color:#f87171">${counts.High} High</span> &nbsp;`+
      `<span style="color:#fbbf24">${counts.Medium} Medium</span> &nbsp;`+
      `<span style="color:#60a5fa">${counts.Low} Low</span>`;

    if(!alerts.length){
      document.getElementById('alerts-container').innerHTML =
        '<p style="color:#4ade80;font-size:.86rem;padding:.5rem 0">✅ All metrics within normal range. No anomalies detected.</p>';
      return;
    }

    document.getElementById('alerts-container').innerHTML = alerts.map(a=>{
      const sev=a.severity.toLowerCase();
      const sign=a.change_pct>0?'+':'';
      const investigateQ=`Investigate the ${a.metric} anomaly in ${a.segment} — it changed ${sign}${a.change_pct}% from the prior period. What is the likely root cause and recommended action?`;
      return `<div class="alert-item alert-${sev}">
        <span class="sev-badge sev-${sev}">${a.severity}</span>
        <div class="alert-title">${a.direction} ${a.metric}
          <span style="color:#64748b;font-size:.76rem"> · ${a.segment}</span>
        </div>
        <div class="alert-meta">${a.is_positive?'✅':'❌'} ${sign}${a.change_pct}% &nbsp;·&nbsp; ${a.previous_value} → ${a.current_value}</div>
        <div class="alert-action">💡 ${a.recommended_action}</div>
        <span class="alert-investigate" onclick="askAgent(${JSON.stringify(investigateQ)})">→ Investigate with agent</span>
      </div>`;
    }).join('');
  } catch(e) {
    document.getElementById('alerts-container').innerHTML =
      `<p style="color:#f87171;font-size:.84rem">Alert check failed: ${e.message}</p>`;
    document.getElementById('alerts-scan-info').textContent = 'Scan failed';
  }
}

// ── Chat ──────────────────────────────────────────────────────────────────────
const chatHistory = [];

function addMessage(role, text, steps) {
  const el = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg msg-'+role;

  let traceHtml = '';
  if(steps && steps.length) {
    const tid = 'trace-'+Date.now();
    const stepHtml = steps.map(s=>`
      <div class="trace-step">
        <div class="trace-tool">⚙ ${s.tool}</div>
        <div class="trace-in">in: ${JSON.stringify(s.input)}</div>
        <div class="trace-out">out: ${escHtml(String(s.output||'').substring(0,300))}${(s.output||'').length>300?'…':''}</div>
      </div>`).join('');
    traceHtml = `<div class="trace-toggle" onclick="document.getElementById('${tid}').classList.toggle('open');this.querySelector('span').textContent=document.getElementById('${tid}').classList.contains('open')?'▲ Hide reasoning':'▼ View reasoning (${steps.length} tool calls)'">
      <span>▼ View reasoning (${steps.length} tool calls)</span>
    </div>
    <div class="trace-body" id="${tid}">${stepHtml}</div>`;
  }
  div.innerHTML = `<div class="msg-label">${role==='user'?'👤 You':'🧠 Agent'}</div>${escHtml(text)}${traceHtml}`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

async function sendMessage(text) {
  const input = document.getElementById('chat-input');
  const question = text || input.value.trim();
  if(!question) return;
  input.value = '';
  const btn = document.getElementById('send-btn');
  btn.disabled = true;

  // Switch to chat tab if not already there
  switchTab('chat');

  addMessage('user', question, null);
  const histPairs = [];
  for(let i=0;i<chatHistory.length-1;i+=2) {
    if(chatHistory[i]&&chatHistory[i+1]) histPairs.push([chatHistory[i].text,chatHistory[i+1].text]);
  }
  chatHistory.push({role:'user',text:question});

  const thinkDiv = document.createElement('div');
  thinkDiv.className='msg msg-agent';
  thinkDiv.innerHTML='<div class="msg-label">🧠 Agent</div><div class="spinner"></div> Reasoning…';
  document.getElementById('chat-messages').appendChild(thinkDiv);
  document.getElementById('chat-messages').scrollTop=99999;

  try {
    const res = await fetch('/api/ask',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question,chat_history:histPairs})
    });
    const data = await res.json();
    const answer = data.answer||data.detail||'No response';
    thinkDiv.remove();
    addMessage('agent', answer, data.steps||[]);
    chatHistory.push({role:'agent',text:answer});
  } catch(e) {
    thinkDiv.remove();
    addMessage('agent',`⚠️ Error: ${e.message}. Ensure API key is set.`,null);
  }
  btn.disabled=false;
}

function clearChat() {
  chatHistory.length=0;
  document.getElementById('chat-messages').innerHTML='';
}

function askAgent(question) {
  switchTab('chat');
  sendMessage(question);
}

// Suggestion chips
document.getElementById('suggestions').innerHTML = SUGGESTIONS.map(s=>
  `<span class="chip" onclick="sendMessage(${JSON.stringify(s)})">${s.substring(0,36)}…</span>`
).join('');

// ── Init ──────────────────────────────────────────────────────────────────────
loadKPIs();
// Pre-warm alerts
setTimeout(()=>{ if(!_alertsLoaded) runAlerts(false); }, 2000);
</script>
</body>
</html>"""


# ── Architecture page HTML ────────────────────────────────────────────────────

_ARCHITECTURE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Architecture · Growth Intelligence Agent</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0f1e;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh}
nav{background:#070d1a;border-bottom:1px solid #1e293b;padding:.8rem 2rem;display:flex;align-items:center;justify-content:space-between}
.nav-brand{font-size:1rem;font-weight:700;color:#e2e8f0}
.nav-links{display:flex;gap:1.2rem;font-size:.82rem}
.nav-links a{color:#64748b;text-decoration:none;transition:color .15s}
.nav-links a:hover{color:#e2e8f0}
.container{max-width:860px;margin:0 auto;padding:2.5rem 2rem}
h1{font-size:1.6rem;font-weight:700;color:#e2e8f0;margin-bottom:.4rem}
.subtitle{color:#64748b;font-size:.9rem;margin-bottom:2.5rem}
h2{font-size:1rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;margin:2.2rem 0 1rem}
pre.diagram{background:#070d1a;border:1px solid #1e293b;border-radius:10px;padding:1.4rem 1.6rem;font-family:monospace;font-size:.82rem;color:#94a3b8;overflow-x:auto;line-height:1.7}
pre.diagram .hl{color:#3b82f6}
pre.diagram .gr{color:#22c55e}
.tools-grid{display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin-bottom:1.5rem}
@media(max-width:600px){.tools-grid{grid-template-columns:1fr}}
.tool-card{background:#111827;border:1px solid #1e293b;border-radius:10px;padding:.9rem 1.1rem}
.tool-name{color:#3b82f6;font-weight:700;font-size:.88rem;margin-bottom:.3rem;font-family:monospace}
.tool-desc{color:#94a3b8;font-size:.8rem;line-height:1.5}
.stack-row{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1.5rem}
.badge{background:#111827;border:1px solid #1e293b;padding:4px 11px;border-radius:20px;font-size:.75rem;color:#94a3b8;font-family:monospace}
.links-row{display:flex;gap:1rem;flex-wrap:wrap;margin-top:2rem;padding-top:1.5rem;border-top:1px solid #1e293b}
.links-row a{color:#3b82f6;font-size:.84rem;text-decoration:none}
.links-row a:hover{text-decoration:underline}
</style>
</head>
<body>
<nav>
  <div class="nav-brand">🧠 Growth Intelligence Agent</div>
  <div class="nav-links">
    <a href="/dashboard">Dashboard</a>
    <a href="/">Article</a>
    <a href="/docs" target="_blank">API Docs</a>
    <a href="https://github.com/ShrikantLambe/growth_intelligence_agent" target="_blank">GitHub</a>
  </div>
</nav>
<div class="container">
  <h1>System Architecture</h1>
  <p class="subtitle">How the Growth Intelligence Agent reasons over live SaaS data using tools, RAG, and an LLM.</p>

  <h2>Data & Request Flow</h2>
  <pre class="diagram">
  Browser / API Client
        │
        ▼
  <span class="hl">FastAPI Backend</span>  (api/main.py · Vercel serverless)
        │
        ▼
  <span class="hl">LangGraph ReAct Agent</span>  (agent/agent.py)
  ┌─────┴─────────────────────────────────────┐
  │  System prompt + tool descriptions         │
  │  Max iterations: 8  ·  Model: Claude        │
  └─────┬─────────────────────────────────────┘
        │ selects tools as needed
  ┌─────┼──────────────────────────────────────────────────┐
  │     ▼               ▼               ▼                  │
  │  get_metric    get_pipeline    get_product_usage        │
  │  (metrics.csv) (opps+accts)   (usage events)           │
  │                                                         │
  │     ▼               ▼                                   │
  │  get_deals     get_company_context                      │
  │  (CRM stages)  (FAISS RAG over playbooks)               │
  └─────────────────────────────────────────────────────────┘
        │
        ▼
  <span class="gr">Structured answer</span>: Key Insight · Root Cause · Data · Actions
  </pre>

  <h2>The 5 MCP-Pattern Tools</h2>
  <div class="tools-grid">
    <div class="tool-card">
      <div class="tool-name">get_metric(query)</div>
      <div class="tool-desc">Keyword-maps natural language to rows in metrics.csv. Returns win rate, NRR, pipeline coverage, deal size, and 5 other KPIs — overall and by segment.</div>
    </div>
    <div class="tool-card">
      <div class="tool-name">get_pipeline_by_segment(query)</div>
      <div class="tool-desc">Segments the CRM opportunity table by region, industry, or stage. Returns open pipeline value, deal counts, and win rates per segment.</div>
    </div>
    <div class="tool-card">
      <div class="tool-name">get_product_usage(query)</div>
      <div class="tool-desc">Usage analytics with at-risk detection. Flags accounts with no activity in 30+ days. Can query by account ID (e.g. "account ACC0042").</div>
    </div>
    <div class="tool-card">
      <div class="tool-name">get_deals_by_stage(query)</div>
      <div class="tool-desc">CRM deals filtered by mode: closing-this-month, high-value (top 20%), or stalled (no movement in 60+ days).</div>
    </div>
    <div class="tool-card" style="grid-column:1/-1">
      <div class="tool-name">get_company_context(query)</div>
      <div class="tool-desc">RAG retrieval over 3 internal playbooks (ICP, growth strategy, pricing rules). Chunked at 800 chars with 100-char overlap, embedded with HuggingFace all-MiniLM-L6-v2, stored in FAISS. Returns top-4 relevant chunks. Degrades gracefully if vectorstore unavailable.</div>
    </div>
  </div>

  <h2>Stack</h2>
  <div class="stack-row">
    <span class="badge">Python 3.12</span>
    <span class="badge">FastAPI</span>
    <span class="badge">LangChain 1.x</span>
    <span class="badge">LangGraph (ReAct)</span>
    <span class="badge">Claude (Haiku / Sonnet)</span>
    <span class="badge">FAISS</span>
    <span class="badge">HuggingFace all-MiniLM-L6-v2</span>
    <span class="badge">Pandas</span>
    <span class="badge">Vercel (serverless)</span>
  </div>

  <h2>Data Layer</h2>
  <pre class="diagram">
  scripts/generate_data.py     →  data/raw/*.csv
    300 accounts · 800 deals · 2,000 leads · 300 subscriptions
    7 industries · 4 regions · realistic distributions (seed=42)

  metrics/compute_metrics.py   →  data/processed/metrics.csv
    dbt-style models: win_rate, NRR, pipeline_coverage, etc.
    Regional win rates computed via accounts join

  rag/build_vectorstore.py     →  rag/vectorstore/ (FAISS index)
    3 markdown playbooks · 800-char chunks · 18 total vectors
  </pre>

  <div class="links-row">
    <a href="https://github.com/ShrikantLambe/growth_intelligence_agent" target="_blank">GitHub Repository</a>
    <a href="/">Portfolio Article</a>
    <a href="/dashboard">Live Dashboard</a>
    <a href="/docs" target="_blank">API Reference</a>
  </div>
</div>
</body>
</html>"""
