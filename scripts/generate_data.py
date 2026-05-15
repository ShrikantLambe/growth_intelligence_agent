"""
Phase 1: Generate realistic simulated SaaS datasets.
Run: python scripts/generate_data.py

Distribution targets (B2B SaaS benchmarks):
  Win rate:        ~29% overall  (NA 30%, EMEA 26%, APAC 24%, LATAM 22%)
  Pipeline:        NA 54%, EMEA 21%, APAC 15%, LATAM 10%
  NRR:             ~112%
  Usage at-risk:   ~17%  (always relative to today's date)
  Sales cycle:     65–90 days median
  Product attach:  ~42%
  Seat expansion:  ~22%
"""

import os
import random
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

TODAY = datetime.today()

# ── Constants ──────────────────────────────────────────────────────────────────
INDUSTRIES = [
    "Technology", "Financial Services", "Healthcare", "Manufacturing",
    "Retail & E-commerce", "Media & Entertainment", "Public Sector",
]
# Weighted: Tech + FS largest (mirrors real ICP)
INDUSTRY_WEIGHTS = [28, 22, 16, 12, 10, 7, 5]

REGIONS = ["North America", "EMEA", "APAC", "LATAM"]
# NA-heavy pipeline per plan
REGION_WEIGHTS = [55, 22, 15, 8]

# Win rate by region (fraction of closed deals won)
REGION_WIN_RATES = {
    "North America": 0.30,
    "EMEA":          0.26,
    "APAC":          0.24,
    "LATAM":         0.22,
}

EMPLOYEE_SIZES = ["1-50", "51-200", "201-500", "501-2000", "2000+"]
# SMB-skewed
EMPLOYEE_WEIGHTS = [15, 30, 25, 20, 10]

PRODUCTS = ["Core Platform", "Analytics Add-on", "API Access", "Enterprise Suite", "Compliance Module"]
LEAD_SOURCES = ["Organic Search", "Paid Search", "LinkedIn", "Referral", "Event", "Cold Outreach"]
CAMPAIGNS = ["Q1 Spring Push", "Product Launch", "Brand Awareness", "Competitor Conquest", "Retention Drive"]

STAGES_OPEN   = ["Prospecting", "Discovery", "Demo", "Proposal", "Negotiation"]
STAGE_WEIGHTS_OPEN = [28, 24, 20, 16, 12]   # funnel-shaped: most deals at top


def _date(days_ago_max: int, days_ago_min: int = 0) -> str:
    """Return a date string between days_ago_min and days_ago_max days before today."""
    days = random.randint(days_ago_min, days_ago_max)
    return (TODAY - timedelta(days=days)).strftime("%Y-%m-%d")


# ── 1. Accounts ────────────────────────────────────────────────────────────────
def generate_accounts(n: int = 300) -> pd.DataFrame:
    """300 accounts weighted by region and industry to match target pipeline mix."""
    records = []
    for i in range(1, n + 1):
        region   = random.choices(REGIONS,        weights=REGION_WEIGHTS)[0]
        industry = random.choices(INDUSTRIES,     weights=INDUSTRY_WEIGHTS)[0]
        emp_size = random.choices(EMPLOYEE_SIZES, weights=EMPLOYEE_WEIGHTS)[0]
        records.append({
            "account_id":   f"ACC{i:04d}",
            "company_name": fake.company(),
            "industry":     industry,
            "employee_size": emp_size,
            "region":       region,
            "created_date": _date(730, 30),
            "tier":         random.choices(["Enterprise", "Mid-Market", "SMB"],
                                           weights=[20, 35, 45])[0],
        })
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(RAW_DIR, "accounts.csv"), index=False)
    print(f"✅ accounts.csv — {len(df)} rows")
    return df


# ── 2. Opportunities ───────────────────────────────────────────────────────────
def generate_opportunities(accounts_df: pd.DataFrame, n: int = 800) -> pd.DataFrame:
    """
    800 deals with realistic funnel shape and per-region win rates.

    Open stage distribution (funnel-shaped):
      Prospecting 28% > Discovery 24% > Demo 20% > Proposal 16% > Negotiation 12%

    Closed deals: ~22% of total → win rate follows REGION_WIN_RATES per account region.
    Deal sizes: log-normal, median ~$48k, range $18k–$220k.
    Sales cycle (closed won): 55–100 days.
    """
    records = []
    opp_idx = 1

    # Pre-assign closed vs open so totals are predictable
    n_closed  = int(n * 0.22)   # ~176 closed deals
    n_open    = n - n_closed    # ~624 open deals

    acct_lookup = accounts_df.set_index("account_id")[["region", "industry", "tier"]].to_dict("index")
    account_ids = accounts_df["account_id"].tolist()

    def _deal_value(tier: str) -> int:
        """Log-normal deal size tuned per tier."""
        mu_map = {"Enterprise": 11.3, "Mid-Market": 10.7, "SMB": 10.1}
        return max(15_000, round(np.random.lognormal(mu_map.get(tier, 10.7), 0.45)))

    # Open deals
    for _ in range(n_open):
        acct_id = random.choice(account_ids)
        acct    = acct_lookup[acct_id]
        stage   = random.choices(STAGES_OPEN, weights=STAGE_WEIGHTS_OPEN)[0]
        created_days_ago  = random.randint(14, 270)
        close_days_offset = random.randint(14, 90)
        records.append({
            "opportunity_id": f"OPP{opp_idx:05d}",
            "account_id":     acct_id,
            "stage":          stage,
            "pipeline_value": _deal_value(acct["tier"]),
            "created_date":   _date(created_days_ago, created_days_ago),
            "close_date":     (TODAY - timedelta(days=created_days_ago) + timedelta(days=close_days_offset)).strftime("%Y-%m-%d"),
            "win_flag":       None,
        })
        opp_idx += 1

    # Closed deals — win/loss driven by regional win rates
    for _ in range(n_closed):
        acct_id  = random.choice(account_ids)
        acct     = acct_lookup[acct_id]
        wr       = REGION_WIN_RATES.get(acct["region"], 0.27)
        won      = random.random() < wr
        stage    = "Closed Won" if won else "Closed Lost"

        # Sales cycle: 55–110 days for won, 20–80 for lost
        if won:
            cycle_days = random.randint(55, 110)
        else:
            cycle_days = random.randint(20, 80)

        closed_days_ago  = random.randint(7, 360)
        created_days_ago = closed_days_ago + cycle_days

        records.append({
            "opportunity_id": f"OPP{opp_idx:05d}",
            "account_id":     acct_id,
            "stage":          stage,
            "pipeline_value": _deal_value(acct["tier"]),
            "created_date":   _date(created_days_ago, created_days_ago),
            "close_date":     _date(closed_days_ago, closed_days_ago),
            "win_flag":       int(won),
        })
        opp_idx += 1

    df = pd.DataFrame(records)
    df.to_csv(os.path.join(RAW_DIR, "opportunities.csv"), index=False)
    print(f"✅ opportunities.csv — {len(df)} rows")
    return df


# ── 3. Product Usage ───────────────────────────────────────────────────────────
def generate_product_usage(accounts_df: pd.DataFrame) -> pd.DataFrame:
    """
    Product usage with realistic at-risk distribution.
    ~17% of accounts flagged at-risk (last active 31–90 days ago).
    Dates always relative to TODAY to avoid stale data issues.
    """
    account_ids = accounts_df["account_id"].tolist()
    random.shuffle(account_ids)

    n_total   = len(account_ids)
    n_at_risk = int(n_total * 0.17)  # ~17% at-risk
    at_risk_set = set(account_ids[:n_at_risk])

    records = []
    for acct_id in account_ids:
        n_products = random.choices([1, 2, 3, 4], weights=[58, 28, 11, 3])[0]
        chosen = random.sample(PRODUCTS, min(n_products, len(PRODUCTS)))
        for product in chosen:
            if acct_id in at_risk_set:
                last_active = _date(85, 31)   # inactive 31–85 days
            else:
                last_active = _date(22, 0)    # active within last 22 days
            records.append({
                "account_id":     acct_id,
                "product_name":   product,
                "active_users":   random.randint(2, 600),
                "usage_events":   random.randint(50, 60_000),
                "last_active_date": last_active,
            })
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(RAW_DIR, "product_usage.csv"), index=False)
    print(f"✅ product_usage.csv — {len(df)} rows  ({n_at_risk} at-risk accounts)")
    return df


# ── 4. Marketing Leads ─────────────────────────────────────────────────────────
def generate_marketing_leads(n: int = 2000) -> pd.DataFrame:
    """2 000 leads, ~18% conversion overall with source-level variance."""
    CONV_BY_SOURCE = {
        "Referral":       0.32,
        "Event":          0.25,
        "Organic Search": 0.20,
        "LinkedIn":       0.16,
        "Paid Search":    0.14,
        "Cold Outreach":  0.08,
    }
    records = []
    for i in range(1, n + 1):
        source    = random.choices(LEAD_SOURCES)[0]
        converted = random.random() < CONV_BY_SOURCE.get(source, 0.15)
        records.append({
            "lead_id":        f"LEAD{i:05d}",
            "source":         source,
            "campaign":       random.choice(CAMPAIGNS),
            "created_date":   _date(365, 0),
            "converted_flag": int(converted),
        })
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(RAW_DIR, "marketing_leads.csv"), index=False)
    print(f"✅ marketing_leads.csv — {len(df)} rows  (conv={df['converted_flag'].mean():.1%})")
    return df


# ── 5. Subscription Revenue ────────────────────────────────────────────────────
def generate_subscriptions(accounts_df: pd.DataFrame) -> pd.DataFrame:
    """
    Contract values calibrated so NRR ≈ 112%.

    compute_metrics.py formula:
      NRR = (base + expansion*0.20 - base*0.05) / base
          = 1 + (expand_ARR / base_ARR)*0.20 - 0.05

    Target NRR 112%  →  (expand_ARR / base_ARR)*0.20 = 0.17
                       →  expand_ARR / base_ARR ≈ 0.85

    Achieved by:
      - 60% of accounts have expansion_flag=1
      - Expanding accounts draw from a higher ARR distribution (larger contracts)
      - Non-expanding accounts draw from a lower ARR distribution
    """
    records = []
    for _, row in accounts_df.iterrows():
        expanding = random.random() < 0.25
        if expanding:
            # Higher ARR for expanding accounts (~$45k median) — drives NRR via large expansion base
            contract_value = max(15_000, round(np.random.lognormal(10.7, 0.50)))
        else:
            # Smaller ARR for stable accounts (~$14k median)
            contract_value = max(5_000, round(np.random.lognormal(9.6, 0.45)))

        renewal_days = random.randint(15, 400)
        records.append({
            "account_id":     row["account_id"],
            "contract_value": contract_value,
            "renewal_date":   (TODAY + timedelta(days=renewal_days)).strftime("%Y-%m-%d"),
            "expansion_flag": int(expanding),
        })
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(RAW_DIR, "subscription_revenue.csv"), index=False)

    # Report expected NRR
    base = df["contract_value"].sum()
    exp  = df[df["expansion_flag"] == 1]["contract_value"].sum()
    expected_nrr = 1 + (exp / base) * 0.20 - 0.05
    print(f"✅ subscription_revenue.csv — {len(df)} rows  "
          f"(expand_rate={df['expansion_flag'].mean():.0%}  "
          f"expand_ARR_share={exp/base:.0%}  expected_NRR≈{expected_nrr:.1%})")
    return df


# ── 6. Metrics History (8 quarters) ───────────────────────────────────────────
def generate_metrics_history() -> pd.DataFrame:
    """
    8 quarters of key metric values for trend/delta displays on KPI cards.
    Q1 2024 → Q4 2025, with realistic quarter-over-quarter drift.
    """
    quarters = [
        "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4",
        "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4",
    ]
    # Base values (Q1 2024) + quarterly drift deltas
    base_and_drift = {
        "Win Rate":                  (0.24, +0.006),
        "Pipeline Coverage":         (3.4,  +0.12),
        "Net Revenue Retention":     (1.07, +0.009),
        "Average Deal Size":         (44_000, +800),
        "Product Attach Rate":       (0.35, +0.009),
        "Seat Expansion Rate":       (0.19, +0.004),
        "Usage At-Risk Rate":        (0.24, -0.010),  # improving (declining = good)
        "Sales Cycle Length (days)": (88,   -2.5),    # improving (declining = good)
        "Lead Conversion Rate":      (0.15, +0.004),
    }
    records = []
    for metric, (base_val, drift) in base_and_drift.items():
        val = base_val
        for q in quarters:
            noise = np.random.normal(0, abs(drift) * 0.5)
            records.append({
                "metric_name":  metric,
                "quarter":      q,
                "metric_value": round(val + noise, 4 if val < 10 else 0),
            })
            val += drift
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(RAW_DIR, "metrics_history.csv"), index=False)
    print(f"✅ metrics_history.csv — {len(df)} rows  (8 quarters × {len(base_and_drift)} metrics)")
    return df


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n🚀 Generating SaaS datasets (seed={SEED})...\n")
    accounts = generate_accounts(300)
    generate_opportunities(accounts, 800)
    generate_product_usage(accounts)
    generate_marketing_leads(2000)
    generate_subscriptions(accounts)
    generate_metrics_history()
    print(f"\n✅ All datasets written to: {RAW_DIR}\n")
