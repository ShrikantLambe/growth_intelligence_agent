"""
Phase 1: Generate realistic simulated SaaS datasets.
Run: python scripts/generate_data.py
"""

import os
import random
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()
random.seed(42)
np.random.seed(42)

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

INDUSTRIES = ["FinTech", "HealthTech", "EdTech", "RetailTech", "HRTech", "LegalTech"]
REGIONS = ["North America", "EMEA", "APAC", "LATAM"]
EMPLOYEE_SIZES = ["1-50", "51-200", "201-500", "501-2000", "2000+"]
PRODUCTS = ["Core Platform", "Analytics Add-on", "API Access", "Enterprise Suite", "Compliance Module"]
LEAD_SOURCES = ["Organic Search", "Paid Search", "LinkedIn", "Referral", "Event", "Cold Outreach"]
CAMPAIGNS = ["Q1 Spring Push", "Product Launch", "Brand Awareness", "Competitor Conquest", "Retention Drive"]
STAGES = ["Prospecting", "Discovery", "Demo", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]


def date_range_random(start_days_ago: int, end_days_ago: int = 0) -> str:
    days = random.randint(end_days_ago, start_days_ago)
    return (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")


# ── 1. Accounts ────────────────────────────────────────────────────────────────
def generate_accounts(n=200):
    records = []
    for i in range(1, n + 1):
        records.append({
            "account_id": f"ACC{i:04d}",
            "company_name": fake.company(),
            "industry": random.choice(INDUSTRIES),
            "employee_size": random.choice(EMPLOYEE_SIZES),
            "region": random.choice(REGIONS),
            "created_date": date_range_random(730, 30),
        })
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(RAW_DIR, "accounts.csv"), index=False)
    print(f"✅ accounts.csv — {len(df)} rows")
    return df


# ── 2. Opportunities ───────────────────────────────────────────────────────────
def generate_opportunities(accounts_df, n=600):
    account_ids = accounts_df["account_id"].tolist()
    records = []
    for i in range(1, n + 1):
        created_days_ago = random.randint(30, 365)
        close_days_offset = random.randint(14, 120)
        stage = random.choices(
            STAGES,
            weights=[10, 15, 20, 15, 10, 20, 10]
        )[0]
        win_flag = 1 if stage == "Closed Won" else (0 if stage == "Closed Lost" else None)
        pipeline_value = round(random.lognormvariate(10.5, 0.8))  # realistic deal sizes

        records.append({
            "opportunity_id": f"OPP{i:05d}",
            "account_id": random.choice(account_ids),
            "stage": stage,
            "pipeline_value": pipeline_value,
            "close_date": (datetime.today() - timedelta(days=created_days_ago) + timedelta(days=close_days_offset)).strftime("%Y-%m-%d"),
            "created_date": (datetime.today() - timedelta(days=created_days_ago)).strftime("%Y-%m-%d"),
            "win_flag": win_flag,
        })
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(RAW_DIR, "opportunities.csv"), index=False)
    print(f"✅ opportunities.csv — {len(df)} rows")
    return df


# ── 3. Product Usage ───────────────────────────────────────────────────────────
def generate_product_usage(accounts_df):
    account_ids = accounts_df["account_id"].tolist()
    records = []
    for account_id in account_ids:
        n_products = random.choices([1, 2, 3], weights=[55, 30, 15])[0]
        chosen = random.sample(PRODUCTS, n_products)
        for product in chosen:
            records.append({
                "account_id": account_id,
                "product_name": product,
                "active_users": random.randint(1, 500),
                "usage_events": random.randint(10, 50000),
                "last_active_date": date_range_random(60, 0),
            })
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(RAW_DIR, "product_usage.csv"), index=False)
    print(f"✅ product_usage.csv — {len(df)} rows")
    return df


# ── 4. Marketing Leads ─────────────────────────────────────────────────────────
def generate_marketing_leads(n=1500):
    records = []
    for i in range(1, n + 1):
        converted = random.random() < 0.18  # 18% conversion rate
        records.append({
            "lead_id": f"LEAD{i:05d}",
            "source": random.choice(LEAD_SOURCES),
            "campaign": random.choice(CAMPAIGNS),
            "created_date": date_range_random(365, 0),
            "converted_flag": int(converted),
        })
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(RAW_DIR, "marketing_leads.csv"), index=False)
    print(f"✅ marketing_leads.csv — {len(df)} rows")
    return df


# ── 5. Subscription Revenue ────────────────────────────────────────────────────
def generate_subscriptions(accounts_df):
    records = []
    for _, row in accounts_df.iterrows():
        contract_value = round(random.lognormvariate(9.5, 0.7))
        expansion = random.random() < 0.25  # 25% expanded
        renewal_days = random.randint(30, 365)
        records.append({
            "account_id": row["account_id"],
            "contract_value": contract_value,
            "renewal_date": (datetime.today() + timedelta(days=renewal_days)).strftime("%Y-%m-%d"),
            "expansion_flag": int(expansion),
        })
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(RAW_DIR, "subscription_revenue.csv"), index=False)
    print(f"✅ subscription_revenue.csv — {len(df)} rows")
    return df


if __name__ == "__main__":
    print("\n🚀 Generating SaaS datasets...\n")
    accounts = generate_accounts(200)
    generate_opportunities(accounts, 600)
    generate_product_usage(accounts)
    generate_marketing_leads(1500)
    generate_subscriptions(accounts)
    print(f"\n✅ All datasets written to: {RAW_DIR}\n")
