"""
Automated alert system: detects anomalies in growth metrics.
Compares current period vs. a simulated previous period.
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def simulate_previous_metrics(current_df: pd.DataFrame, noise_pct: float = 0.15) -> pd.DataFrame:
    """
    Simulate a previous period by adding random noise to current metrics.
    In production, you'd load actual historical metrics from a database.
    """
    prev = current_df.copy()
    noise = np.random.uniform(-noise_pct, noise_pct, size=len(prev))
    prev["metric_value"] = prev["metric_value"] * (1 + noise)
    prev["metric_value"] = prev["metric_value"].round(4)
    return prev


def compute_alerts(threshold_pct: float = 0.15) -> list[dict]:
    """
    Compare current vs. previous period metrics.
    Returns list of alert dicts for metrics that changed more than threshold_pct.
    """
    metrics_path = os.path.join(PROCESSED_DIR, "metrics.csv")
    if not os.path.exists(metrics_path):
        logger.warning("Metrics file not found at %s", metrics_path)
        return [{"error": "Metrics not found. Run metrics/compute_metrics.py first."}]

    current = pd.read_csv(metrics_path)
    if current.empty:
        logger.warning("Metrics file is empty")
        return []

    previous = simulate_previous_metrics(current)

    alerts = []
    for _, row in current.iterrows():
        metric = row["metric_name"]
        segment = row["segment"]
        curr_val = row["metric_value"]

        if pd.isna(curr_val):
            logger.debug("Skipping %s/%s — current value is NaN", metric, segment)
            continue

        prev_row = previous[
            (previous["metric_name"] == metric) & (previous["segment"] == segment)
        ]
        if len(prev_row) == 0:
            continue
        prev_val = prev_row.iloc[0]["metric_value"]

        if pd.isna(prev_val) or prev_val == 0:
            continue

        change_pct = (curr_val - prev_val) / abs(prev_val)

        if abs(change_pct) >= threshold_pct:
            direction = "📈" if change_pct > 0 else "📉"
            is_good = _is_positive_change(metric, change_pct)
            severity = _compute_severity(abs(change_pct), is_good)

            alerts.append({
                "metric": metric,
                "segment": segment,
                "current_value": round(float(curr_val), 4),
                "previous_value": round(float(prev_val), 4),
                "change_pct": round(change_pct * 100, 1),
                "direction": direction,
                "is_positive": is_good,
                "severity": severity,
                "recommended_action": _get_recommendation(metric, change_pct),
                "timestamp": datetime.now().isoformat(),
            })

    # Sort: high severity first, then bad changes before good ones
    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    alerts.sort(key=lambda x: (severity_order.get(x["severity"], 3), x["is_positive"]))
    logger.info("Alert check complete: %d alerts found (threshold=%.0f%%)", len(alerts), threshold_pct * 100)
    return alerts


def _is_positive_change(metric_name: str, change_pct: float) -> bool:
    """Determine if a metric movement is favorable (True) or unfavorable (False)."""
    negative_metrics = ["Usage At-Risk Rate", "Sales Cycle Length (days)"]
    if any(neg.lower() in metric_name.lower() for neg in negative_metrics):
        return change_pct < 0  # decrease is good for risk/cycle metrics
    return change_pct > 0


def _compute_severity(abs_change: float, is_positive: bool) -> str:
    """
    Severity is driven by whether the change is unfavorable.
    Unfavorable large changes = High; unfavorable moderate = Medium.
    Favorable changes are generally Low unless surprisingly large (High).
    """
    if not is_positive:
        if abs_change >= 0.25:
            return "High"
        elif abs_change >= 0.15:
            return "Medium"
        return "Low"
    else:
        if abs_change >= 0.25:
            return "High"   # unusually large positive swing — worth noting
        return "Low"


def _get_recommendation(metric_name: str, change_pct: float) -> str:
    name = metric_name.lower()
    up = change_pct > 0

    recommendations = {
        "win rate": "Review lost deal analysis; update qualification criteria; consider additional sales enablement" if not up else "Document what's working; replicate winning patterns across team",
        "pipeline coverage": "Increase outbound activity; run a pipeline generation campaign; review lead routing" if not up else "Validate quality of pipeline; ensure accurate stage progression",
        "net revenue retention": "Audit at-risk accounts immediately; schedule executive sponsor calls; review CSM assignments" if not up else "Identify expansion patterns and scale the playbook",
        "product attach rate": "Launch cross-sell campaign; train CSMs on module positioning; create bundled pricing incentive" if not up else "Capture case studies from multi-product accounts for social proof",
        "seat expansion": "Trigger seat expansion playbook at 75% utilization; review CSM QBR cadence" if not up else "Identify expansion-ready accounts and fast-track expansion proposals",
        "usage at-risk": "Immediately activate at-risk playbook; assign CSMs to inactive accounts" if up else "Continue monitoring; identify successful re-engagement tactics",
        "sales cycle": "Review deal stages for bottlenecks; add mutual action plans; involve executive sponsors earlier" if up else "Analyze what's driving faster cycles and replicate",
        "average deal size": "Re-evaluate pricing strategy; review discounting patterns; focus on enterprise segment" if not up else "Identify which segments or products are driving higher ACV",
        "lead conversion": "Review lead scoring model; audit top-of-funnel messaging; A/B test landing pages" if not up else "Scale highest-converting channels; analyze what changed",
    }

    for key, rec in recommendations.items():
        if key in name:
            return rec
    return "Investigate this metric change with the relevant team and determine appropriate action."


def format_alerts_for_display(alerts: list[dict]) -> str:
    """Format alerts as human-readable text."""
    if not alerts:
        return "✅ All metrics within normal range. No alerts triggered."

    lines = [f"🚨 {len(alerts)} metric alert(s) detected\n"]
    for a in alerts:
        sign = "+" if a["change_pct"] > 0 else ""
        color = "🟢" if a["is_positive"] else "🔴"
        lines.append(f"""
{'─' * 60}
{a['direction']} **{a['metric']}** — Segment: {a['segment']}
{color} Priority: {a['severity']}
Change: {sign}{a['change_pct']}% ({a['previous_value']} → {a['current_value']})
Action: {a['recommended_action']}
""")
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    alerts = compute_alerts()
    print(format_alerts_for_display(alerts))
