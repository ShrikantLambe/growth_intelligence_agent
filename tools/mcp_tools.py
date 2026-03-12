"""
Phase 4: MCP-compatible tool definitions for the Growth Intelligence Agent.
Each tool wraps a data source and returns structured JSON the agent can reason over.
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from langchain.tools import tool

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def _load(filename: str) -> pd.DataFrame:
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data file not found: {path}. Run scripts/generate_data.py first.")
    return pd.read_csv(path)


# ── Tool 1: Warehouse Metrics Tool ─────────────────────────────────────────────
@tool
def get_metric(query: str) -> str:
    """
    Retrieve growth metrics from the metrics warehouse.
    Input should be a metric name or question like:
    'win rate', 'pipeline coverage', 'NRR', 'seat expansion rate', 'all metrics'.
    Returns metric name, segment, value, and date.
    """
    metrics_path = os.path.join(PROCESSED_DIR, "metrics.csv")
    if not os.path.exists(metrics_path):
        return json.dumps({"error": "Metrics not computed yet. Run metrics/compute_metrics.py first."})

    df = pd.read_csv(metrics_path)
    q = query.lower()

    # Smart keyword matching
    keyword_map = {
        "win rate": "Win Rate",
        "pipeline": "Pipeline Coverage",
        "deal size": "Average Deal Size",
        "sales cycle": "Sales Cycle Length",
        "nrr": "Net Revenue Retention",
        "retention": "Net Revenue Retention",
        "attach rate": "Product Attach Rate",
        "product attach": "Product Attach Rate",
        "seat expansion": "Seat Expansion Rate",
        "expansion": "Seat Expansion Rate",
        "lead conversion": "Lead Conversion Rate",
        "conversion": "Lead Conversion Rate",
        "usage": "Usage At-Risk Rate",
        "at-risk": "Usage At-Risk Rate",
        "churn": "Usage At-Risk Rate",
    }

    if "all" in q:
        result = df.to_dict(orient="records")
    else:
        matched_name = next((v for k, v in keyword_map.items() if k in q), None)
        if matched_name:
            result = df[df["metric_name"] == matched_name].to_dict(orient="records")
        else:
            result = df[df["metric_name"].str.lower().str.contains(q, na=False)].to_dict(orient="records")

    if not result:
        return json.dumps({"message": f"No metrics found matching: {query}", "available": df["metric_name"].unique().tolist()})

    return json.dumps(result, indent=2)


# ── Tool 2: Opportunity / Pipeline Tool ────────────────────────────────────────
@tool
def get_pipeline_by_segment(query: str = "all") -> str:
    """
    Retrieve CRM opportunity pipeline data, segmented by stage, region, or industry.
    Input examples: 'by region', 'by stage', 'by industry', 'open deals', 'all'.
    Returns pipeline value, deal counts, and win rates per segment.
    """
    opps = _load("opportunities.csv")
    accounts = _load("accounts.csv")
    merged = opps.merge(accounts[["account_id", "region", "industry"]], on="account_id", how="left")

    q = query.lower()

    def summarize(df, group_col):
        summary = []
        for val, grp in df.groupby(group_col):
            closed = grp[grp["stage"].isin(["Closed Won", "Closed Lost"])]
            won = (grp["stage"] == "Closed Won").sum()
            summary.append({
                "segment": str(val),
                "open_pipeline_value": int(grp[~grp["stage"].isin(["Closed Won", "Closed Lost"])]["pipeline_value"].sum()),
                "total_deals": len(grp),
                "closed_won": int(won),
                "win_rate": round(won / len(closed), 3) if len(closed) else 0,
                "avg_deal_size": int(grp[grp["stage"] == "Closed Won"]["pipeline_value"].mean() or 0),
            })
        return summary

    if "region" in q:
        result = summarize(merged, "region")
    elif "industry" in q:
        result = summarize(merged, "industry")
    elif "stage" in q:
        result = summarize(merged, "stage")
    else:
        # Open pipeline overview
        open_opps = merged[~merged["stage"].isin(["Closed Won", "Closed Lost"])]
        result = {
            "total_open_pipeline": int(open_opps["pipeline_value"].sum()),
            "open_deal_count": len(open_opps),
            "avg_open_deal_size": int(open_opps["pipeline_value"].mean() or 0),
            "top_stages": open_opps["stage"].value_counts().to_dict(),
        }

    return json.dumps(result, indent=2)


# ── Tool 3: Product Usage Analytics Tool ───────────────────────────────────────
@tool
def get_product_usage(query: str = "summary") -> str:
    """
    Retrieve product usage analytics.
    Input examples: 'summary', 'at-risk accounts', 'top products', 'account ACC0001'.
    Returns usage events, active users, last active dates, and risk signals.
    """
    usage = _load("product_usage.csv")
    q = query.lower()

    cutoff_30 = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    cutoff_60 = (datetime.today() - timedelta(days=60)).strftime("%Y-%m-%d")
    usage["last_active_date"] = usage["last_active_date"].astype(str)

    if "at-risk" in q or "risk" in q or "churn" in q:
        at_risk = usage[usage["last_active_date"] < cutoff_30]
        result = {
            "at_risk_accounts": at_risk["account_id"].nunique(),
            "total_accounts": usage["account_id"].nunique(),
            "at_risk_rate": round(at_risk["account_id"].nunique() / usage["account_id"].nunique(), 3),
            "sample_at_risk": at_risk[["account_id", "product_name", "last_active_date"]].head(10).to_dict(orient="records"),
        }
    elif "top product" in q or "product" in q:
        product_summary = usage.groupby("product_name").agg(
            accounts=("account_id", "nunique"),
            total_active_users=("active_users", "sum"),
            total_usage_events=("usage_events", "sum"),
        ).reset_index().sort_values("total_active_users", ascending=False)
        result = product_summary.to_dict(orient="records")
    elif q.startswith("account"):
        acct_id = query.strip().split()[-1].upper()
        acct_usage = usage[usage["account_id"] == acct_id]
        result = acct_usage.to_dict(orient="records") if len(acct_usage) else {"message": f"No usage data for {acct_id}"}
    else:
        result = {
            "total_accounts": int(usage["account_id"].nunique()),
            "total_products": int(usage["product_name"].nunique()),
            "total_active_users": int(usage["active_users"].sum()),
            "total_usage_events": int(usage["usage_events"].sum()),
            "avg_products_per_account": round(usage.groupby("account_id")["product_name"].nunique().mean(), 2),
            "accounts_inactive_30d": int((usage[usage["last_active_date"] < cutoff_30]["account_id"].nunique())),
            "accounts_inactive_60d": int((usage[usage["last_active_date"] < cutoff_60]["account_id"].nunique())),
        }

    return json.dumps(result, indent=2)


# ── Tool 4: CRM Deal Tool ──────────────────────────────────────────────────────
@tool
def get_deals_by_stage(query: str = "all") -> str:
    """
    Retrieve CRM deals organized by stage or filter for specific deal types.
    Input examples: 'all', 'closing this month', 'high value', 'stalled deals'.
    Returns deal counts, pipeline value, and deal details by stage.
    """
    opps = _load("opportunities.csv")
    accounts = _load("accounts.csv")
    merged = opps.merge(accounts[["account_id", "company_name", "industry", "region"]], on="account_id", how="left")
    merged["close_date"] = pd.to_datetime(merged["close_date"])

    q = query.lower()
    today = datetime.today()

    if "closing this month" in q or "this month" in q:
        end_of_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        subset = merged[
            (merged["close_date"] >= pd.Timestamp(today)) &
            (merged["close_date"] <= pd.Timestamp(end_of_month)) &
            (~merged["stage"].isin(["Closed Won", "Closed Lost"]))
        ]
        result = {
            "closing_this_month": len(subset),
            "total_value": int(subset["pipeline_value"].sum()),
            "deals": subset[["opportunity_id", "company_name", "stage", "pipeline_value", "close_date"]].head(20).to_dict(orient="records"),
        }
    elif "high value" in q:
        high_val = merged[
            (~merged["stage"].isin(["Closed Won", "Closed Lost"])) &
            (merged["pipeline_value"] > merged["pipeline_value"].quantile(0.8))
        ].sort_values("pipeline_value", ascending=False)
        result = high_val[["opportunity_id", "company_name", "stage", "pipeline_value", "region", "industry"]].head(20).to_dict(orient="records")
    elif "stalled" in q:
        merged["created_date"] = pd.to_datetime(merged["created_date"])
        stalled = merged[
            (~merged["stage"].isin(["Closed Won", "Closed Lost"])) &
            ((pd.Timestamp(today) - merged["created_date"]).dt.days > 60)
        ]
        result = {
            "stalled_deals": len(stalled),
            "stalled_pipeline_value": int(stalled["pipeline_value"].sum()),
            "deals": stalled[["opportunity_id", "company_name", "stage", "pipeline_value"]].head(15).to_dict(orient="records"),
        }
    else:
        by_stage = merged.groupby("stage").agg(
            deal_count=("opportunity_id", "count"),
            total_pipeline=("pipeline_value", "sum"),
            avg_deal_size=("pipeline_value", "mean"),
        ).reset_index()
        by_stage["total_pipeline"] = by_stage["total_pipeline"].astype(int)
        by_stage["avg_deal_size"] = by_stage["avg_deal_size"].round(0).astype(int)
        result = by_stage.to_dict(orient="records")

    return json.dumps(result, indent=2, default=str)


# ── Tool 5: Company Context (RAG) Tool ─────────────────────────────────────────
@tool
def get_company_context(query: str) -> str:
    """
    Retrieve relevant company strategy, ICP, pricing, and playbook context via RAG.
    Use this to ground recommendations in company-specific knowledge.
    Input: any question about company strategy, ICP, pricing, expansion, or sales rules.
    """
    try:
        from rag.build_vectorstore import retrieve_context
        return retrieve_context(query)
    except Exception as e:
        return f"RAG context unavailable: {str(e)}. Ensure the vectorstore has been built by running rag/build_vectorstore.py."


# ── Tool registry ───────────────────────────────────────────────────────────────
ALL_TOOLS = [
    get_metric,
    get_pipeline_by_segment,
    get_product_usage,
    get_deals_by_stage,
    get_company_context,
]
