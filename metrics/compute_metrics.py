"""
Phase 2: dbt-style metrics layer.
Computes all key SaaS growth metrics from raw CSV data using Pandas + SQL-style transforms.
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)


def _metric(name: str, value: float, segment: str = "All") -> dict:
    return {
        "metric_name": name,
        "segment": segment,
        "metric_value": value,
        "date": datetime.today().strftime("%Y-%m-%d"),
    }


def load_data():
    """Load all raw tables."""
    tables = {}
    files = {
        "accounts": "accounts.csv",
        "opportunities": "opportunities.csv",
        "product_usage": "product_usage.csv",
        "marketing_leads": "marketing_leads.csv",
        "subscriptions": "subscription_revenue.csv",
    }
    for key, filename in files.items():
        path = os.path.join(RAW_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing data file: {path}. Run scripts/generate_data.py first.")
        tables[key] = pd.read_csv(path)
        logger.debug("Loaded %s: %d rows", filename, len(tables[key]))
    return tables


# ── Metric Models ───────────────────────────────────────────────────────────────

def model_pipeline_coverage(opps: pd.DataFrame, quota: float = 5_000_000) -> dict:
    """
    SQL equivalent:
        SELECT SUM(pipeline_value) / :quota AS pipeline_coverage
        FROM opportunities
        WHERE stage NOT IN ('Closed Won', 'Closed Lost')
    """
    if len(opps) == 0:
        logger.warning("No opportunities data — pipeline coverage defaulting to 0")
        return _metric("Pipeline Coverage", 0.0)
    open_pipeline = opps[~opps["stage"].isin(["Closed Won", "Closed Lost"])]["pipeline_value"].sum()
    return _metric("Pipeline Coverage", round(open_pipeline / quota, 2))


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
        logger.warning("No closed opportunities — win rate not computable")
        return []

    def _wr(df):
        won = (df["stage"] == "Closed Won").sum()
        total = len(df)
        return round(won / total, 4) if total else 0

    results = []
    if segment_col and segment_col in opps.columns:
        accounts_path = os.path.join(RAW_DIR, "accounts.csv")
        accounts = pd.read_csv(accounts_path)[[col for col in ["account_id", segment_col] if col in pd.read_csv(accounts_path).columns]]
        merged = opps.merge(accounts, on="account_id", how="left")
        closed_seg = merged[merged["stage"].isin(["Closed Won", "Closed Lost"])]
        for seg_val, grp in closed_seg.groupby(segment_col):
            results.append(_metric("Win Rate", _wr(grp), str(seg_val)))
    else:
        results.append(_metric("Win Rate", _wr(closed)))
    return results


def model_average_deal_size(opps: pd.DataFrame) -> dict:
    """Average contract value of Closed Won opportunities."""
    won = opps[opps["stage"] == "Closed Won"]
    if len(won) == 0:
        logger.warning("No Closed Won opportunities — average deal size defaulting to 0")
        return _metric("Average Deal Size", 0.0)
    avg = won["pipeline_value"].mean()
    return _metric("Average Deal Size", round(float(avg), 2) if pd.notna(avg) else 0.0)


def model_sales_cycle_length(opps: pd.DataFrame) -> dict:
    """
    SQL equivalent:
        SELECT AVG(DATEDIFF('day', created_date, close_date)) AS avg_cycle_days
        FROM opportunities WHERE stage = 'Closed Won'
    """
    won = opps[opps["stage"] == "Closed Won"].copy()
    if len(won) == 0:
        return _metric("Sales Cycle Length (days)", 0.0)
    won["created_date"] = pd.to_datetime(won["created_date"])
    won["close_date"] = pd.to_datetime(won["close_date"])
    won["cycle_days"] = (won["close_date"] - won["created_date"]).dt.days
    avg_days = won["cycle_days"].mean()
    return _metric("Sales Cycle Length (days)", round(float(avg_days), 1) if pd.notna(avg_days) else 0.0)


def model_net_revenue_retention(subs: pd.DataFrame) -> dict:
    """
    NRR = (Base ARR + Expansion ARR - Churned ARR) / Base ARR

    Expansion ARR: accounts with expansion_flag=1 are assumed to have grown 20%
    above their base contract (incremental only).
    Churned ARR:   5% of base ARR modeled as churn (no dedicated churn table).

    Standard benchmark: NRR > 120% = best-in-class expansion engine.
    """
    if len(subs) == 0:
        logger.warning("No subscription data — NRR defaulting to 0")
        return _metric("Net Revenue Retention", 0.0)

    base_arr = subs["contract_value"].sum()
    if base_arr == 0:
        logger.warning("Base ARR is zero — NRR defaulting to 0")
        return _metric("Net Revenue Retention", 0.0)

    expansion_base = subs[subs["expansion_flag"] == 1]["contract_value"].sum()
    expansion_arr = expansion_base * 0.20   # 20% incremental uplift on expanding accounts
    churned_arr = base_arr * 0.05           # 5% annual churn (modeled; no churn table)

    nrr = round((base_arr + expansion_arr - churned_arr) / base_arr, 4)
    logger.debug("NRR: base=%.0f expansion=%.0f churn=%.0f nrr=%.4f", base_arr, expansion_arr, churned_arr, nrr)
    return _metric("Net Revenue Retention", nrr)


def model_product_attach_rate(usage: pd.DataFrame, accounts: pd.DataFrame) -> dict:
    """% of accounts using more than one product."""
    if len(accounts) == 0 or len(usage) == 0:
        return _metric("Product Attach Rate", 0.0)
    product_counts = usage.groupby("account_id")["product_name"].nunique().reset_index()
    product_counts.columns = ["account_id", "product_count"]
    multi = (product_counts["product_count"] > 1).sum()
    attach_rate = round(multi / len(accounts), 4)
    return _metric("Product Attach Rate", attach_rate)


def model_seat_expansion_rate(subs: pd.DataFrame) -> dict:
    """% of accounts with expansion flag."""
    if len(subs) == 0:
        return _metric("Seat Expansion Rate", 0.0)
    rate = subs["expansion_flag"].mean()
    return _metric("Seat Expansion Rate", round(float(rate), 4) if pd.notna(rate) else 0.0)


def model_lead_conversion_rate(leads: pd.DataFrame) -> list:
    """Conversion rate overall and by source."""
    if len(leads) == 0:
        return [_metric("Lead Conversion Rate", 0.0)]
    results = []
    overall = leads["converted_flag"].mean()
    results.append(_metric("Lead Conversion Rate", round(float(overall), 4) if pd.notna(overall) else 0.0))
    for source, grp in leads.groupby("source"):
        val = grp["converted_flag"].mean()
        results.append(_metric("Lead Conversion Rate", round(float(val), 4) if pd.notna(val) else 0.0, source))
    return results


def model_usage_health(usage: pd.DataFrame) -> list:
    """Flag accounts with no activity in the last 30 days as at-risk."""
    if len(usage) == 0:
        return [_metric("Usage At-Risk Rate", 0.0)]
    cutoff = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    usage = usage.copy()
    usage["last_active_date"] = usage["last_active_date"].astype(str)
    total = usage["account_id"].nunique()
    if total == 0:
        return [_metric("Usage At-Risk Rate", 0.0)]
    at_risk = usage[usage["last_active_date"] < cutoff]["account_id"].nunique()
    return [_metric("Usage At-Risk Rate", round(at_risk / total, 4))]


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
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    df = compute_all_metrics()
    print("\n📊 Metrics Table:\n")
    print(df.to_string(index=False))
