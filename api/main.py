"""
FastAPI backend for the Growth Intelligence Agent.
Exposes REST endpoints suitable for a Next.js frontend on Vercel.

Local dev:  uvicorn api.main:app --reload --port 8000
Vercel:     set VERCEL=1 in env; functions run as serverless via vercel.json routing.
"""

import os
import sys
import logging
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Allow importing project modules from the repo root
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


# ── Root ─────────────────────────────────────────────────────────────────────────

from fastapi.responses import RedirectResponse

@app.get("/")
def root():
    return RedirectResponse(url="/docs")


# ── Health ───────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Metrics ──────────────────────────────────────────────────────────────────────

@app.get("/api/metrics")
def get_metrics(metric_name: Optional[str] = None, segment: Optional[str] = None):
    """Return rows from data/processed/metrics.csv, optionally filtered."""
    import pandas as pd
    path = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "metrics.csv")
    if not os.path.exists(path):
        raise HTTPException(
            status_code=503,
            detail="Metrics not computed yet. Run metrics/compute_metrics.py first.",
        )
    df = pd.read_csv(path)
    if metric_name:
        df = df[df["metric_name"].str.lower() == metric_name.lower()]
    if segment:
        df = df[df["segment"] == segment]
    return df.to_dict(orient="records")


# ── Pipeline ─────────────────────────────────────────────────────────────────────

@app.get("/api/pipeline")
def get_pipeline(segment: str = "region"):
    """Return pipeline summary segmented by region, industry, or stage."""
    try:
        from tools.mcp_tools import get_pipeline_by_segment
        return {"data": get_pipeline_by_segment.invoke(f"by {segment}")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Product usage ────────────────────────────────────────────────────────────────

@app.get("/api/usage")
def get_usage(query: str = "summary"):
    """Return product usage analytics."""
    try:
        from tools.mcp_tools import get_product_usage
        return {"data": get_product_usage.invoke(query)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Alerts ───────────────────────────────────────────────────────────────────────

@app.get("/api/alerts")
def get_alerts(threshold_pct: float = 0.20):
    """Run anomaly detection and return alert list."""
    try:
        from agent.alerts import compute_alerts
        alerts = compute_alerts(threshold_pct=threshold_pct)
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Agent chat ───────────────────────────────────────────────────────────────────

@app.post("/api/ask", response_model=AskResponse)
def ask(body: AskRequest):
    """
    Ask the Growth Intelligence Agent a natural-language question.

    Vercel Hobby timeout is 60 s; Pro is 300 s.
    LLM calls typically finish in 5–30 s — should be fine on Pro.
    For Hobby, consider using a lighter model (claude-haiku-4-5) or streaming.
    """
    try:
        from agent.agent import ask as agent_ask
        question = body.question
        if body.filter_summary:
            question = f"[Active data filters: {body.filter_summary}]\n\n{question}"
        result = agent_ask(question, body.chat_history or [])
        return AskResponse(answer=result["answer"], steps=result.get("steps", []))
    except ValueError as e:
        # Missing API key or similar configuration error
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Agent error")
        raise HTTPException(status_code=500, detail=str(e))


# ── Full analysis ────────────────────────────────────────────────────────────────

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze():
    """
    Run the comprehensive growth analysis (calls LLM directly — no tool loop).
    This endpoint typically takes 15–30 s.
    """
    try:
        from agent.agent import generate_full_analysis
        analysis = generate_full_analysis()
        return AnalyzeResponse(analysis=analysis)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Analysis error")
        raise HTTPException(status_code=500, detail=str(e))
