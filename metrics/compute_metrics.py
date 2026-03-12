"""
Phase 2: dbt-style metrics layer.
Computes all key SaaS growth metrics from raw CSV data using Pandas + SQL-style transforms.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)


def load_data():
    """Load all raw tables."""
    return {
        "accounts": pd.read_csv(os.path.join(RAW_DIR, "accounts.csv")),
        "opportunities": pd.read_csv(os.path.join(RAW_DIR, "opportunities.csv")),
        "product_usage": pd.read_csv(os.path.join(RAW_DIR, "product_usage.csv")),
        "marketing_leads": pd.read_csv(os.path.join(RAW_DIR, "marketing_leads.csv")),
        "subscriptions": pd.read_csv(os.path.join(RAW_DIR, "subscription_revenue.csv")),
    }


# ── Metric Models ───────────────────────────────────────────────────────────────

def model_pipeline_coverage(opps: pd.DataFrame, quota: float = 5_000_000) -> dict:
    """
    SQL equivalent:
        SELECT SUM(pipeline_value) / :quota AS pipeline_coverage
        FROM opportunities
        WHERE stage NOT IN ('Closed Won', 'Closed Lost')
    """
    open_pipeline = opps[~opps["stage"].isin(["Closed Won", "Closed Lost"])]["pipeline_value"].sum()
    return {
        "metric_name": "Pipeline Coverage",
        "segment": "All",
        "metric_value": round(open_pipeline / quota, 2),
        "date": datetime.today().strftime("%Y-%m-%d"),
    }


def model_win_rate(opps: pd.DataFrame, segment_col: str = None) -> list:
    """
    SQL equivalent:
        SELECT
            SUM(CASE WHEN stage = 'Closed Won' THEN 1 ELSE 0 END)::float
            / NULLIF(SUM(CASE WHEN stage IN ('Closed Won','Closed Lost') THEN 1 ELSE 0 END),0)
            AS win_rate
        FROM opportunities
    """
    closed = opps[opps["stage"].isin(["Closed Won", "Closed Lost"])].copy()
    if len(closed) == 0:
        return []

    def _wr(df):
        won = (df["stage"] == "Closed Won").sum()
        total = len(df)
        return round(won / total, 4) if total else 0

    results = []
    if segment_col and segment_col in opps.columns:
        merged = opps.merge(pd.read_csv(os.path.join(RAW_DIR, "accounts.csv"))[["account_id", segment_col]], on="account_id", how="left")
        closed_seg = merged[merged["stage"].isin(["Closed Won", "Closed Lost"])]
        for seg_val, grp in closed_seg.groupby(segment_col):
            results.append({
                "metric_name": "Win Rate",
                "segment": str(seg_val),
                "metric_value": _wr(grp),
                "date": datetime.today().strftime("%Y-%m-%d"),
            })
    else:
        results.append({
            "metric_name": "Win Rate",
            "segment": "All",
            "metric_value": _wr(closed),
            "date": datetime.today().strftime("%Y-%m-%d"),
        })
    return results


def model_average_deal_size(opps: pd.DataFrame) -> dict:
    """Average contract value of Closed Won opportunities."""
    won = opps[opps["stage"] == "Closed Won"]
    avg = round(won["pipeline_value"].mean(), 2) if len(won) else 0
    return {
        "metric_name": "Average Deal Size",
        "segment": "All",
        "metric_value": avg,
        "date": datetime.today().strftime("%Y-%m-%d"),
    }


def model_sales_cycle_length(opps: pd.DataFrame) -> dict:
    """
    SQL equivalent:
        SELECT AVG(DATEDIFF('day', created_date, close_date)) AS avg_cycle_days
        FROM opportunities WHERE stage = 'Closed Won'
    """
    won = opps[opps["stage"] == "Closed Won"].copy()
    won["created_date"] = pd.to_datetime(won["created_date"])
    won["close_date"] = pd.to_datetime(won["close_date"])
    won["cycle_days"] = (won["close_date"] - won["created_date"]).dt.days
    avg_days = round(won["cycle_days"].mean(), 1) if len(won) else 0
    return {
        "metric_name": "Sales Cycle Length (days)",
        "segment": "All",
        "metric_value": avg_days,
        "date": datetime.today().strftime("%Y-%m-%d"),
    }


def model_net_revenue_retention(subs: pd.DataFrame) -> dict:
    """
    Simplified NRR:
        (Base ARR + Expansion ARR) / Base ARR
    """
    base_arr = subs["contract_value"].sum()
    expansion = subs[subs["expansion_flag"] == 1]["contract_value"].sum()
    simulated_churn = base_arr * 0.08  # 8% annual churn assumption
    nrr = round((base_arr + expansion * 0.3 - simulated_churn) / base_arr, 4)
    return {
        "metric_name": "Net Revenue Retention",
        "segment": "All",
        "metric_value": nrr,
        "date": datetime.today().strftime("%Y-%m-%d"),
    }


def model_product_attach_rate(usage: pd.DataFrame, accounts: pd.DataFrame) -> dict:
    """% of accounts using more than one product."""
    product_counts = usage.groupby("account_id")["product_name"].nunique().reset_index()
    product_counts.columns = ["account_id", "product_count"]
    multi = (product_counts["product_count"] > 1).sum()
    attach_rate = round(multi / len(accounts), 4)
    return {
        "metric_name": "Product Attach Rate",
        "segment": "All",
        "metric_value": attach_rate,
        "date": datetime.today().strftime("%Y-%m-%d"),
    }


def model_seat_expansion_rate(subs: pd.DataFrame) -> dict:
    """% of accounts with expansion flag."""
    rate = round(subs["expansion_flag"].mean(), 4)
    return {
        "metric_name": "Seat Expansion Rate",
        "segment": "All",
        "metric_value": rate,
        "date": datetime.today().strftime("%Y-%m-%d"),
    }


def model_lead_conversion_rate(leads: pd.DataFrame) -> list:
    """Conversion rate overall and by source."""
    results = []
    overall = round(leads["converted_flag"].mean(), 4)
    results.append({
        "metric_name": "Lead Conversion Rate",
        "segment": "All",
        "metric_value": overall,
        "date": datetime.today().strftime("%Y-%m-%d"),
    })
    for source, grp in leads.groupby("source"):
        results.append({
            "metric_name": "Lead Conversion Rate",
            "segment": source,
            "metric_value": round(grp["converted_flag"].mean(), 4),
            "date": datetime.today().strftime("%Y-%m-%d"),
        })
    return results


def model_usage_health(usage: pd.DataFrame) -> list:
    """Flag accounts with no activity in the last 30 days as at-risk."""
    cutoff = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    usage["last_active_date"] = usage["last_active_date"].astype(str)
    at_risk = usage[usage["last_active_date"] < cutoff]["account_id"].nunique()
    total = usage["account_id"].nunique()
    return [{
        "metric_name": "Usage At-Risk Rate",
        "segment": "All",
        "metric_value": round(at_risk / total, 4),
        "date": datetime.today().strftime("%Y-%m-%d"),
    }]


# ── Master compute function ─────────────────────────────────────────────────────

def compute_all_metrics() -> pd.DataFrame:
    """Run all metric models and return a unified metrics table."""
    tables = load_data()
    accts = tables["accounts"]
    opps = tables["opportunities"]
    usage = tables["product_usage"]
    leads = tables["marketing_leads"]
    subs = tables["subscriptions"]

    rows = []
    rows.append(model_pipeline_coverage(opps))
    rows.extend(model_win_rate(opps))
    rows.extend(model_win_rate(opps, segment_col="region"))
    rows.append(model_average_deal_size(opps))
    rows.append(model_sales_cycle_length(opps))
    rows.append(model_net_revenue_retention(subs))
    rows.append(model_product_attach_rate(usage, accts))
    rows.append(model_seat_expansion_rate(subs))
    rows.extend(model_lead_conversion_rate(leads))
    rows.extend(model_usage_health(usage))

    metrics_df = pd.DataFrame(rows)
    out_path = os.path.join(PROCESSED_DIR, "metrics.csv")
    metrics_df.to_csv(out_path, index=False)
    print(f"✅ metrics.csv — {len(metrics_df)} metrics computed → {out_path}")
    return metrics_df


if __name__ == "__main__":
    df = compute_all_metrics()
    print("\n📊 Metrics Table:\n")
    print(df.to_string(index=False))
