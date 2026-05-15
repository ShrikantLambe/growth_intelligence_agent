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

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Growth Intelligence Agent</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#0a0f1e;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh}
  a{color:#3b82f6;text-decoration:none}
  /* Nav */
  nav{background:#070d1a;border-bottom:1px solid #1e293b;padding:.9rem 2rem;display:flex;align-items:center;justify-content:space-between}
  .nav-brand{font-size:1.1rem;font-weight:700;color:#e2e8f0}
  .nav-badge{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);color:#4ade80;padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:600}
  .nav-links{display:flex;gap:1.2rem;font-size:.85rem;color:#64748b}
  /* Layout */
  .container{max-width:1300px;margin:0 auto;padding:1.5rem 2rem}
  /* Hero */
  .hero{background:linear-gradient(135deg,#0d1b2a,#1a2744 50%,#0d2137);border:1px solid #1e3a5f;border-radius:16px;padding:1.8rem 2rem;margin-bottom:1.5rem}
  .hero h1{font-size:1.8rem;font-weight:700;color:#e2e8f0}
  .hero p{color:#64748b;font-size:.9rem;margin-top:.3rem}
  /* KPI grid */
  .kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem}
  @media(max-width:900px){.kpi-grid{grid-template-columns:repeat(2,1fr)}}
  .kpi-card{background:linear-gradient(145deg,#111827,#1a2035);border:1px solid #1e293b;border-radius:12px;padding:1.1rem 1.3rem;position:relative;overflow:hidden;transition:border-color .2s}
  .kpi-card:hover{border-color:#3b82f6}
  .kpi-card.good{border-left:3px solid #22c55e}
  .kpi-card.warn{border-left:3px solid #f59e0b}
  .kpi-card.bad{border-left:3px solid #ef4444}
  .kpi-label{color:#64748b;font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em}
  .kpi-value{color:#f1f5f9;font-size:1.7rem;font-weight:700;font-family:monospace;margin:.2rem 0}
  .kpi-target{color:#475569;font-size:.7rem}
  /* Tabs */
  .tabs{display:flex;gap:4px;margin-bottom:1.2rem}
  .tab{background:#111827;border:1px solid #1e293b;border-radius:8px;padding:.45rem 1rem;cursor:pointer;font-size:.85rem;color:#64748b;font-weight:500;transition:all .15s}
  .tab.active,.tab:hover{background:#1d4ed8;border-color:#3b82f6;color:#fff}
  .tab-content{display:none}
  .tab-content.active{display:block}
  /* Cards */
  .card{background:#111827;border:1px solid #1e293b;border-radius:12px;padding:1.2rem 1.4rem;margin-bottom:1rem}
  .card h3{font-size:.9rem;font-weight:600;color:#94a3b8;margin-bottom:1rem;text-transform:uppercase;letter-spacing:.05em}
  /* Charts row */
  .charts-row{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem}
  @media(max-width:700px){.charts-row{grid-template-columns:1fr}}
  /* Alerts */
  .alert-item{border-radius:10px;padding:.9rem 1rem;margin-bottom:.6rem}
  .alert-high{background:rgba(239,68,68,.06);border:1px solid rgba(239,68,68,.3)}
  .alert-medium{background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.3)}
  .alert-low{background:rgba(59,130,246,.06);border:1px solid rgba(59,130,246,.3)}
  .alert-title{font-weight:600;color:#e2e8f0;font-size:.88rem}
  .alert-meta{color:#94a3b8;font-size:.78rem;margin-top:.25rem;font-family:monospace}
  .alert-action{color:#64748b;font-size:.78rem;margin-top:.25rem}
  .sev-badge{font-size:.68rem;font-weight:700;padding:2px 7px;border-radius:4px;float:right}
  .sev-high{background:rgba(239,68,68,.2);color:#f87171}
  .sev-medium{background:rgba(245,158,11,.2);color:#fbbf24}
  .sev-low{background:rgba(59,130,246,.2);color:#60a5fa}
  /* Chat */
  .chat-messages{min-height:300px;max-height:420px;overflow-y:auto;padding:.5rem 0;margin-bottom:.8rem}
  .msg{padding:.7rem .9rem;border-radius:10px;margin-bottom:.5rem;font-size:.88rem;line-height:1.55}
  .msg-user{background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.2);color:#bfdbfe;border-radius:12px 12px 2px 12px}
  .msg-agent{background:rgba(30,41,59,.8);border:1px solid #1e3a5f;color:#e2e8f0;border-radius:12px 12px 12px 2px}
  .msg-label{font-size:.7rem;font-weight:600;color:#475569;margin-bottom:.3rem}
  .chat-form{display:flex;gap:.6rem}
  .chat-input{flex:1;background:#111827;border:1px solid #1e293b;color:#e2e8f0;border-radius:8px;padding:.6rem .9rem;font-size:.88rem;outline:none}
  .chat-input:focus{border-color:#3b82f6}
  .btn{background:linear-gradient(135deg,#1d4ed8,#2563eb);color:#fff;border:none;border-radius:8px;padding:.6rem 1.2rem;cursor:pointer;font-weight:600;font-size:.85rem;transition:opacity .15s}
  .btn:hover{opacity:.9}
  .btn:disabled{opacity:.5;cursor:not-allowed}
  .suggestions{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:.8rem}
  .chip{background:#111827;border:1px solid #1e293b;color:#94a3b8;border-radius:20px;padding:.3rem .8rem;cursor:pointer;font-size:.78rem;transition:all .15s}
  .chip:hover{border-color:#3b82f6;color:#e2e8f0}
  /* Metrics table */
  table{width:100%;border-collapse:collapse;font-size:.83rem}
  th{color:#64748b;font-weight:600;text-align:left;padding:.5rem .7rem;border-bottom:1px solid #1e293b;text-transform:uppercase;font-size:.7rem;letter-spacing:.05em}
  td{padding:.55rem .7rem;border-bottom:1px solid #0f172a;color:#cbd5e1}
  tr:hover td{background:rgba(59,130,246,.04)}
  .pill{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.72rem;font-weight:600}
  .pill-good{background:rgba(34,197,94,.15);color:#4ade80}
  .pill-warn{background:rgba(245,158,11,.15);color:#fbbf24}
  .pill-bad{background:rgba(239,68,68,.15);color:#f87171}
  /* Spinner */
  .spinner{display:inline-block;width:16px;height:16px;border:2px solid #1e293b;border-top-color:#3b82f6;border-radius:50%;animation:spin .6s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  .loading-row{text-align:center;color:#475569;padding:2rem}
</style>
</head>
<body>
<nav>
  <div class="nav-brand">🧠 Growth Intelligence Agent</div>
  <div style="display:flex;align-items:center;gap:1rem">
    <span class="nav-badge" id="status-badge">⏳ Loading…</span>
    <div class="nav-links">
      <a href="/docs" target="_blank">API Docs</a>
      <a href="/api/health">Health</a>
    </div>
  </div>
</nav>

<div class="container">
  <div class="hero">
    <h1>Revenue Intelligence Platform</h1>
    <p>AI-powered growth analytics · live data · Claude-powered insights</p>
  </div>

  <!-- KPI Cards -->
  <div class="kpi-grid" id="kpi-grid">
    <div class="loading-row" style="grid-column:1/-1"><div class="spinner"></div> Loading metrics…</div>
  </div>

  <!-- Tabs -->
  <div class="tabs">
    <div class="tab active" onclick="switchTab('chat')">💬 AI Chat</div>
    <div class="tab" onclick="switchTab('metrics')">📊 Metrics</div>
    <div class="tab" onclick="switchTab('pipeline')">🔀 Pipeline</div>
    <div class="tab" onclick="switchTab('alerts')">🚨 Alerts</div>
  </div>

  <!-- Chat Tab -->
  <div class="tab-content active" id="tab-chat">
    <div class="card">
      <h3>Ask the Growth Intelligence Agent</h3>
      <div class="suggestions" id="suggestions"></div>
      <div class="chat-messages" id="chat-messages"></div>
      <div class="chat-form">
        <input class="chat-input" id="chat-input" placeholder="e.g. What is driving pipeline decline in EMEA?" onkeydown="if(event.key==='Enter')sendMessage()"/>
        <button class="btn" id="send-btn" onclick="sendMessage()">Send ↑</button>
      </div>
    </div>
  </div>

  <!-- Metrics Tab -->
  <div class="tab-content" id="tab-metrics">
    <div class="charts-row">
      <div class="card"><h3>Win Rate by Region</h3><canvas id="chart-winrate" height="200"></canvas></div>
      <div class="card"><h3>All Metrics</h3><canvas id="chart-metrics" height="200"></canvas></div>
    </div>
    <div class="card">
      <h3>Metrics Table</h3>
      <table><thead><tr><th>Metric</th><th>Segment</th><th>Value</th><th>Status</th></tr></thead>
      <tbody id="metrics-table-body"><tr><td colspan="4" class="loading-row"><div class="spinner"></div></td></tr></tbody></table>
    </div>
  </div>

  <!-- Pipeline Tab -->
  <div class="tab-content" id="tab-pipeline">
    <div class="charts-row">
      <div class="card"><h3>Pipeline by Region</h3><canvas id="chart-pipeline-region" height="220"></canvas></div>
      <div class="card"><h3>Pipeline by Stage</h3><canvas id="chart-pipeline-stage" height="220"></canvas></div>
    </div>
    <div class="card"><h3>Pipeline by Industry</h3><canvas id="chart-pipeline-industry" height="180"></canvas></div>
  </div>

  <!-- Alerts Tab -->
  <div class="tab-content" id="tab-alerts">
    <div class="card">
      <h3>Anomaly Alerts</h3>
      <div style="margin-bottom:1rem;display:flex;gap:.5rem">
        <button class="btn" onclick="loadAlerts()">🔍 Run Alert Check</button>
      </div>
      <div id="alerts-container"><p style="color:#475569;font-size:.85rem">Click "Run Alert Check" to scan metrics for anomalies.</p></div>
    </div>
  </div>
</div>

<script>
// ── State ────────────────────────────────────────────────────────────────────────
const chatHistory = [];
const SUGGESTIONS = [
  "What is our current win rate by region?",
  "Which accounts are at churn risk?",
  "How is our pipeline coverage vs target?",
  "What are the top expansion opportunities?",
  "Summarize our overall growth health",
];

// ── Tab switching ────────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',['chat','metrics','pipeline','alerts'][i]===name));
  document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  if(name==='metrics') renderMetricsCharts();
  if(name==='pipeline') loadPipeline();
}

// ── Formatting helpers ────────────────────────────────────────────────────────────
function fmtVal(name, val) {
  if(val===null||val===undefined) return '—';
  const pct=['Win Rate','Net Revenue Retention','Product Attach Rate','Seat Expansion Rate','Usage At-Risk Rate','Lead Conversion Rate'];
  const dollar=['Average Deal Size'];
  if(pct.some(k=>name.includes(k.split(' ')[0]))) return (val*100).toFixed(1)+'%';
  if(dollar.some(k=>name.includes(k.split(' ')[0]))) return '$'+Number(val).toLocaleString('en-US',{maximumFractionDigits:0});
  if(name.includes('Pipeline Coverage')) return val.toFixed(2)+'x';
  return Number(val).toLocaleString('en-US',{maximumFractionDigits:1});
}

function statusPill(name, val) {
  if(val===null) return '';
  let cls='pill-warn', label='~';
  if(name==='Win Rate'){ cls=val>=0.28?'pill-good':'pill-bad'; label=val>=0.28?'On Target':'Below'; }
  else if(name==='Pipeline Coverage'){ cls=val>=3.5?'pill-good':'pill-warn'; label=val>=3.5?'On Target':'Watch'; }
  else if(name==='Net Revenue Retention'){ cls=val>=1.2?'pill-good':'pill-bad'; label=val>=1.2?'Best-in-class':'Below'; }
  else if(name==='Usage At-Risk Rate'){ cls=val<0.10?'pill-good':'pill-bad'; label=val<0.10?'Healthy':'At Risk'; }
  else { cls='pill-warn'; label='Live'; }
  return `<span class="pill ${cls}">${label}</span>`;
}

// ── KPI Cards ────────────────────────────────────────────────────────────────────
const KPI_DEFS = [
  {name:'Win Rate',          key:'Win Rate',                   target:'≥ 28%',    fmt:'pct',  good:v=>v>=0.28},
  {name:'Pipeline Coverage', key:'Pipeline Coverage',          target:'≥ 3.5x',   fmt:'x',    good:v=>v>=3.5},
  {name:'Net Rev Retention', key:'Net Revenue Retention',      target:'≥ 120%',   fmt:'pct',  good:v=>v>=1.2},
  {name:'Avg Deal Size',     key:'Average Deal Size',          target:'Maximize', fmt:'$',    good:()=>true},
  {name:'Product Attach',    key:'Product Attach Rate',        target:'≥ 35%',    fmt:'pct',  good:v=>v>=0.35},
  {name:'Seat Expansion',    key:'Seat Expansion Rate',        target:'≥ 25%',    fmt:'pct',  good:v=>v>=0.25},
  {name:'Usage At-Risk',     key:'Usage At-Risk Rate',         target:'< 10%',    fmt:'pct',  good:v=>v<0.10},
  {name:'Sales Cycle (d)',   key:'Sales Cycle Length (days)',  target:'Minimize', fmt:'d',    good:v=>v<60},
];

async function loadKPIs() {
  try {
    const data = await fetch('/api/metrics').then(r=>r.json());
    document.getElementById('status-badge').textContent = '✅ Live Data';
    document.getElementById('status-badge').style.background = 'rgba(34,197,94,.1)';
    const byName = {};
    data.forEach(row=>{ if(row.segment==='All') byName[row.metric_name]=row.metric_value; });
    const grid = document.getElementById('kpi-grid');
    grid.innerHTML = KPI_DEFS.map(d=>{
      const v = byName[d.key];
      const display = v==null ? '—' : d.fmt==='pct' ? (v*100).toFixed(1)+'%' : d.fmt==='x' ? v.toFixed(2)+'x' : d.fmt==='$' ? '$'+Number(v).toLocaleString('en-US',{maximumFractionDigits:0}) : v.toFixed(1);
      const status = v==null ? '' : d.good(v) ? 'good' : d.name.includes('At-Risk')||d.name.includes('Retention')||d.name.includes('Win') ? 'bad' : 'warn';
      return `<div class="kpi-card ${status}">
        <div class="kpi-label">${d.name}</div>
        <div class="kpi-value">${display}</div>
        <div class="kpi-target">Target: ${d.target}</div>
      </div>`;
    }).join('');
  } catch(e) {
    document.getElementById('status-badge').textContent = '⚠️ No Data';
    document.getElementById('kpi-grid').innerHTML = '<div class="loading-row" style="grid-column:1/-1;color:#f87171">Could not load metrics. Check API.</div>';
  }
}

// ── Metrics Charts & Table ───────────────────────────────────────────────────────
let metricsChartsLoaded = false;
async function renderMetricsCharts() {
  if(metricsChartsLoaded) return;
  metricsChartsLoaded = true;
  try {
    const data = await fetch('/api/metrics').then(r=>r.json());
    const COLORS = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#a78bfa','#06b6d4','#f97316','#84cc16'];

    // Win Rate by Region
    const wrRegion = data.filter(r=>r.metric_name==='Win Rate' && r.segment!=='All');
    if(wrRegion.length) {
      new Chart(document.getElementById('chart-winrate'), {
        type:'bar', data:{
          labels: wrRegion.map(r=>r.segment),
          datasets:[{data:wrRegion.map(r=>(r.metric_value*100).toFixed(1)),backgroundColor:COLORS,borderRadius:6}]
        }, options:{plugins:{legend:{display:false}},scales:{y:{ticks:{callback:v=>v+'%'},grid:{color:'#1e293b'}},x:{grid:{color:'#1e293b'}}},responsive:true}
      });
    }

    // All Metrics bar (overall only)
    const overall = data.filter(r=>r.segment==='All');
    const names = overall.map(r=>r.metric_name.replace('Net Revenue Retention','NRR').replace('Product Attach Rate','Attach').replace('Seat Expansion Rate','Expansion').replace('Usage At-Risk Rate','At-Risk').replace('Sales Cycle Length (days)','Cycle').replace('Pipeline Coverage','Coverage').replace('Average Deal Size','Deal $').replace('Lead Conversion Rate','Lead Conv').replace('Win Rate','Win Rate'));
    new Chart(document.getElementById('chart-metrics'), {
      type:'bar', data:{
        labels: names,
        datasets:[{data:overall.map(r=>parseFloat(r.metric_value.toFixed(4))),backgroundColor:COLORS,borderRadius:6}]
      }, options:{plugins:{legend:{display:false}},scales:{y:{grid:{color:'#1e293b'}},x:{grid:{color:'#1e293b'},ticks:{maxRotation:45}}},responsive:true}
    });

    // Table
    const tbody = document.getElementById('metrics-table-body');
    tbody.innerHTML = data.map(r=>{
      const pill = statusPill(r.metric_name, r.metric_value);
      return `<tr><td>${r.metric_name}</td><td>${r.segment}</td><td style="font-family:monospace">${fmtVal(r.metric_name,r.metric_value)}</td><td>${pill}</td></tr>`;
    }).join('');
  } catch(e) { console.error(e); }
}

// ── Pipeline Charts ───────────────────────────────────────────────────────────────
let pipelineLoaded = false;
async function loadPipeline() {
  if(pipelineLoaded) return;
  pipelineLoaded = true;
  const COLORS = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#a78bfa','#06b6d4','#f97316'];
  try {
    const [region, stage, industry] = await Promise.all([
      fetch('/api/pipeline?segment=region').then(r=>r.json()),
      fetch('/api/pipeline?segment=stage').then(r=>r.json()),
      fetch('/api/pipeline?segment=industry').then(r=>r.json()),
    ]);

    const parseData = d => { try{ return typeof d.data==='string'?JSON.parse(d.data):d.data; }catch(e){return [];} };
    const rData = parseData(region), sData = parseData(stage), iData = parseData(industry);

    if(Array.isArray(rData) && rData.length) {
      new Chart(document.getElementById('chart-pipeline-region'),{
        type:'bar', data:{labels:rData.map(r=>r.segment),datasets:[{label:'Open Pipeline ($)',data:rData.map(r=>r.open_pipeline_value),backgroundColor:COLORS,borderRadius:6}]},
        options:{plugins:{legend:{display:false}},scales:{y:{ticks:{callback:v=>'$'+Number(v/1e6).toFixed(1)+'M'},grid:{color:'#1e293b'}},x:{grid:{color:'#1e293b'}}},responsive:true}
      });
    }
    if(Array.isArray(sData) && sData.length) {
      new Chart(document.getElementById('chart-pipeline-stage'),{
        type:'doughnut', data:{labels:sData.map(r=>r.segment),datasets:[{data:sData.map(r=>r.open_pipeline_value||r.total_pipeline||1),backgroundColor:COLORS}]},
        options:{plugins:{legend:{position:'right',labels:{color:'#94a3b8',boxWidth:12}}},responsive:true}
      });
    }
    if(Array.isArray(iData) && iData.length) {
      new Chart(document.getElementById('chart-pipeline-industry'),{
        type:'bar', data:{labels:iData.map(r=>r.segment),datasets:[{label:'Win Rate',data:iData.map(r=>r.win_rate*100),backgroundColor:COLORS,borderRadius:6}]},
        options:{plugins:{legend:{display:false}},scales:{y:{ticks:{callback:v=>v+'%'},grid:{color:'#1e293b'}},x:{grid:{color:'#1e293b'}}},responsive:true,indexAxis:'y'}
      });
    }
  } catch(e) { console.error(e); }
}

// ── Alerts ───────────────────────────────────────────────────────────────────────
async function loadAlerts() {
  const el = document.getElementById('alerts-container');
  el.innerHTML = '<div class="loading-row"><div class="spinner"></div> Analyzing metrics…</div>';
  try {
    const data = await fetch('/api/alerts').then(r=>r.json());
    const alerts = data.alerts || [];
    if(!alerts.length){ el.innerHTML='<p style="color:#4ade80;font-size:.88rem">✅ All metrics within normal range.</p>'; return; }
    const counts = {High:0,Medium:0,Low:0};
    alerts.forEach(a=>counts[a.severity]=(counts[a.severity]||0)+1);
    el.innerHTML = `<div style="display:flex;gap:1rem;margin-bottom:1rem">
      <span style="color:#f87171">🔴 ${counts.High||0} High</span>
      <span style="color:#fbbf24">🟡 ${counts.Medium||0} Medium</span>
      <span style="color:#60a5fa">🔵 ${counts.Low||0} Low</span>
    </div>` + alerts.map(a=>{
      const sev=a.severity.toLowerCase();
      const sign=a.change_pct>0?'+':'';
      return `<div class="alert-item alert-${sev}">
        <span class="sev-badge sev-${sev}">${a.severity}</span>
        <div class="alert-title">${a.direction} ${a.metric} <span style="color:#64748b;font-size:.78rem">· ${a.segment}</span></div>
        <div class="alert-meta">${a.is_positive?'✅':'❌'} ${sign}${a.change_pct}% &nbsp;·&nbsp; ${a.previous_value} → ${a.current_value}</div>
        <div class="alert-action">💡 ${a.recommended_action}</div>
      </div>`;
    }).join('');
  } catch(e) { el.innerHTML=`<p style="color:#f87171">Error: ${e.message}</p>`; }
}

// ── Chat ─────────────────────────────────────────────────────────────────────────
function addMessage(role, text) {
  const el = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg msg-'+role;
  div.innerHTML = `<div class="msg-label">${role==='user'?'👤 You':'🧠 Agent'}</div>${escHtml(text)}`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function escHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br>'); }

async function sendMessage(text) {
  const input = document.getElementById('chat-input');
  const question = text || input.value.trim();
  if(!question) return;
  input.value = '';
  const btn = document.getElementById('send-btn');
  btn.disabled = true;
  addMessage('user', question);

  const history = chatHistory.slice(-6).map((m,i,a)=>i%2===0&&i+1<a.length?[a[i].text,a[i+1].text]:null).filter(Boolean);
  chatHistory.push({role:'user',text:question});

  const thinkingDiv = document.createElement('div');
  thinkingDiv.className = 'msg msg-agent';
  thinkingDiv.innerHTML = '<div class="msg-label">🧠 Agent</div><div class="spinner"></div> Reasoning…';
  document.getElementById('chat-messages').appendChild(thinkingDiv);

  try {
    const res = await fetch('/api/ask', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,chat_history:history})});
    const data = await res.json();
    thinkingDiv.innerHTML = `<div class="msg-label">🧠 Agent</div>${escHtml(data.answer||data.detail||'No response')}`;
    chatHistory.push({role:'agent',text:data.answer||''});
  } catch(e) {
    thinkingDiv.innerHTML = `<div class="msg-label">🧠 Agent</div><span style="color:#f87171">Error: ${e.message}</span>`;
  }
  btn.disabled = false;
  document.getElementById('chat-messages').scrollTop = 99999;
}

// ── Suggestion chips ─────────────────────────────────────────────────────────────
document.getElementById('suggestions').innerHTML = SUGGESTIONS.map(s=>
  `<span class="chip" onclick="sendMessage(${JSON.stringify(s)})">${s.substring(0,38)}…</span>`
).join('');

// ── Init ─────────────────────────────────────────────────────────────────────────
loadKPIs();
</script>
</body>
</html>"""

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

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse(content=DASHBOARD_HTML)


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
