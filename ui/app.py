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
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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

    /* Header */
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
    .hero-title {
        font-size: 2rem;
        font-weight: 700;
        color: #e2e8f0;
        margin: 0;
    }
    .hero-subtitle {
        color: #64748b;
        font-size: 0.95rem;
        margin-top: 0.3rem;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(34,197,94,0.1);
        border: 1px solid rgba(34,197,94,0.3);
        color: #4ade80;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(145deg, #111827, #1a2035);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        position: relative;
        overflow: hidden;
        transition: border-color 0.2s;
    }
    .metric-card:hover { border-color: #3b82f6; }
    .metric-card.good { border-left: 3px solid #22c55e; }
    .metric-card.warn { border-left: 3px solid #f59e0b; }
    .metric-card.bad  { border-left: 3px solid #ef4444; }
    .metric-label { color: #64748b; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
    .metric-value { color: #f1f5f9; font-size: 1.8rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .metric-target { color: #475569; font-size: 0.72rem; margin-top: 2px; }

    /* Alert cards */
    .alert-high { background: rgba(239,68,68,0.05); border: 1px solid rgba(239,68,68,0.3); border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem; }
    .alert-medium { background: rgba(245,158,11,0.05); border: 1px solid rgba(245,158,11,0.3); border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem; }
    .alert-low { background: rgba(59,130,246,0.05); border: 1px solid rgba(59,130,246,0.3); border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem; }

    /* Chat */
    .chat-container { max-height: 500px; overflow-y: auto; }
    .user-msg { background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2); border-radius: 12px 12px 2px 12px; padding: 0.75rem 1rem; margin: 0.5rem 0; color: #bfdbfe; }
    .agent-msg { background: rgba(30,41,59,0.8); border: 1px solid #1e3a5f; border-radius: 12px 12px 12px 2px; padding: 0.75rem 1rem; margin: 0.5rem 0; color: #e2e8f0; }

    /* Sidebar */
    .stSidebar { background: #070d1a !important; }
    section[data-testid="stSidebar"] { background: #070d1a; border-right: 1px solid #1e293b; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background: transparent; gap: 4px; }
    .stTabs [data-baseweb="tab"] { background: #111827; border: 1px solid #1e293b; border-radius: 8px; color: #64748b; font-weight: 500; }
    .stTabs [aria-selected="true"] { background: #1d4ed8 !important; border-color: #3b82f6 !important; color: white !important; }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #1d4ed8, #2563eb);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-family: 'Space Grotesk', sans-serif;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s;
    }
    .stButton > button:hover { background: linear-gradient(135deg, #2563eb, #3b82f6); transform: translateY(-1px); }

    /* Input */
    .stTextInput > div > div > input {
        background: #111827;
        border: 1px solid #1e293b;
        color: #e2e8f0;
        border-radius: 8px;
        font-family: 'Space Grotesk', sans-serif;
    }
    .stTextInput > div > div > input:focus { border-color: #3b82f6; }
</style>
""", unsafe_allow_html=True)


# ── Data loading helpers ─────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_metrics():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "metrics.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


@st.cache_data(ttl=300)
def load_opportunities():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "opportunities.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


@st.cache_data(ttl=300)
def load_usage():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "product_usage.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


def get_metric_val(df, name, segment="All"):
    if df is None:
        return None
    row = df[(df["metric_name"] == name) & (df["segment"] == segment)]
    return row.iloc[0]["metric_value"] if len(row) else None


# ── Sidebar ──────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='padding: 1rem 0;'>
        <div style='font-size:1.3rem; font-weight:700; color:#e2e8f0;'>🧠 Growth Agent</div>
        <div style='color:#475569; font-size:0.8rem;'>Revenue Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**⚡ Quick Actions**")

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if st.button("🚨 Check Alerts", use_container_width=True):
        st.session_state["active_tab"] = "alerts"

    if st.button("📊 Run Full Analysis", use_container_width=True):
        st.session_state["run_analysis"] = True

    st.markdown("---")
    st.markdown("**⚙️ Settings**")
    alert_threshold = st.slider("Alert Threshold (%)", 10, 40, 20, 5)
    show_tool_steps = st.checkbox("Show Agent Tool Steps", value=False)

    st.markdown("---")
    st.markdown("""
    <div style='color:#334155; font-size:0.72rem; line-height:1.6;'>
    <b style='color:#475569;'>Stack</b><br>
    Python · LangChain · Claude<br>
    FAISS · Streamlit · Plotly
    </div>
    """, unsafe_allow_html=True)


# ── Hero Header ──────────────────────────────────────────────────────────────────

metrics_df = load_metrics()
data_status = "✅ Live Data" if metrics_df is not None else "⚠️ No Data — Run generate_data.py"

st.markdown(f"""
<div class="hero-header">
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
            <div class="hero-title">Growth Intelligence Agent</div>
            <div class="hero-subtitle">AI-powered revenue analytics · {datetime.now().strftime("%B %d, %Y")}</div>
        </div>
        <div class="hero-badge">{data_status}</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── KPI Cards ────────────────────────────────────────────────────────────────────

if metrics_df is not None:
    wr = get_metric_val(metrics_df, "Win Rate")
    pc = get_metric_val(metrics_df, "Pipeline Coverage")
    nrr = get_metric_val(metrics_df, "Net Revenue Retention")
    ads = get_metric_val(metrics_df, "Average Deal Size")
    attach = get_metric_val(metrics_df, "Product Attach Rate")
    expansion = get_metric_val(metrics_df, "Seat Expansion Rate")
    at_risk = get_metric_val(metrics_df, "Usage At-Risk Rate")
    cycle = get_metric_val(metrics_df, "Sales Cycle Length (days)")

    def card(label, value, fmt, target, target_label, status):
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
        ("Win Rate", wr, "pct", None, "≥ 28%", "good" if wr and wr >= 0.28 else "bad"),
        ("Pipeline Coverage", pc, "x", None, "≥ 3.5x", "good" if pc and pc >= 3.5 else "warn"),
        ("Net Revenue Retention", nrr, "pct", None, "≥ 120%", "good" if nrr and nrr >= 1.2 else "bad"),
        ("Average Deal Size", ads, "$", None, "Maximize", "good"),
        ("Product Attach Rate", attach, "pct", None, "≥ 35%", "good" if attach and attach >= 0.35 else "warn"),
        ("Seat Expansion Rate", expansion, "pct", None, "≥ 25%", "good" if expansion and expansion >= 0.25 else "warn"),
        ("Usage At-Risk Rate", at_risk, "pct", None, "< 10%", "good" if at_risk and at_risk < 0.10 else "bad"),
        ("Sales Cycle (days)", cycle, "d", None, "Minimize", "good" if cycle and cycle < 60 else "warn"),
    ]
    for i, (label, val, fmt, tgt, tgt_label, status) in enumerate(cards):
        cols[i % 4].markdown(card(label, val, fmt, tgt, tgt_label, status), unsafe_allow_html=True)
        if i % 4 == 3 and i < 7:
            cols = st.columns(4)

st.markdown("<br>", unsafe_allow_html=True)


# ── Main Tabs ────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(["💬 AI Chat", "📊 Metrics Explorer", "🚨 Alerts", "🔍 Insights"])


# ── Tab 1: AI Chat ───────────────────────────────────────────────────────────────

with tab1:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.markdown("**Ask the Growth Intelligence Agent anything about your metrics:**")

    # Suggestion chips
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

    # Chat display
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for role, content in st.session_state.chat_history:
        if role == "user":
            st.markdown(f'<div class="user-msg">👤 {content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="agent-msg">🧠 {content}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Input
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
        st.session_state.chat_history.append(("user", question))

        with st.spinner("🧠 Agent is reasoning..."):
            try:
                from agent.agent import ask as agent_ask
                history_pairs = []
                msgs = st.session_state.chat_history[:-1]
                for i in range(0, len(msgs) - 1, 2):
                    if msgs[i][0] == "user" and msgs[i+1][0] == "agent":
                        history_pairs.append((msgs[i][1], msgs[i+1][1]))

                result = agent_ask(question, history_pairs)
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
    if metrics_df is None:
        st.warning("No metrics data found. Run `python scripts/generate_data.py` and then `python metrics/compute_metrics.py`.")
    else:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("**Metrics Table**")
            display_df = metrics_df.copy()
            display_df["metric_value"] = display_df["metric_value"].round(4)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**Win Rate by Region**")
            region_wr = metrics_df[
                (metrics_df["metric_name"] == "Win Rate") & (metrics_df["segment"] != "All")
            ]
            if len(region_wr) > 0:
                fig = px.bar(
                    region_wr, x="segment", y="metric_value",
                    color="metric_value",
                    color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
                    labels={"segment": "Region", "metric_value": "Win Rate"},
                    template="plotly_dark",
                )
                fig.update_layout(
                    plot_bgcolor="#111827", paper_bgcolor="#111827",
                    coloraxis_showscale=False,
                    margin=dict(l=0, r=0, t=30, b=0),
                )
                fig.add_hline(y=0.28, line_dash="dash", line_color="#f59e0b",
                              annotation_text="Target 28%")
                fig.update_traces(marker_line_width=0)
                st.plotly_chart(fig, use_container_width=True)

        # Pipeline by stage
        st.markdown("**Pipeline Distribution by Stage**")
        opps_df = load_opportunities()
        if opps_df is not None:
            stage_data = opps_df.groupby("stage")["pipeline_value"].sum().reset_index()
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

        # Product usage
        st.markdown("**Product Usage by Module**")
        usage_df = load_usage()
        if usage_df is not None:
            product_stats = usage_df.groupby("product_name").agg(
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

    alerts = st.session_state.get("alerts", [])
    if alerts:
        high = [a for a in alerts if a.get("severity") == "High"]
        med = [a for a in alerts if a.get("severity") == "Medium"]
        low = [a for a in alerts if a.get("severity") == "Low"]

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
    elif "alerts" in st.session_state:
        st.success("✅ All metrics within normal range. No alerts triggered.")
    else:
        st.info("Click **Run Alert Check** to scan metrics for anomalies.")


# ── Tab 4: Insights ──────────────────────────────────────────────────────────────

with tab4:
    st.markdown("**AI-Generated Growth Insights**")
    st.caption("The agent analyzes all metrics, pipeline, and usage data to generate strategic insights.")

    run_now = st.session_state.pop("run_analysis", False)
    if st.button("🧠 Generate Full Analysis", use_container_width=False) or run_now:
        with st.spinner("Running comprehensive analysis (this may take 15–30 seconds)..."):
            try:
                from agent.agent import generate_full_analysis
                analysis = generate_full_analysis()
                st.session_state["analysis"] = analysis
            except Exception as e:
                st.session_state["analysis"] = f"⚠️ Analysis failed: {str(e)}\n\nEnsure your API key is set and data is generated."

    analysis = st.session_state.get("analysis")
    if analysis:
        st.markdown(f"""
        <div style="background:#111827; border:1px solid #1e3a5f; border-radius:12px; padding:1.5rem; line-height:1.8; color:#e2e8f0; white-space:pre-wrap;">
{analysis}
        </div>
        """, unsafe_allow_html=True)
    else:
        # Placeholder insight cards
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
