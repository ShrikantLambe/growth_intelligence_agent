"""
Phase 6: Streamlit Growth Intelligence Dashboard.
Run: streamlit run ui/app.py
"""

import os
import sys
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, date, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Session state initialization ─────────────────────────────────────────────────
def _init_session_state():
    defaults = {
        "chat_history": [],
        "alerts": None,
        "analysis": None,
        "run_analysis": False,
        "prefill_question": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

_init_session_state()

# ── Page config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Growth Intelligence Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }

    .main { background: #0a0f1e; }
    .block-container { padding: 1.5rem 2rem; max-width: 1400px; }

    .hero-header {
        background: linear-gradient(135deg, #0d1b2a 0%, #1a2744 50%, #0d2137 100%);
        border: 1px solid #1e3a5f;
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .hero-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%);
    }
    .hero-title { font-size: 2rem; font-weight: 700; color: #e2e8f0; margin: 0; }
    .hero-subtitle { color: #64748b; font-size: 0.95rem; margin-top: 0.3rem; }
    .hero-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3);
        color: #4ade80; padding: 4px 12px; border-radius: 20px;
        font-size: 0.78rem; font-weight: 600;
    }
    .filter-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(139,92,246,0.15); border: 1px solid rgba(139,92,246,0.4);
        color: #a78bfa; padding: 3px 10px; border-radius: 20px;
        font-size: 0.72rem; font-weight: 600; margin-left: 8px;
    }

    .metric-card {
        background: linear-gradient(145deg, #111827, #1a2035);
        border: 1px solid #1e293b; border-radius: 12px;
        padding: 1.2rem 1.5rem; position: relative; overflow: hidden;
        transition: border-color 0.2s;
    }
    .metric-card:hover { border-color: #3b82f6; }
    .metric-card.good { border-left: 3px solid #22c55e; }
    .metric-card.warn { border-left: 3px solid #f59e0b; }
    .metric-card.bad  { border-left: 3px solid #ef4444; }
    .metric-label { color: #64748b; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
    .metric-value { color: #f1f5f9; font-size: 1.8rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .metric-target { color: #475569; font-size: 0.72rem; margin-top: 2px; }

    .alert-high { background: rgba(239,68,68,0.05); border: 1px solid rgba(239,68,68,0.3); border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem; }
    .alert-medium { background: rgba(245,158,11,0.05); border: 1px solid rgba(245,158,11,0.3); border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem; }
    .alert-low { background: rgba(59,130,246,0.05); border: 1px solid rgba(59,130,246,0.3); border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem; }

    .chat-container { max-height: 500px; overflow-y: auto; }
    .user-msg { background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2); border-radius: 12px 12px 2px 12px; padding: 0.75rem 1rem; margin: 0.5rem 0; color: #bfdbfe; }
    .agent-msg { background: rgba(30,41,59,0.8); border: 1px solid #1e3a5f; border-radius: 12px 12px 12px 2px; padding: 0.75rem 1rem; margin: 0.5rem 0; color: #e2e8f0; }

    .stSidebar { background: #070d1a !important; }
    section[data-testid="stSidebar"] { background: #070d1a; border-right: 1px solid #1e293b; }

    .stTabs [data-baseweb="tab-list"] { background: transparent; gap: 4px; }
    .stTabs [data-baseweb="tab"] { background: #111827; border: 1px solid #1e293b; border-radius: 8px; color: #64748b; font-weight: 500; }
    .stTabs [aria-selected="true"] { background: #1d4ed8 !important; border-color: #3b82f6 !important; color: white !important; }

    .stButton > button {
        background: linear-gradient(135deg, #1d4ed8, #2563eb);
        color: white; border: none; border-radius: 8px;
        font-weight: 600; font-family: 'Space Grotesk', sans-serif;
        padding: 0.5rem 1.5rem; transition: all 0.2s;
    }
    .stButton > button:hover { background: linear-gradient(135deg, #2563eb, #3b82f6); transform: translateY(-1px); }

    .stTextInput > div > div > input {
        background: #111827; border: 1px solid #1e293b;
        color: #e2e8f0; border-radius: 8px; font-family: 'Space Grotesk', sans-serif;
    }
    .stTextInput > div > div > input:focus { border-color: #3b82f6; }
</style>
""", unsafe_allow_html=True)


# ── Data loading helpers ─────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")

@st.cache_data(ttl=300)
def load_accounts():
    path = os.path.join(DATA_DIR, "data", "raw", "accounts.csv")
    return pd.read_csv(path) if os.path.exists(path) else None

@st.cache_data(ttl=300)
def load_opportunities():
    path = os.path.join(DATA_DIR, "data", "raw", "opportunities.csv")
    return pd.read_csv(path) if os.path.exists(path) else None

@st.cache_data(ttl=300)
def load_usage():
    path = os.path.join(DATA_DIR, "data", "raw", "product_usage.csv")
    return pd.read_csv(path) if os.path.exists(path) else None

@st.cache_data(ttl=300)
def load_subscriptions():
    path = os.path.join(DATA_DIR, "data", "raw", "subscription_revenue.csv")
    return pd.read_csv(path) if os.path.exists(path) else None

@st.cache_data(ttl=300)
def load_metrics():
    path = os.path.join(DATA_DIR, "data", "processed", "metrics.csv")
    return pd.read_csv(path) if os.path.exists(path) else None

def get_metric_val(df, name, segment="All"):
    if df is None:
        return None
    row = df[(df["metric_name"] == name) & (df["segment"] == segment)]
    return row.iloc[0]["metric_value"] if len(row) else None


# ── Filter application helpers ────────────────────────────────────────────────────

def apply_account_filter(accounts_df, regions, industries, sizes):
    """Return account_ids matching the selected filter values."""
    if accounts_df is None:
        return None
    df = accounts_df.copy()
    if regions:
        df = df[df["region"].isin(regions)]
    if industries:
        df = df[df["industry"].isin(industries)]
    if sizes:
        df = df[df["employee_size"].isin(sizes)]
    return df


def filter_opps(opps_df, accounts_df, date_from, date_to, stages):
    """Apply account-level and date/stage filters to opportunities."""
    if opps_df is None:
        return None
    df = opps_df.copy()
    df["close_date"] = pd.to_datetime(df["close_date"])
    # Account filters
    if accounts_df is not None:
        df = df[df["account_id"].isin(accounts_df["account_id"])]
    # Date filter
    if date_from:
        df = df[df["close_date"] >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df["close_date"] <= pd.Timestamp(date_to)]
    # Stage filter
    if stages:
        df = df[df["stage"].isin(stages)]
    return df


def filter_usage(usage_df, accounts_df, products, activity_days):
    """Apply account-level and product/activity filters to usage data."""
    if usage_df is None:
        return None
    df = usage_df.copy()
    if accounts_df is not None:
        df = df[df["account_id"].isin(accounts_df["account_id"])]
    if products:
        df = df[df["product_name"].isin(products)]
    if activity_days:
        cutoff = (datetime.today() - timedelta(days=activity_days)).strftime("%Y-%m-%d")
        df["last_active_date"] = df["last_active_date"].astype(str)
        df = df[df["last_active_date"] >= cutoff]
    return df


def compute_live_kpis(opps_f, usage_f, subs_f, accts_f, quota=5_000_000):
    """Compute KPIs live from filtered dataframes."""
    kpis = {}
    if opps_f is not None and len(opps_f):
        open_pipe = opps_f[~opps_f["stage"].isin(["Closed Won", "Closed Lost"])]["pipeline_value"].sum()
        kpis["pipeline_coverage"] = round(open_pipe / quota, 2)
        closed = opps_f[opps_f["stage"].isin(["Closed Won", "Closed Lost"])]
        won = (closed["stage"] == "Closed Won").sum()
        kpis["win_rate"] = round(won / len(closed), 4) if len(closed) else 0
        won_opps = opps_f[opps_f["stage"] == "Closed Won"]
        kpis["avg_deal_size"] = round(float(won_opps["pipeline_value"].mean()), 2) if len(won_opps) else 0
        if len(won_opps):
            wc = won_opps.copy()
            wc["created_date"] = pd.to_datetime(wc["created_date"])
            wc["close_date"] = pd.to_datetime(wc["close_date"])
            cycle = (wc["close_date"] - wc["created_date"]).dt.days.mean()
            kpis["sales_cycle"] = round(float(cycle), 1) if pd.notna(cycle) else 0
        else:
            kpis["sales_cycle"] = 0
    if subs_f is not None and len(subs_f):
        base = subs_f["contract_value"].sum()
        if base > 0:
            exp = subs_f[subs_f["expansion_flag"] == 1]["contract_value"].sum() * 0.20
            kpis["nrr"] = round((base + exp - base * 0.05) / base, 4)
        kpis["seat_expansion"] = round(float(subs_f["expansion_flag"].mean()), 4)
    if usage_f is not None and accts_f is not None and len(usage_f) and len(accts_f):
        product_counts = usage_f.groupby("account_id")["product_name"].nunique()
        multi = (product_counts > 1).sum()
        kpis["product_attach"] = round(multi / len(accts_f), 4)
        cutoff = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        uf = usage_f.copy()
        uf["last_active_date"] = uf["last_active_date"].astype(str)
        total = uf["account_id"].nunique()
        at_risk = uf[uf["last_active_date"] < cutoff]["account_id"].nunique()
        kpis["usage_at_risk"] = round(at_risk / total, 4) if total else 0
    return kpis


def build_filter_summary(regions, industries, sizes, date_from, date_to, stages, products):
    """Build a human-readable summary of active filters for AI context."""
    parts = []
    if regions:
        parts.append(f"Region: {', '.join(regions)}")
    if industries:
        parts.append(f"Industry: {', '.join(industries)}")
    if sizes:
        parts.append(f"Company size: {', '.join(sizes)}")
    if date_from or date_to:
        parts.append(f"Close date: {date_from or '...'} → {date_to or '...'}")
    if stages:
        parts.append(f"Stage: {', '.join(stages)}")
    if products:
        parts.append(f"Products: {', '.join(products)}")
    return " | ".join(parts) if parts else ""


# ── Load base data ────────────────────────────────────────────────────────────────

accounts_raw = load_accounts()
opps_raw     = load_opportunities()
usage_raw    = load_usage()
subs_raw     = load_subscriptions()
metrics_df   = load_metrics()

# Derive option lists from raw data
_regions    = sorted(accounts_raw["region"].dropna().unique().tolist()) if accounts_raw is not None else []
_industries = sorted(accounts_raw["industry"].dropna().unique().tolist()) if accounts_raw is not None else []
_sizes      = sorted(accounts_raw["employee_size"].dropna().unique().tolist()) if accounts_raw is not None else []
_stages     = sorted(opps_raw["stage"].dropna().unique().tolist()) if opps_raw is not None else []
_products   = sorted(usage_raw["product_name"].dropna().unique().tolist()) if usage_raw is not None else []

_opps_min_date = pd.to_datetime(opps_raw["close_date"]).min().date() if opps_raw is not None else date(2024, 1, 1)
_opps_max_date = pd.to_datetime(opps_raw["close_date"]).max().date() if opps_raw is not None else date.today()


# ── Sidebar ──────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='padding: 1rem 0;'>
        <div style='font-size:1.3rem; font-weight:700; color:#e2e8f0;'>🧠 Growth Agent</div>
        <div style='color:#475569; font-size:0.8rem;'>Revenue Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Global Filters ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**🔍 Global Filters**")
    st.caption("Applied to KPI cards, charts, and AI context")

    sel_regions = st.multiselect("Region", _regions, placeholder="All regions")
    sel_industries = st.multiselect("Industry", _industries, placeholder="All industries")
    sel_sizes = st.multiselect("Company Size", _sizes, placeholder="All sizes")

    col_d1, col_d2 = st.columns(2)
    sel_date_from = col_d1.date_input("Close From", value=None, min_value=_opps_min_date, max_value=_opps_max_date)
    sel_date_to   = col_d2.date_input("Close To",   value=None, min_value=_opps_min_date, max_value=_opps_max_date)

    sel_stages = st.multiselect("Deal Stage", _stages, placeholder="All stages")
    sel_products = st.multiselect("Product Module", _products, placeholder="All products")

    if st.button("↺ Reset Filters", use_container_width=True):
        st.rerun()

    # ── Settings ─────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**⚙️ Settings**")
    alert_threshold = st.slider("Alert Threshold (%)", 10, 40, 20, 5)
    show_tool_steps = st.checkbox("Show Agent Tool Steps", value=False)

    # ── Quick Actions ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**⚡ Quick Actions**")

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if st.button("🚨 Check Alerts", use_container_width=True):
        try:
            from agent.alerts import compute_alerts
            with st.spinner("Checking alerts..."):
                st.session_state["alerts"] = compute_alerts(threshold_pct=alert_threshold / 100)
            count = len(st.session_state["alerts"])
            st.toast(f"Found {count} alert(s) — see Alerts tab", icon="🚨" if count else "✅")
        except Exception as e:
            st.error(f"Alert check failed: {e}")

    if st.button("📊 Run Full Analysis", use_container_width=True):
        st.session_state["run_analysis"] = True

    st.markdown("---")
    st.markdown("""
    <div style='color:#334155; font-size:0.72rem; line-height:1.6;'>
    <b style='color:#475569;'>Stack</b><br>
    Python · LangChain · Claude<br>
    FAISS · Streamlit · Plotly
    </div>
    """, unsafe_allow_html=True)


# ── Apply filters to data ────────────────────────────────────────────────────────

filters_active = any([sel_regions, sel_industries, sel_sizes,
                      sel_date_from, sel_date_to, sel_stages, sel_products])

accts_f = apply_account_filter(accounts_raw, sel_regions, sel_industries, sel_sizes)
opps_f  = filter_opps(opps_raw, accts_f if filters_active else None,
                      sel_date_from, sel_date_to, sel_stages)
usage_f = filter_usage(usage_raw, accts_f if filters_active else None,
                       sel_products, None)
subs_f  = subs_raw[subs_raw["account_id"].isin(accts_f["account_id"])].copy() \
          if (accts_f is not None and filters_active and subs_raw is not None) else subs_raw

filter_summary = build_filter_summary(sel_regions, sel_industries, sel_sizes,
                                      sel_date_from, sel_date_to, sel_stages, sel_products)

# Compute live KPIs (from filtered data when filters active, otherwise from metrics.csv)
live_kpis = compute_live_kpis(opps_f, usage_f, subs_f, accts_f) if filters_active else {}


# ── Hero Header ──────────────────────────────────────────────────────────────────

data_status = "✅ Live Data" if metrics_df is not None else "⚠️ No Data — Run generate_data.py"

_filter_badge_html = f'<span class="filter-badge">🔍 Filtered: {filter_summary}</span>' if filters_active else ""
st.markdown(
    f'<div class="hero-header"><div style="display:flex; justify-content:space-between; align-items:flex-start;"><div>'
    f'<div class="hero-title">Growth Intelligence Agent</div>'
    f'<div class="hero-subtitle">AI-powered revenue analytics · {datetime.now().strftime("%B %d, %Y")}</div>'
    f'{_filter_badge_html}</div>'
    f'<div class="hero-badge">{data_status}</div></div></div>',
    unsafe_allow_html=True,
)


# ── KPI Cards ────────────────────────────────────────────────────────────────────

def _kv(name, fallback_df=None):
    """Get KPI value: from live_kpis if filtered, else from metrics.csv."""
    key_map = {
        "Win Rate": "win_rate",
        "Pipeline Coverage": "pipeline_coverage",
        "Net Revenue Retention": "nrr",
        "Average Deal Size": "avg_deal_size",
        "Product Attach Rate": "product_attach",
        "Seat Expansion Rate": "seat_expansion",
        "Usage At-Risk Rate": "usage_at_risk",
        "Sales Cycle Length (days)": "sales_cycle",
    }
    if filters_active and key_map.get(name) in live_kpis:
        return live_kpis[key_map[name]]
    return get_metric_val(fallback_df, name)

if metrics_df is not None or filters_active:
    wr       = _kv("Win Rate", metrics_df)
    pc       = _kv("Pipeline Coverage", metrics_df)
    nrr      = _kv("Net Revenue Retention", metrics_df)
    ads      = _kv("Average Deal Size", metrics_df)
    attach   = _kv("Product Attach Rate", metrics_df)
    expansion= _kv("Seat Expansion Rate", metrics_df)
    at_risk  = _kv("Usage At-Risk Rate", metrics_df)
    cycle    = _kv("Sales Cycle Length (days)", metrics_df)

    def card(label, value, fmt, target_label, status):
        if value is None:
            display = "—"
        elif fmt == "pct":
            display = f"{value*100:.1f}%"
        elif fmt == "x":
            display = f"{value:.2f}x"
        elif fmt == "$":
            display = f"${value:,.0f}"
        else:
            display = f"{value:.1f}"
        return f"""
        <div class="metric-card {status}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{display}</div>
            <div class="metric-target">Target: {target_label}</div>
        </div>"""

    cols = st.columns(4)
    cards = [
        ("Win Rate",            wr,        "pct", "≥ 28%",    "good" if wr and wr >= 0.28 else "bad"),
        ("Pipeline Coverage",   pc,        "x",   "≥ 3.5x",   "good" if pc and pc >= 3.5 else "warn"),
        ("Net Revenue Retention",nrr,      "pct", "≥ 120%",   "good" if nrr and nrr >= 1.2 else "bad"),
        ("Average Deal Size",   ads,       "$",   "Maximize",  "good"),
        ("Product Attach Rate", attach,    "pct", "≥ 35%",    "good" if attach and attach >= 0.35 else "warn"),
        ("Seat Expansion Rate", expansion, "pct", "≥ 25%",    "good" if expansion and expansion >= 0.25 else "warn"),
        ("Usage At-Risk Rate",  at_risk,   "pct", "< 10%",    "good" if at_risk and at_risk < 0.10 else "bad"),
        ("Sales Cycle (days)",  cycle,     "d",   "Minimize",  "good" if cycle and cycle < 60 else "warn"),
    ]
    for i, (label, val, fmt, tgt_label, status) in enumerate(cards):
        cols[i % 4].markdown(card(label, val, fmt, tgt_label, status), unsafe_allow_html=True)
        if i % 4 == 3 and i < 7:
            cols = st.columns(4)

st.markdown("<br>", unsafe_allow_html=True)


# ── Main Tabs ────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(["💬 AI Chat", "📊 Metrics Explorer", "🚨 Alerts", "🔍 Insights"])


# ── Tab 1: AI Chat ───────────────────────────────────────────────────────────────

with tab1:
    st.markdown("**Ask the Growth Intelligence Agent anything about your metrics:**")

    if filters_active:
        st.info(f"🔍 **Active filters applied to context:** {filter_summary}", icon="🔍")

    suggestions = [
        "What is our current win rate by region?",
        "Which accounts are at churn risk?",
        "How is our pipeline coverage vs target?",
        "What are the top expansion opportunities?",
        "Summarize our overall growth health",
    ]

    cols = st.columns(len(suggestions))
    for i, suggestion in enumerate(suggestions):
        if cols[i].button(suggestion[:30] + "...", key=f"sugg_{i}", use_container_width=True):
            st.session_state["prefill_question"] = suggestion

    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for role, content in st.session_state.chat_history:
        if role == "user":
            st.markdown(f'<div class="user-msg">👤 {content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="agent-msg">🧠 {content}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    prefill = st.session_state.pop("prefill_question", "")
    question = st.text_input(
        "Your question",
        value=prefill,
        placeholder="e.g. What's driving our pipeline decline in EMEA?",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 5])
    ask_clicked = col1.button("Ask Agent 🚀", use_container_width=True)

    if ask_clicked and question:
        # Prepend active filter context so agent answers within the right scope
        agent_question = question
        if filters_active:
            agent_question = f"[Active data filters: {filter_summary}]\n\n{question}"

        st.session_state.chat_history.append(("user", question))

        with st.spinner("🧠 Agent is reasoning..."):
            try:
                from agent.agent import ask as agent_ask
                history_pairs = []
                msgs = st.session_state.chat_history[:-1]
                for i in range(0, len(msgs) - 1, 2):
                    if (i + 1 < len(msgs)
                            and msgs[i][0] == "user"
                            and msgs[i + 1][0] == "agent"):
                        history_pairs.append((msgs[i][1], msgs[i + 1][1]))

                result = agent_ask(agent_question, history_pairs)
                answer = result["answer"]

                if show_tool_steps and result.get("steps"):
                    with st.expander("🔧 Agent Tool Steps", expanded=False):
                        for step in result["steps"]:
                            st.json(step)
            except Exception as e:
                answer = f"⚠️ Agent error: {str(e)}\n\nMake sure your API key is set in `.env` and data is generated."

        st.session_state.chat_history.append(("agent", answer))
        st.rerun()

    if col2.button("Clear Chat", use_container_width=False):
        st.session_state.chat_history = []
        st.rerun()


# ── Tab 2: Metrics Explorer ──────────────────────────────────────────────────────

with tab2:
    if opps_f is None and metrics_df is None:
        st.warning("No data found. Run `python scripts/generate_data.py` and then `python metrics/compute_metrics.py`.")
    else:
        # Filter summary banner
        if filters_active:
            n_accts = len(accts_f) if accts_f is not None else "?"
            n_opps  = len(opps_f)  if opps_f  is not None else "?"
            st.success(f"🔍 Showing filtered data — **{n_accts} accounts**, **{n_opps} opportunities**")

        # ── Row 1: Win Rate chart + pipeline stage filters ────────────────────────
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("**Metrics Table**")
            if metrics_df is not None:
                display_df = metrics_df.copy()
                display_df["metric_value"] = display_df["metric_value"].round(4)
                st.dataframe(display_df, use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**Win Rate by Region**")
            # Compute filtered win rate by region live
            if opps_f is not None and accts_f is not None and len(opps_f):
                merged_wr = opps_f.merge(
                    accts_f[["account_id", "region"]], on="account_id", how="left"
                )
                closed_wr = merged_wr[merged_wr["stage"].isin(["Closed Won", "Closed Lost"])]
                if len(closed_wr):
                    wr_by_region = closed_wr.groupby("region").apply(
                        lambda g: round((g["stage"] == "Closed Won").sum() / len(g), 4)
                    ).reset_index(name="metric_value")
                    wr_by_region.columns = ["segment", "metric_value"]

                    fig = px.bar(
                        wr_by_region, x="segment", y="metric_value",
                        color="metric_value",
                        color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
                        labels={"segment": "Region", "metric_value": "Win Rate"},
                        template="plotly_dark",
                    )
                    fig.update_layout(
                        plot_bgcolor="#111827", paper_bgcolor="#111827",
                        coloraxis_showscale=False, margin=dict(l=0, r=0, t=30, b=0),
                    )
                    fig.add_hline(y=0.28, line_dash="dash", line_color="#f59e0b",
                                  annotation_text="Target 28%")
                    fig.update_traces(marker_line_width=0)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No closed deals match the current filters.")
            elif metrics_df is not None:
                region_wr = metrics_df[
                    (metrics_df["metric_name"] == "Win Rate") & (metrics_df["segment"] != "All")
                ]
                if len(region_wr):
                    fig = px.bar(
                        region_wr, x="segment", y="metric_value",
                        color="metric_value",
                        color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
                        labels={"segment": "Region", "metric_value": "Win Rate"},
                        template="plotly_dark",
                    )
                    fig.update_layout(
                        plot_bgcolor="#111827", paper_bgcolor="#111827",
                        coloraxis_showscale=False, margin=dict(l=0, r=0, t=30, b=0),
                    )
                    fig.add_hline(y=0.28, line_dash="dash", line_color="#f59e0b",
                                  annotation_text="Target 28%")
                    fig.update_traces(marker_line_width=0)
                    st.plotly_chart(fig, use_container_width=True)

        # ── Row 2: Pipeline by stage + Industry breakdown ─────────────────────────
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("**Pipeline Distribution by Stage**")
            if opps_f is not None and len(opps_f):
                stage_data = opps_f.groupby("stage")["pipeline_value"].sum().reset_index()
                fig2 = px.pie(
                    stage_data, names="stage", values="pipeline_value",
                    template="plotly_dark",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )
                fig2.update_layout(
                    plot_bgcolor="#111827", paper_bgcolor="#111827",
                    margin=dict(l=0, r=0, t=30, b=0),
                )
                st.plotly_chart(fig2, use_container_width=True)

        with c2:
            st.markdown("**Win Rate by Industry**")
            if opps_f is not None and accts_f is not None and len(opps_f):
                merged_ind = opps_f.merge(
                    accts_f[["account_id", "industry"]], on="account_id", how="left"
                )
                closed_ind = merged_ind[merged_ind["stage"].isin(["Closed Won", "Closed Lost"])]
                if len(closed_ind):
                    wr_ind = closed_ind.groupby("industry").apply(
                        lambda g: round((g["stage"] == "Closed Won").sum() / len(g), 4)
                    ).reset_index(name="win_rate")
                    fig_ind = px.bar(
                        wr_ind.sort_values("win_rate", ascending=True),
                        x="win_rate", y="industry", orientation="h",
                        template="plotly_dark",
                        labels={"win_rate": "Win Rate", "industry": ""},
                        color="win_rate",
                        color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
                    )
                    fig_ind.update_layout(
                        plot_bgcolor="#111827", paper_bgcolor="#111827",
                        coloraxis_showscale=False, margin=dict(l=0, r=0, t=30, b=0),
                    )
                    fig_ind.add_vline(x=0.28, line_dash="dash", line_color="#f59e0b",
                                      annotation_text="Target")
                    st.plotly_chart(fig_ind, use_container_width=True)

        # ── Row 3: Pipeline value range filter + deal table ───────────────────────
        st.markdown("**Deal Pipeline Explorer**")
        if opps_f is not None and len(opps_f):
            min_val = int(opps_f["pipeline_value"].min())
            max_val = int(opps_f["pipeline_value"].max())
            if min_val < max_val:
                val_range = st.slider(
                    "Pipeline Value Range ($)",
                    min_value=min_val, max_value=max_val,
                    value=(min_val, max_val),
                    format="$%d",
                )
                deals_view = opps_f[
                    (opps_f["pipeline_value"] >= val_range[0]) &
                    (opps_f["pipeline_value"] <= val_range[1])
                ]
            else:
                deals_view = opps_f

            if accts_f is not None:
                deals_view = deals_view.merge(
                    accts_f[["account_id", "company_name", "region", "industry"]],
                    on="account_id", how="left"
                )

            cols_show = [c for c in ["opportunity_id", "company_name", "stage",
                                      "pipeline_value", "close_date", "region", "industry"]
                         if c in deals_view.columns]
            st.dataframe(
                deals_view[cols_show].sort_values("pipeline_value", ascending=False).head(50),
                use_container_width=True, hide_index=True
            )
            st.caption(f"{len(deals_view):,} deals shown")

        # ── Row 4: Product usage ──────────────────────────────────────────────────
        st.markdown("**Product Usage by Module**")

        # Activity window selector
        activity_window = st.select_slider(
            "Active within last N days",
            options=[7, 14, 30, 60, 90, 180],
            value=60,
        )
        usage_view = filter_usage(usage_raw, accts_f if filters_active else None,
                                  sel_products if sel_products else None, activity_window)

        if usage_view is not None and len(usage_view):
            product_stats = usage_view.groupby("product_name").agg(
                accounts=("account_id", "nunique"),
                total_users=("active_users", "sum"),
                total_events=("usage_events", "sum"),
            ).reset_index().sort_values("total_users", ascending=False)

            fig3 = px.bar(
                product_stats, x="product_name", y=["total_users", "total_events"],
                barmode="group", template="plotly_dark",
                labels={"product_name": "Product", "value": "Count"},
                color_discrete_map={"total_users": "#3b82f6", "total_events": "#22c55e"},
            )
            fig3.update_layout(
                plot_bgcolor="#111827", paper_bgcolor="#111827",
                margin=dict(l=0, r=0, t=30, b=0),
            )
            st.plotly_chart(fig3, use_container_width=True)

            # Company size distribution of active accounts
            if accts_f is not None:
                active_accts = usage_view["account_id"].unique()
                size_dist = accts_f[accts_f["account_id"].isin(active_accts)].groupby(
                    "employee_size"
                ).size().reset_index(name="count")
                if len(size_dist):
                    st.markdown("**Active Accounts by Company Size**")
                    fig4 = px.bar(
                        size_dist, x="employee_size", y="count",
                        template="plotly_dark", color="count",
                        color_continuous_scale=["#1e3a5f", "#3b82f6"],
                        labels={"employee_size": "Company Size", "count": "Accounts"},
                    )
                    fig4.update_layout(
                        plot_bgcolor="#111827", paper_bgcolor="#111827",
                        coloraxis_showscale=False, margin=dict(l=0, r=0, t=30, b=0),
                    )
                    st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No usage data matches the current filters.")


# ── Tab 3: Alerts ────────────────────────────────────────────────────────────────

with tab3:
    st.markdown("**Automated Metric Alerts**")
    st.caption(f"Threshold: >{alert_threshold}% change from previous period triggers an alert")

    if st.button("🔍 Run Alert Check", use_container_width=False):
        with st.spinner("Analyzing metrics for anomalies..."):
            try:
                from agent.alerts import compute_alerts
                alerts = compute_alerts(threshold_pct=alert_threshold / 100)
                st.session_state["alerts"] = alerts
            except Exception as e:
                st.error(f"Alert check failed: {e}")

    alerts = st.session_state.get("alerts") or []
    if alerts:
        high = [a for a in alerts if a.get("severity") == "High"]
        med  = [a for a in alerts if a.get("severity") == "Medium"]
        low  = [a for a in alerts if a.get("severity") == "Low"]

        a1, a2, a3 = st.columns(3)
        a1.metric("🔴 High Priority", len(high))
        a2.metric("🟡 Medium Priority", len(med))
        a3.metric("🔵 Low Priority", len(low))

        st.markdown("---")
        for alert in alerts:
            sev = alert.get("severity", "Low").lower()
            sign = "+" if alert["change_pct"] > 0 else ""
            good_icon = "✅" if alert["is_positive"] else "❌"

            st.markdown(f"""
            <div class="alert-{sev}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="font-weight:700; color:#e2e8f0;">{alert['direction']} {alert['metric']}</span>
                        <span style="color:#64748b; font-size:0.8rem; margin-left:0.5rem;">· {alert['segment']}</span>
                    </div>
                    <div style="font-size:0.75rem; font-weight:600; color:{'#ef4444' if sev=='high' else '#f59e0b' if sev=='medium' else '#3b82f6'}">
                        {alert['severity'].upper()}
                    </div>
                </div>
                <div style="margin-top:0.4rem; color:#94a3b8; font-family:'JetBrains Mono',monospace; font-size:0.85rem;">
                    {good_icon} {sign}{alert['change_pct']}% &nbsp;·&nbsp;
                    {alert['previous_value']} → {alert['current_value']}
                </div>
                <div style="margin-top:0.4rem; color:#64748b; font-size:0.82rem;">
                    💡 {alert['recommended_action']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    elif st.session_state.get("alerts") is not None:
        st.success("✅ All metrics within normal range. No alerts triggered.")
    else:
        st.info("Click **Run Alert Check** to scan metrics for anomalies.")


# ── Tab 4: Insights ──────────────────────────────────────────────────────────────

with tab4:
    st.markdown("**AI-Generated Growth Insights**")
    st.caption("The agent analyzes all metrics, pipeline, and usage data to generate strategic insights.")

    if filters_active:
        st.info(f"🔍 Analysis will reflect active filters: **{filter_summary}**")

    run_now = st.session_state.pop("run_analysis", False)
    if st.button("🧠 Generate Full Analysis", use_container_width=False) or run_now:
        with st.spinner("Running comprehensive analysis (this may take 15–30 seconds)..."):
            try:
                from agent.agent import generate_full_analysis

                # When filters are active, compute a filtered data summary and
                # inject it into the analysis so the LLM reasons over the right slice
                filter_context = ""
                if filters_active and opps_f is not None and len(opps_f):
                    closed_f = opps_f[opps_f["stage"].isin(["Closed Won", "Closed Lost"])]
                    won_f = (closed_f["stage"] == "Closed Won").sum()
                    open_pipe_f = opps_f[~opps_f["stage"].isin(["Closed Won", "Closed Lost"])]["pipeline_value"].sum()
                    filter_context = (
                        f"\n\n[FILTER CONTEXT — analysis is scoped to: {filter_summary}]\n"
                        f"Filtered dataset: {len(accts_f)} accounts, {len(opps_f)} opportunities, "
                        f"open pipeline ${open_pipe_f:,.0f}, "
                        f"win rate {round(won_f/len(closed_f)*100,1) if len(closed_f) else 0}%\n"
                    )

                analysis = generate_full_analysis()
                if filter_context:
                    analysis = filter_context + "\n" + analysis
                st.session_state["analysis"] = analysis
            except Exception as e:
                st.session_state["analysis"] = f"⚠️ Analysis failed: {str(e)}\n\nEnsure your API key is set and data is generated."

    analysis = st.session_state.get("analysis")
    if analysis:
        with st.container():
            st.markdown(analysis)
    else:
        st.markdown("""
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
            <div style="background:#111827; border:1px solid #1e293b; border-radius:12px; padding:1.25rem;">
                <div style="color:#3b82f6; font-weight:700; margin-bottom:0.5rem;">🎯 Pipeline Health</div>
                <div style="color:#64748b; font-size:0.85rem;">Click "Generate Full Analysis" to get AI-powered insights about your pipeline coverage, win rates, and deal velocity.</div>
            </div>
            <div style="background:#111827; border:1px solid #1e293b; border-radius:12px; padding:1.25rem;">
                <div style="color:#22c55e; font-weight:700; margin-bottom:0.5rem;">📈 Expansion Opportunities</div>
                <div style="color:#64748b; font-size:0.85rem;">The agent will identify which accounts are primed for expansion based on usage patterns and product adoption.</div>
            </div>
            <div style="background:#111827; border:1px solid #1e293b; border-radius:12px; padding:1.25rem;">
                <div style="color:#f59e0b; font-weight:700; margin-bottom:0.5rem;">⚠️ Retention Risk</div>
                <div style="color:#64748b; font-size:0.85rem;">AI will flag at-risk accounts based on usage decline and renewal timing.</div>
            </div>
            <div style="background:#111827; border:1px solid #1e293b; border-radius:12px; padding:1.25rem;">
                <div style="color:#a78bfa; font-weight:700; margin-bottom:0.5rem;">🗺️ Segment Analysis</div>
                <div style="color:#64748b; font-size:0.85rem;">Understand which regions and industries are outperforming or lagging against targets.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
