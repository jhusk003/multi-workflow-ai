# SELLER ASSIST COHESIVE USER SHADER MERGE v33
# SELLER ASSIST SHARED BRAINS v23
# SELLER ASSIST EXPLORE MODE v21
"""Seller Assist v16.1: Operable Whimsical Kawaii Edition.
Features: Fully Operable Clickable Kawaii Character & Building Cards, True Transparent PNG Illustrations,
Global CSV Sync, SQLite Persistence, Marketplace Fee Simulator, 1-Click Exports, and XP Gamification.
"""
import asyncio
import base64
import csv
import io
import json
import math
import os
import random
import re
import sqlite3
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
from seller_fast_voice_v30 import schedule as _sa_schedule_voice, collect as _sa_collect_voice, is_pending as _sa_voice_pending
from seller_portraits import embedded_portrait
from seller_character_brain import reply as _sa_shared_brain_reply, BrainUnavailable as _sa_brain_unavailable
from seller_ai_workflows import get_prefs as _sa_get_prefs, specialist_room_tools as _sa_specialist_room_tools
from seller_business_engine import (
    inventory_report as _sa_inventory_report,
    purchase_order as _sa_purchase_order,
    bulk_listing_csv as _sa_bulk_listing_csv,
    estimate_pl as _sa_estimate_pl,
    answer_from_shop_data as _sa_answer_from_shop_data,
    parse_inventory as _sa_parse_inventory,
)

try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    sentry_sdk = None
    SENTRY_AVAILABLE = False

st.set_page_config(
    page_title="Seller Assist · Whimsical Kawaii Edition",
    page_icon="🌸",
    layout="wide",
)

# SELLER ASSIST SETTINGS DATA v21.2 — old session selections remain useful.
if st.session_state.get("nav_selector") == "📁 Shop Data":
    st.session_state["nav_selector"] = "⚙️ Settings & Data"
    st.session_state["sa_settings_section_request"] = "📁 Data & Uploads"
elif st.session_state.get("nav_selector") == "⚙️ Settings":
    st.session_state["nav_selector"] = "⚙️ Settings & Data"

DB_FILE = "seller_assist.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, val TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, done INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS inventory (sku TEXT PRIMARY KEY, product_name TEXT, category TEXT, unit_cost REAL, retail_price REAL, stock INTEGER, weekly_sales INTEGER, lead_days INTEGER)""")
    conn.commit()
    conn.close()

init_db()

def db_load_budgets():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT key, val FROM settings WHERE key IN ('daily', 'monthly', 'annual', 'xp')")
    rows = c.fetchall()
    conn.close()
    data = {k: float(v) for k, v in rows}
    return {
        "daily": data.get("daily", 950.0),
        "monthly": data.get("monthly", 28500.0),
        "annual": data.get("annual", 342000.0),
        "xp": int(data.get("xp", 500))
    }

def db_save_budget(key, val):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, val) VALUES (?, ?)", (key, str(val)))
    conn.commit()
    conn.close()

def db_load_todos():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, task, done FROM todos")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "task": r[1], "done": bool(r[2])} for r in rows]

def db_save_todo_status(todo_id, done):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE todos SET done = ? WHERE id = ?", (1 if done else 0, todo_id))
    conn.commit()
    conn.close()

def db_add_todo(task_text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO todos (task, done) VALUES (?, 0)", (task_text,))
    conn.commit()
    conn.close()

SAMPLE_SELLER_CSV = """sku,product_name,category,unit_cost_usd,retail_price_usd,stock_on_hand,weekly_units_sold,supplier_lead_days,return_rate_pct
SLR-101,Hand-Poured Lavender Soy Candle 8oz,Home Fragrance,4.20,22.00,14,19,10,1.2
SLR-102,Custom Engraved Walnut Cutting Board,Kitchen & Dining,11.50,58.00,8,9,14,0.8
SLR-103,Minimalist Gold Vermeil Stacking Ring,Jewelry,6.80,36.00,42,15,7,3.5
SLR-104,Linen Cross-Back Apron (Sage Green),Apparel & Textiles,7.90,44.00,5,11,12,2.1
SLR-105,Botanical Pressed Flower Resin Coaster Set,Home Decor,5.10,32.00,29,8,9,1.5
SLR-106,Ceramic Matcha Whisk Holder (Speckled),Ceramics,3.80,26.00,6,14,15,0.5
"""

SAMPLE_DASHBOARD_CSV = """Day,Sales,Profit,Daily_Budget
Mon,1200,780,950
Tue,1450,940,950
Wed,1320,850,950
Thu,1680,1100,950
Fri,1950,1280,950
Sat,2400,1560,950
Sun,2100,1370,950
"""

MARKETPLACE_FEES = {
    "Etsy (Standard 9.5% + $0.20)": 0.095,
    "Shopify Payments (2.9% + $0.30)": 0.029,
    "eBay Managed Payments (13.25%)": 0.1325,
    "Amazon Handmade (15%)": 0.15,
}

CURRENCY_RATES = {
    "USD ($)": (1.0, "$"),
    "EUR (€)": (0.92, "€"),
    "GBP (£)": (0.79, "£"),
    "CAD (C$)": (1.36, "C$"),
    "AUD (A$)": (1.52, "A$"),
}

ASSISTANTS = {
    "Level 1: Inventory Lab": {
        "name": "Morgan", "level": "LEVEL 1", "color": "#ff70a6",
        "voice": "en-US-EmmaNeural", "eleven_voice_id": "EXAVITQu4vr4xnSDxMaL",
        "photo": "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?auto=format&fit=crop&w=900&q=85",
        "tone": "cheerful, analytical and supportive",
        "specialty": "Wilson EOQ and reorder-point calculations, interpreting stock and safety-stock estimates.",
    },
    "Level 2: Listing Studio": {
        "name": "Jordan", "level": "LEVEL 2", "color": "#70d6ff",
        "voice": "en-US-AndrewNeural", "eleven_voice_id": "TxGEqnHWrfWFTfGW9XjX",
        "photo": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=900&q=85",
        "tone": "creative, bubbly and colorful",
        "specialty": "Etsy/Shopify descriptions, 13-tag Etsy SEO, whimsical branding.",
    },
    "Level 3: Ops & PO Room": {
        "name": "Taylor", "level": "LEVEL 3", "color": "#ffd166",
        "voice": "en-US-ChristopherNeural", "eleven_voice_id": "pNInz6obpgDQGcFmaJgB",
        "photo": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=900&q=85",
        "tone": "organized, friendly and efficient",
        "specialty": "Batch scheduling, automated EOQ purchase order generation.",
    },
    "Level 4: Finance & Tax Desk": {
        "name": "Alex", "level": "LEVEL 4", "color": "#06d6a0",
        "voice": "en-US-AvaNeural", "eleven_voice_id": "21m00Tcm4TlvDq8ikWAM",
        "photo": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=900&q=85",
        "tone": "precise, encouraging and helpful",
        "specialty": "Product-level estimated profit, costs, returns, budgeting and educational tax questions.",
    },
}

# Keep the supplied portrait shader; replace only missing remote image dependencies.
ASSISTANTS['Level 2: Listing Studio']['photo'] = embedded_portrait('jordan')
ASSISTANTS['Level 3: Ops & PO Room']['photo'] = embedded_portrait('taylor')
ASSISTANTS['Level 4: Finance & Tax Desk']['voice'] = 'en-US-JennyNeural'
ASSISTANTS['Level 1: Inventory Lab']['voice'] = 'en-US-EmmaNeural'


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&family=Quicksand:wght@600;700&display=swap');

.stApp {
    background-color: #f3ebff;
    background-image: 
        linear-gradient(rgba(209, 196, 233, 0.4) 1.5px, transparent 1.5px),
        linear-gradient(90deg, rgba(209, 196, 233, 0.4) 1.5px, transparent 1.5px);
    background-size: 32px 32px;
    color: #2b2d42;
    font-family: 'Fredoka', sans-serif;
}

[data-testid="stSidebar"] {
    background: #e8def8 !important;
    border-right: 3px solid #b39ddb;
    color: #2b2d42 !important;
}

[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: #4a154b !important;
    font-weight: 600 !important;
}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 98vw !important;
}

/* Whimsical Kawaii Header */
.kawaii-header {
    background: linear-gradient(135deg, #fff9c4 0%, #e1f5fe 50%, #fce4ec 100%);
    border: 3px solid #7e57c2;
    border-radius: 28px;
    padding: 22px 28px;
    margin-bottom: 24px;
    box-shadow: 6px 6px 0px #b39ddb;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
}

.kawaii-header h1 {
    font-family: 'Quicksand', sans-serif;
    font-size: clamp(1.2rem, 2.2vw, 1.7rem);
    color: #512da8;
    margin: 0 0 6px 0;
    font-weight: 700;
}

.kawaii-header p {
    color: #5e35b1;
    font-size: 0.95rem;
    margin: 0;
    font-weight: 500;
}

.kawaii-badge {
    background: #ff4081;
    color: #ffffff !important;
    font-family: 'Quicksand', sans-serif;
    font-size: 0.75rem;
    padding: 8px 16px;
    border: 2px solid #fff;
    border-radius: 20px;
    display: inline-block;
    font-weight: 700;
    box-shadow: 3px 3px 0px #7e57c2;
}

/* Kawaii Rounded Cards */
.kawaii-card {
    background: #ffffff;
    border: 3px solid #7e57c2;
    border-radius: 24px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 5px 5px 0px #b39ddb;
    transition: transform 0.15s ease;
}

.kawaii-card:hover {
    transform: translateY(-2px);
}

.kawaii-card h4 {
    font-family: 'Quicksand', sans-serif;
    font-size: 0.8rem;
    color: #5e35b1;
    text-transform: uppercase;
    margin: 0 0 8px 0;
    letter-spacing: 0.5px;
}

.kawaii-card .big-num {
    font-family: 'Quicksand', sans-serif;
    font-size: 1.65rem;
    font-weight: 700;
    color: #311b92;
    margin: 0 0 4px 0;
}

.kawaii-card small {
    color: #7c4dff;
    font-size: 0.82rem;
    font-weight: 600;
}

.kawaii-panel {
    background: #ffffff;
    border: 3px solid #7e57c2;
    border-radius: 24px;
    padding: 22px;
    margin-bottom: 20px;
    box-shadow: 6px 6px 0px #b39ddb;
}

/* Fun Pill Buttons */
.stButton > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #ff4081, #7c4dff) !important;
    color: #ffffff !important;
    border: 2.5px solid #2b2d42 !important;
    border-radius: 30px !important;
    font-family: 'Quicksand', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    padding: 10px 22px !important;
    box-shadow: 4px 4px 0px #2b2d42 !important;
    transition: all 0.15s ease !important;
}

.stButton > button[kind="primary"]:hover {
    transform: translate(-2px, -2px);
    box-shadow: 6px 6px 0px #2b2d42 !important;
}

.stButton > button[kind="secondary"] {
    background: #e0f7fa !important;
    color: #006064 !important;
    border: 2.5px solid #00acc1 !important;
    border-radius: 30px !important;
    font-weight: 700 !important;
    box-shadow: 4px 4px 0px #00acc1 !important;
}

div[data-testid="stForm"] {
    background: #ffffff;
    border: 3px solid #7e57c2;
    border-radius: 24px;
    padding: 18px;
    box-shadow: 5px 5px 0px #b39ddb;
}
</style>
""", unsafe_allow_html=True)

from premium_theme import apply_premium_theme
apply_premium_theme()

STATE_KEY = "seller_assist_kawaii_workspaces"

def new_workspace():
    return {
        "messages": [], "last_reply": "", "last_audio": "", "word_timings": [],
        "reply_id": "", "file_text": SAMPLE_SELLER_CSV, "file_name": "global_sync.csv", "tabpfn_report": "",
        "schedule_c_pl": "", "generated_po": "", "exported_listing_csv": "",
        "last_model_used": "No AI model used yet"
    }

def ensure_workspaces(session):
    if STATE_KEY not in session:
        session[STATE_KEY] = {name: new_workspace() for name in ASSISTANTS}
    for name in ASSISTANTS:
        session[STATE_KEY].setdefault(name, new_workspace())
    
    db_b = db_load_budgets()
    if "dash_budgets" not in session:
        session["dash_budgets"] = {"daily": db_b["daily"], "monthly": db_b["monthly"], "annual": db_b["annual"]}
    if "seller_xp" not in session:
        session["seller_xp"] = db_b["xp"]
    if "telemetry" not in session:
        session["telemetry"] = {"calls": 0, "last_latency_ms": 0, "errors": 0}
    return session[STATE_KEY]

workspaces = ensure_workspaces(st.session_state)

def secret(name):
    val = os.getenv(name, "").strip()
    if val:
        return val
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""

def add_xp(amount):
    st.session_state["seller_xp"] += amount
    db_save_budget("xp", st.session_state["seller_xp"])

def fetch_serpapi_competitor_pricing(query):
    """Fetch actual SerpApi results, never label example prices live."""
    api_key = secret('SERPAPI_API_KEY')
    if not api_key:
        return 'Live competitor prices unavailable: configure SERPAPI_API_KEY under Render secrets. No prices have been fetched.'
    q = str(query or '').strip()
    if not q:
        return 'Enter a product to research.'
    try:
        url = 'https://serpapi.com/search.json?engine=google_shopping&q=' + urllib.parse.quote(q) + '&api_key=' + urllib.parse.quote(api_key)
        request = urllib.request.Request(url,headers={'User-Agent':'SellerAssist/1.0'})
        with urllib.request.urlopen(request,timeout=15) as response:
            payload = json.load(response)
        results = payload.get('shopping_results',[])
        if not results:
            return 'No shopping results returned by SerpApi for this query.'
        lines = [f'### Live SerpApi results for {q} (verify before pricing decisions)']
        for item in results[:8]:
            title = str(item.get('title') or 'Untitled').replace('|','/')
            price = str(item.get('price') or 'Not stated')
            source = str(item.get('source') or 'Unspecified source')
            lines.append(f'- **{title}** — {price} ({source})')
        return '\n'.join(lines)
    except urllib.error.HTTPError as exc:
        return f'Live SerpApi request failed (HTTP {exc.code}). Check your key, quota, or query.'
    except Exception:
        return 'Live SerpApi request failed. Please retry or check connectivity.'



# SELLER ASSIST BUSINESS ENGINE v22 — keep previous app.py function interfaces.
def _sa_inventory_source(workspace=None):
    """Inventory upload from Settings & Data wins; financial uploads do not replace stock."""
    if st.session_state.get('sa_shared_kind') == 'inventory':
        value = st.session_state.get('sa_shared_csv', '')
        if value:
            return value
    if isinstance(workspace, dict):
        candidate = workspace.get('file_text', '')
        if isinstance(candidate, str):
            try:
                _sa_parse_inventory(candidate)
                return candidate
            except ValueError:
                pass
    return SAMPLE_SELLER_CSV

def run_tabpfn_inventory_forecast(csv_text, fee_rate=0.095):
    """Wilson EOQ and reorder-point estimates; no TabPFN inference performed."""
    try:
        return _sa_inventory_report(csv_text, fee_rate)
    except ValueError as error:
        return f"Invalid inventory CSV: {error}"

def generate_schedule_c_pl(csv_text, fee_rate=0.095):
    """Educational product-level P&L estimate; not tax preparation."""
    try:
        return _sa_estimate_pl(csv_text, fee_rate)
    except ValueError as error:
        return f"Cannot estimate P&L: {error}"

def generate_supplier_po(workspace):
    """Compatibility interface: always returns a text report."""
    try:
        report, tasks = _sa_purchase_order(_sa_inventory_source(workspace))
        st.session_state['sa_latest_po_tasks'] = tasks
        return report
    except ValueError as error:
        st.session_state['sa_latest_po_tasks'] = []
        return f"Cannot build purchase order: {error}"

def generate_shopify_etsy_listing_csv(title, price=None, category=None):
    """Compatible with legacy title/price/category and new full-inventory CSV."""
    if price is None and category is None:
        source = title
    else:
        buf = io.StringIO(newline='')
        writer = csv.writer(buf)
        writer.writerow(['sku', 'product_name', 'category', 'unit_cost_usd', 'retail_price_usd', 'stock_on_hand', 'weekly_units_sold', 'supplier_lead_days', 'return_rate_pct'])
        writer.writerow(['EXAMPLE-001', title, category or 'General', '0', price or '0', '25', '0', '7', '0'])
        source = buf.getvalue()
    try:
        output, warnings = _sa_bulk_listing_csv(source)
        st.session_state['sa_latest_listing_warnings'] = warnings
        return output
    except ValueError as error:
        st.session_state['sa_latest_listing_warnings'] = [str(error)]
        return ''

def run_ai(mode, workspace, prompt, reference=""):
    # SELLER ASSIST SHARED BRAINS v23 — same brain and history as workflow pages.
    t0 = time.time()
    try:
        response, provider = _sa_shared_brain_reply(
            mode, ASSISTANTS[mode], workspace, prompt,
            reference, _sa_get_prefs(), secret,
        )
        workspace['last_model_used'] = provider
        return response
    except _sa_brain_unavailable as error:
        st.session_state['telemetry']['errors'] += 1
        return 'AI generation unavailable: ' + str(error)
    finally:
        st.session_state['telemetry']['calls'] += 1
        st.session_state['telemetry']['last_latency_ms'] = int((time.time()-t0)*1000)


def neural_speech(text, voice, eleven_id=''):
    """Compatibility shim. Preferred runtime uses the shared asynchronous voice worker."""
    from seller_voice_v29 import synthesize
    cfg={'name':'Alex' if voice == 'en-US-JennyNeural' else 'Assistant', 'voice':voice, 'eleven_voice_id':eleven_id}
    return synthesize(text,cfg,secret)[0]

def process_message(mode, workspace, prompt, ref=False):
    prompt = (prompt or '').strip()
    if ref:
        uploaded = st.session_state.get('sa_shared_csv', '')
        ref_text = ('USER-UPLOADED '+st.session_state.get('sa_shared_kind','shop').upper()+' CSV:\n'+uploaded) if uploaded else ('BUILT-IN SAMPLE INVENTORY (NOT USER DATA):\n'+SAMPLE_SELLER_CSV)
    else:
        ref_text = ''
    if not prompt and not ref_text:
        return
    reply = run_ai(mode, workspace, prompt, ref_text)
    now = datetime.now().strftime('%b %d · %I:%M %p')
    workspace.setdefault('messages', []).extend([
        {'role': 'user', 'content': prompt or 'Review uploaded file.', 'time': now},
        {'role': 'assistant', 'content': reply, 'time': now},
    ])
    workspace['last_reply'] = reply
    workspace['reply_id'] = uuid.uuid4().hex
    if reply.startswith('AI generation unavailable:'):
        workspace['last_audio'] = ''
        workspace['last_audio_mime'] = ''
        workspace['last_audio_error'] = 'No successful AI reply to narrate.'
    else:
        _sa_schedule_voice(workspace, reply, ASSISTANTS[mode], secret)

def render_dashboard_charts(periods, sales_list, profit_list, daily_budget, sku_labels, sku_stock, sku_sales, sym):
    payload = {
        "periods": periods,
        "sales": sales_list,
        "profit": profit_list,
        "dailyBudget": daily_budget,
        "skuLabels": sku_labels,
        "skuStock": sku_stock,
        "skuSales": sku_sales,
        "sym": sym,
    }
    safe_json = json.dumps(payload)
    html_code = DASHBOARD_CHARTS_HTML.replace("__CHART_DATA__", safe_json)
    components.html(html_code, height=360, scrolling=False)

DASHBOARD_CHARTS_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600&family=Quicksand:wght@600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; font-family: 'Fredoka', sans-serif; color: #2b2d42; overflow: hidden; }
  .grid { display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 16px; height: 350px; }
  .card {
    background: #ffffff; border: 3px solid #7e57c2; border-radius: 20px;
    padding: 16px; box-shadow: 4px 4px 0px #b39ddb; display: flex; flex-direction: column;
  }
  .title-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .title { font-family: 'Quicksand', sans-serif; font-size: 11px; color: #512da8; font-weight: 700; }
  .legend { display: flex; gap: 12px; font-size: 11px; font-weight: 600; color: #5e35b1; }
  .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
  canvas { width: 100%; height: 280px; display: block; }
</style>
</head>
<body>
<div class="grid">
  <div class="card">
    <div class="title-row">
      <span class="title">📈 REVENUE vs. PROFIT vs. BUDGET</span>
      <div class="legend">
        <span><i class="dot" style="background:#00bcd4;"></i>Sales</span>
        <span><i class="dot" style="background:#00e676;"></i>Profit</span>
        <span><i class="dot" style="background:#ff4081;"></i>Budget</span>
      </div>
    </div>
    <canvas id="revCanvas"></canvas>
  </div>
  <div class="card">
    <div class="title-row">
      <span class="title">📦 STOCK vs. WEEKLY VELOCITY</span>
      <div class="legend">
        <span><i class="dot" style="background:#ffd600;"></i>Stock</span>
        <span><i class="dot" style="background:#ff4081;"></i>Sold</span>
      </div>
    </div>
    <canvas id="skuCanvas"></canvas>
  </div>
</div>
<script>
(() => {
  const D = __CHART_DATA__;
  function setupCanvas(id) {
    const c = document.getElementById(id);
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = c.getBoundingClientRect();
    c.width = Math.max(300, rect.width * dpr);
    c.height = Math.max(220, rect.height * dpr);
    const ctx = c.getContext('2d');
    ctx.scale(dpr, dpr);
    return { ctx, w: rect.width, h: rect.height };
  }

  function drawRevChart() {
    const { ctx, w, h } = setupCanvas('revCanvas');
    ctx.clearRect(0, 0, w, h);
    const padL = 52, padR = 16, padT = 18, padB = 34;
    const cw = w - padL - padR, ch = h - padT - padB;
    const allVals = [...D.sales, ...D.profit, D.dailyBudget * 1.1, 100];
    const maxV = Math.max(...allVals) * 1.12;

    ctx.strokeStyle = 'rgba(126, 87, 194, 0.12)';
    ctx.fillStyle = '#5e35b1';
    ctx.font = '500 10px Quicksand';
    for (let i = 0; i <= 4; i++) {
      const y = padT + ch - (i / 4) * ch;
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + cw, y); ctx.stroke();
      const val = Math.round((i / 4) * maxV);
      ctx.fillText(D.sym + val, 4, y + 3);
    }

    const n = Math.max(1, D.periods.length);
    const groupW = cw / n;
    const barW = Math.min(20, groupW * 0.34);

    D.periods.forEach((label, i) => {
      const gx = padL + i * groupW + groupW * 0.16;
      const sVal = D.sales[i] || 0;
      const pVal = D.profit[i] || 0;
      const sH = (sVal / maxV) * ch;
      const pH = (pVal / maxV) * ch;

      ctx.fillStyle = '#00bcd4';
      ctx.fillRect(gx, padT + ch - sH, barW, sH);

      ctx.fillStyle = '#00e676';
      ctx.fillRect(gx + barW + 3, padT + ch - pH, barW, pH);

      ctx.fillStyle = '#4a154b';
      ctx.font = '600 10px Fredoka';
      ctx.fillText(String(label).slice(0, 6), gx, padT + ch + 18);
    });

    if (D.dailyBudget > 0) {
      const by = padT + ch - Math.min(ch, (D.dailyBudget / maxV) * ch);
      ctx.strokeStyle = '#ff4081';
      ctx.lineWidth = 2.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(padL, by); ctx.lineTo(padL + cw, by); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#ff4081';
      ctx.font = '700 10px Quicksand';
      ctx.fillText('Target: ' + D.sym + Math.round(D.dailyBudget), padL + 8, Math.max(14, by - 6));
    }
  }

  function drawSkuChart() {
    const { ctx, w, h } = setupCanvas('skuCanvas');
    ctx.clearRect(0, 0, w, h);
    const padL = 38, padR = 14, padT = 18, padB = 34;
    const cw = w - padL - padR, ch = h - padT - padB;
    const maxV = Math.max(...D.skuStock, ...D.skuSales, 20) * 1.15;

    ctx.strokeStyle = 'rgba(126, 87, 194, 0.12)';
    ctx.fillStyle = '#5e35b1';
    ctx.font = '500 10px Quicksand';
    for (let i = 0; i <= 4; i++) {
      const y = padT + ch - (i / 4) * ch;
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + cw, y); ctx.stroke();
      ctx.fillText(Math.round((i / 4) * maxV) + 'u', 4, y + 3);
    }

    const n = Math.max(1, D.skuLabels.length);
    const groupW = cw / n;
    const barW = Math.min(16, groupW * 0.34);

    D.skuLabels.forEach((sku, i) => {
      const gx = padL + i * groupW + groupW * 0.16;
      const stVal = D.skuStock[i] || 0;
      const slVal = D.skuSales[i] || 0;
      const stH = (stVal / maxV) * ch;
      const slH = (slVal / maxV) * ch;

      ctx.fillStyle = '#ffd600';
      ctx.fillRect(gx, padT + ch - stH, barW, stH);

      ctx.fillStyle = '#ff4081';
      ctx.fillRect(gx + barW + 3, padT + ch - slH, barW, slH);

      ctx.fillStyle = '#4a154b';
      ctx.font = '600 9.5px Fredoka';
      ctx.fillText(String(sku).slice(0, 7), gx - 2, padT + ch + 18);
    });
  }

  drawRevChart();
  drawSkuChart();
  window.addEventListener('resize', () => { drawRevChart(); drawSkuChart(); });
})();
</script>
</body>
</html>
"""

def render_avatar(assistant, workspace):
    """Render original user-supplied mouth/eye shader; collect audio asynchronously."""
    def _display():
        if _sa_collect_voice(workspace):
            st.rerun()
        payload = {
            'name': assistant['name'], 'room': assistant['level'], 'accent': assistant['color'],
            'photo': assistant['photo'], 'text': workspace.get('last_reply') or
                f"Hi! I'm {assistant['name']} in {assistant['level']}. How can I help today?",
            'audio': workspace.get('last_audio',''),
            'audioMime': workspace.get('last_audio_mime') or 'audio/mpeg',
            'audioError': workspace.get('last_audio_error',''),
            'pending': _sa_voice_pending(workspace),
            'replyId': workspace.get('reply_id',''),
        }
        safe = json.dumps(payload, ensure_ascii=False).replace('<', r'\u003c').replace('>', r'\u003e').replace('&', r'\u0026')
        components.html(AVATAR_HTML.replace('__PAYLOAD__', safe), height=635, scrolling=False)
    if _sa_voice_pending(workspace) and hasattr(st,'fragment'):
        st.fragment(run_every='1s')(_display)()
    else:
        _display()


def _sa_voice_status(mode, workspace):
    if _sa_voice_pending(workspace):
        st.caption('AI reply ready. Preparing the generated character voice in the background…')
    elif workspace.get('last_audio'):
        st.caption('Voice: ' + workspace.get('last_audio_provider','generated audio'))
    elif workspace.get('last_reply') and not workspace['last_reply'].startswith('AI generation unavailable:'):
        st.caption('Voice could not be generated. The character mouth/eye preview still works independently.')
        if workspace.get('last_audio_error'):
            with st.expander('Voice diagnostics'):
                st.caption(workspace['last_audio_error'])
        if st.button('Regenerate voice for this reply',key='sa_merge_voice_'+mode):
            _sa_schedule_voice(workspace, workspace['last_reply'], ASSISTANTS[mode], secret)
            st.rerun()

AVATAR_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600&family=Quicksand:wght@600;700&display=swap" rel="stylesheet">
<style>
  :root { --accent: #ff4081; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { color: #2b2d42; background: transparent; font: 12px 'Fredoka', sans-serif; overflow: hidden; }
  .panel {
    height: 625px; border: 3px solid #7e57c2; border-radius: 24px; overflow: hidden;
    background: #ffffff; display: flex; flex-direction: column; box-shadow: 6px 6px 0px #b39ddb;
  }
  .stage { height: 445px; position: relative; background: linear-gradient(135deg, #e0f7fa 0%, #ede7f6 100%); overflow: hidden; }
  #portraitFallback {position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:linear-gradient(135deg,#e0f7fa,#ede7f6);}
  #glCanvas { position:relative; width: 100%; height: 100%; display: block; }
  .plate {
    position: absolute; top: 12px; left: 12px; border: 2px solid #7e57c2; background: #fff; color: #512da8;
    padding: 6px 14px; font-weight: 700; font-size: 11px; border-radius: 16px; font-family: 'Quicksand', sans-serif;
    box-shadow: 3px 3px 0px #ff4081;
  }
  .live-pill {
    position: absolute; top: 12px; right: 12px; background: #00e676; color: #fff;
    border: 2px solid #2b2d42; padding: 5px 12px; font-size: 10px; font-weight: 700; border-radius: 16px;
    box-shadow: 2px 2px 0px #2b2d42;
  }
  .controls { padding: 12px 16px; display: flex; flex-direction: column; gap: 8px; background: #f3e5f5; border-top: 3px solid #7e57c2; }
  .buttons { display: flex; gap: 8px; justify-content: space-between; align-items: center; }
  button {
    border: 2.5px solid #2b2d42; background: #ff4081; color: #ffffff; font-weight: 700;
    font-size: 11px; cursor: pointer; padding: 8px 14px; border-radius: 20px; font-family: 'Quicksand', sans-serif;
    box-shadow: 3px 3px 0px #2b2d42;
  }
  button:hover { transform: translate(-1px, -1px); box-shadow: 4px 4px 0px #2b2d42; }
  button.alt { background: #00bcd4; color: #ffffff; }
  #voice { height: 30px; width: 100%; accent-color: #ff4081; }
  .status-bar { display: flex; justify-content: space-between; font-size: 10.5px; color: #5e35b1; font-weight: 600; }
  #caption { font-size: 11.5px; color: #2b2d42; font-weight: 600; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; }
</style>
</head>
<body>
<div class="panel">
  <div class="stage">
    <img id="portraitFallback" aria-hidden="true" alt=""/>
    <canvas id="glCanvas"></canvas>
    <div class="plate" id="plate"></div>
    <div class="live-pill">● KAWAII AI</div>
  </div>
  <div class="controls">
    <div class="buttons">
      <div style="display:flex;gap:8px;">
        <button id="speak" type="button">▶ Play Audio Voice</button>
        <button class="alt" id="stop" type="button">■ Stop</button>
        <button class="alt" id="preview" type="button">Preview lips</button>
      </div>
    </div>
    <audio id="voice" controls preload="auto"></audio>
    <div class="status-bar"><span id="status">Audio Ready</span><span>Kawaii Lip-Sync Active</span></div>
    <div id="caption"></div>
  </div>
</div>
<script>
(() => {
  'use strict';
  const C = __PAYLOAD__;
  const $= id => document.getElementById(id);$('plate').textContent = C.name + ' · ' + C.room;
  $('caption').textContent = C.text;
  $('portraitFallback').src = C.photo;

  const sound = $('voice');
  const PRESETS = {
    Morgan: { mouthCenter: [0.50, 0.692], mouthWidth: 0.155, leftEye: [0.395, 0.478], rightEye: [0.605, 0.478], eyeRadius: [0.048, 0.026] },
    Jordan: { mouthCenter: [0.50, 0.685], mouthWidth: 0.152, leftEye: [0.400, 0.468], rightEye: [0.600, 0.468], eyeRadius: [0.048, 0.025] },
    Taylor: { mouthCenter: [0.50, 0.690], mouthWidth: 0.158, leftEye: [0.400, 0.472], rightEye: [0.600, 0.472], eyeRadius: [0.048, 0.025] },
    Alex:   { mouthCenter: [0.50, 0.695], mouthWidth: 0.152, leftEye: [0.395, 0.480], rightEye: [0.605, 0.480], eyeRadius: [0.048, 0.026] }
  };
  let landmarks = PRESETS[C.name] || PRESETS.Morgan;
  const canvas = $('glCanvas'), gl = canvas.getContext('webgl', { alpha: false, antialias: true });
  if (!gl) {canvas.style.display='none';$('status').textContent='WebGL unavailable: showing the portrait without animation.';return;}

  const VS = `attribute vec2 aPos; attribute vec2 aUv; varying vec2 vUv; uniform float uZoom; uniform vec2 uHeadSway; void main() { vUv = aUv; vec2 pos = aPos * uZoom + uHeadSway * smoothstep(0.9,0.1,aUv.y); gl_Position = vec4(pos, 0.0, 1.0); }`;
  const FS = `
    precision highp float; varying vec2 vUv; uniform sampler2D uTex; uniform vec2 uCanvasSize; uniform float uMediaAspect;
    uniform vec2 uMouthCenter; uniform float uMouthWidth; uniform vec2 uLeftEye, uRightEye, uEyeRadius;
    uniform float uMouthOpen, uBlink;
    void main() {
      vec2 uv = vUv;
      float sa = uCanvasSize.x / max(1.0, uCanvasSize.y);
      float r = sa / max(0.1, uMediaAspect);
      if (r > 1.0) uv.y = (uv.y - 0.42) / r + 0.42; else uv.x = (uv.x - 0.50) * r + 0.50;
      uv = clamp(uv, 0.002, 0.998); vec2 su = uv;
      vec2 dL = (uv - uLeftEye) / uEyeRadius, dR = (uv - uRightEye) / uEyeRadius;
      if (uBlink > 0.005) {
        if (dot(dL,dL)<1.0) su.y -= (1.0-dot(dL,dL))*uBlink*uEyeRadius.y*0.85;
        if (dot(dR,dR)<1.0) su.y -= (1.0-dot(dR,dR))*uBlink*uEyeRadius.y*0.85;
      }
      float openAmt = clamp(uMouthOpen, 0.0, 0.95);
      float hw = max(0.044, uMouthWidth*0.52), hh = max(0.036, uMouthWidth*0.46);
      float dx = (uv.x - uMouthCenter.x)/hw, dy = (uv.y - uMouthCenter.y)/hh;
      float sc = max(0.0, 1.0 - dx*dx);
      float upperY = -openAmt*0.18*sc*sqrt(sc), lowerY = openAmt*0.58*sc*sqrt(sc);
      if (dy >= 0.0) {
        su.y -= openAmt*hh*0.78*exp(-1.15*dx*dx)*exp(-0.52*dy*dy);
      } else {
        su.y += openAmt*hh*0.20*exp(-1.25*dx*dx)*exp(-2.4*dy*dy);
      }
      vec4 col = texture2D(uTex, clamp(su, 0.002, 0.998));
      if (abs(dx) < 0.96 && openAmt > 0.025) {
        float gh = max(0.001, lowerY - upperY);
        float mask = smoothstep(upperY-0.05, upperY+0.03, dy)*(1.0-smoothstep(lowerY-0.05, lowerY+0.03, dy))*smoothstep(0.96, 0.68, abs(dx))*smoothstep(0.025, 0.11, openAmt);
        if (mask > 0.005) {
          float ry = clamp((dy - upperY) / gh, 0.0, 1.0);
          vec3 cav = vec3(0.11, 0.03, 0.045);
          float teeth = (1.0 - smoothstep(0.16, 0.34, ry)) * smoothstep(0.0, 0.07, ry) * smoothstep(0.88, 0.45, abs(dx));
          float tongue = smoothstep(0.45, 0.75, ry) * (1.0 - smoothstep(0.85, 1.0, ry)) * smoothstep(0.75, 0.25, abs(dx));
          cav = mix(cav, vec3(0.92, 0.90, 0.87), teeth * 0.82);
          cav = mix(cav, vec3(0.58, 0.22, 0.27), tongue * 0.55);
          col.rgb = mix(col.rgb, cav, mask*0.92);
        }
      }
      gl_FragColor = vec4(col.rgb, 1.0);
    }
  `;

  function comp(t, s) { let sh = gl.createShader(t); gl.shaderSource(sh, s); gl.compileShader(sh); return sh; }
  const prog = gl.createProgram(); gl.attachShader(prog, comp(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, comp(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(prog); gl.useProgram(prog);

  const GRID = 48; let verts = [], uvs = [], idx = [];
  for (let y=0; y<=GRID; y++) for (let x=0; x<=GRID; x++) { verts.push(x/GRID*2-1, (1-y/GRID)*2-1); uvs.push(x/GRID, y/GRID); }
  for (let y=0; y<GRID; y++) for (let x=0; x<GRID; x++) { let i = y*(GRID+1)+x; idx.push(i, i+1, i+GRID+1, i+1, i+GRID+2, i+GRID+1); }

  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
  let al = gl.getAttribLocation(prog, 'aPos'); gl.enableVertexAttribArray(al); gl.vertexAttribPointer(al, 2, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(uvs), gl.STATIC_DRAW);
  let ul = gl.getAttribLocation(prog, 'aUv'); gl.enableVertexAttribArray(ul); gl.vertexAttribPointer(ul, 2, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(idx), gl.STATIC_DRAW);

  const U = {}; ['uTime','uZoom','uHeadSway','uCanvasSize','uMediaAspect','uMouthCenter','uMouthWidth','uLeftEye','uRightEye','uEyeRadius','uMouthOpen','uBlink'].forEach(n => U[n] = gl.getUniformLocation(prog, n));
  const tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([12, 12, 16, 255]));

  let mediaReady = false, img = new Image(); img.crossOrigin = 'anonymous';
  img.onload = () => { mediaReady = true; gl.bindTexture(gl.TEXTURE_2D, tex); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img); };
  img.src = C.photo;

  function resize() { let r = canvas.parentElement.getBoundingClientRect(), d = Math.min(window.devicePixelRatio||1, 2); canvas.width = Math.round(r.width*d); canvas.height = Math.round(r.height*d); gl.viewport(0,0,canvas.width,canvas.height); }
  window.addEventListener('resize', resize); resize();

  const wordCount = (C.text || '').trim().split(/\s+/).filter(Boolean).length;
  const estDurationMs = Math.min(22000, Math.max(4500, wordCount * 350));

  let mouthOpen = 0, blink = 0, nextBlink = performance.now() + 1800, isSpeaking = false;
  let lipSyncUntil = 0;

  let audioCtx = null, analyser = null, freqData = null, sourceConnected = false;
  function ensureAudioAnalyser() {
    if (sourceConnected || !C.audio) return;
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 128;
      freqData = new Uint8Array(analyser.frequencyBinCount);
      const srcNode = audioCtx.createMediaElementSource(sound);
      srcNode.connect(analyser);
      analyser.connect(audioCtx.destination);
      sourceConnected = true;
    } catch (e) {}
  }

  if (C.audio) {
    sound.src = 'data:' + (C.audioMime || 'audio/mpeg') + ';base64,' + C.audio;
    sound.style.display = 'block';
  } else {
    sound.style.display = 'none';
  }

  function getSyllableEnvelope(now) {
    const phraseGate = Math.sin(now * 0.0045) > -0.68 ? 1.0 : 0.10;
    const sylA = Math.max(0.0, Math.sin(now * 0.027));
    const sylB = Math.max(0.0, Math.sin(now * 0.016 + 1.2));
    const bilabialDip = 0.72 + 0.28 * Math.cos(now * 0.063);
    return Math.min(0.92, (0.16 + 0.50 * sylA + 0.30 * sylB) * bilabialDip * phraseGate);
  }

  function render(now) {
    requestAnimationFrame(render);
    if (!mediaReady) return;
    if (now >= nextBlink) {
      let el = now - nextBlink;
      if (el < 150) blink = Math.sin((el / 150) * Math.PI);
      else { blink = 0; nextBlink = now + 2400 + Math.random() * 2200; }
    }

    const activeSpeech = isSpeaking || (!sound.paused && !sound.ended && sound.currentTime > 0) || (now < lipSyncUntil);
    let targetOpen = 0;
    if (activeSpeech) {
      let cad = getSyllableEnvelope(now);
      if (analyser && freqData && !sound.paused) {
        analyser.getByteFrequencyData(freqData);
        let sum = 0;
        for (let i = 1; i < 20; i++) sum += freqData[i];
        let env = Math.min(0.95, (sum / (19 * 255)) * 2.4);
        targetOpen = env > 0.04 ? (0.45 * env + 0.55 * cad) : cad;
      } else {
        targetOpen = cad;
      }
    }
    mouthOpen += (targetOpen - mouthOpen) * 0.34;

    const swayAmp = activeSpeech ? 0.0065 : 0.0035;
    gl.clearColor(0.9, 0.95, 1.0, 1); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform1f(U.uTime, now * 0.001); gl.uniform1f(U.uZoom, 1.0);
    gl.uniform2f(U.uHeadSway, Math.sin(now * 0.0014) * swayAmp, Math.cos(now * 0.0022) * (swayAmp * 0.8));
    gl.uniform2f(U.uCanvasSize, canvas.width, canvas.height);
    gl.uniform1f(U.uMediaAspect, img.naturalWidth / Math.max(1, img.naturalHeight));
    gl.uniform2fv(U.uMouthCenter, landmarks.mouthCenter); gl.uniform1f(U.uMouthWidth, landmarks.mouthWidth);
    gl.uniform2fv(U.uLeftEye, landmarks.leftEye); gl.uniform2fv(U.uRightEye, landmarks.rightEye);
    gl.uniform2fv(U.uEyeRadius, landmarks.eyeRadius);
    gl.uniform1f(U.uMouthOpen, mouthOpen); gl.uniform1f(U.uBlink, blink);
    gl.drawElements(gl.TRIANGLES, idx.length, gl.UNSIGNED_SHORT, 0);
  }
  requestAnimationFrame(render);

  function speakFallbackBrowserTTS() {
    // Intentional visual preview only: do not substitute an unintended male browser voice.
    lipSyncUntil = performance.now() + Math.min(4800, estDurationMs);
    isSpeaking = false;
    $('status').textContent = C.pending ? 'Preparing generated voice…' :
      (C.audioError || 'Generated voice unavailable. Preview lips is available.');
  }

  async function play() {
    lipSyncUntil = performance.now() + estDurationMs;
    isSpeaking = true;
    if (!C.audio) {
      speakFallbackBrowserTTS();
      return;
    }
    try {
      ensureAudioAnalyser();
      if (audioCtx && audioCtx.state === 'suspended') await audioCtx.resume();
      sound.currentTime = 0;
      await sound.play();
    } catch (e) {
      speakFallbackBrowserTTS();
    }
  }

  $('speak').onclick = play;
  $('preview').onclick = () => { lipSyncUntil = performance.now() + 5000; $('status').textContent = 'Lip animation preview'; };
  $('stop').onclick = () => {
    sound.pause();
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    isSpeaking = false;
    lipSyncUntil = 0;
    mouthOpen = 0;
    $('status').textContent = 'Stopped';
  };
  sound.onplay = () => {
    isSpeaking = true;
    lipSyncUntil = performance.now() + Math.max(estDurationMs, (sound.duration || 6) * 1000);
    $('status').textContent = 'Speaking…';
  };
  sound.onended = sound.onpause = () => {
    isSpeaking = false;
    lipSyncUntil = 0;
    $('status').textContent = 'Audio Ready';
  };
  if (C.audio && C.replyId) setTimeout(play, 300);
})();
</script>
</body>
</html>
"""

MIC_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600&family=Quicksand:wght@600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; overflow: hidden; font-family: 'Fredoka', sans-serif; }
  .mic-bar {
    background: #ffffff;
    border: 2.5px solid #7e57c2;
    padding: 8px 14px;
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 4px 4px 0px #b39ddb;
  }
  #micBtn {
    background: #ff4081;
    color: #ffffff;
    border: 2px solid #2b2d42;
    padding: 8px 14px;
    font-family: 'Quicksand', sans-serif;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    border-radius: 16px;
    white-space: nowrap;
    box-shadow: 2px 2px 0px #2b2d42;
  }
  #micBtn:active { transform: scale(0.98); }
  #micStatus {
    font-size: 11px;
    color: #512da8;
    font-weight: 600;
    margin-left: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    text-align: right;
  }
</style>
</head>
<body>
<div class="mic-bar">
  <button id="micBtn" type="button">🎙️ Speak to AI</button>
  <span id="micStatus">Click mic &amp; speak</span>
</div>
<script>
(() => {
  const micBtn = document.getElementById('micBtn');
  const micStatus = document.getElementById('micStatus');
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  function setChatTextareaValue(spokenText, shouldSubmit) {
    try {
      const parentWin = window.parent;
      const parentDoc = parentWin.document;
      const ta = parentDoc.querySelector('div[data-testid="stForm"] textarea') ||
                 parentDoc.querySelector('textarea[aria-label="Question"]') ||
                 parentDoc.querySelector('textarea');
      if (!ta) {
        micStatus.textContent = 'Chat box not found';
        return;
      }

      const proto = parentWin.HTMLTextAreaElement ? parentWin.HTMLTextAreaElement.prototype : window.HTMLTextAreaElement.prototype;
      const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
      nativeSetter.call(ta, spokenText);

      if (ta._valueTracker) {
        ta._valueTracker.setValue('');
      }

      ta.focus();
      ta.dispatchEvent(new parentWin.FocusEvent('focusin', { bubbles: true }));
      ta.dispatchEvent(new parentWin.Event('input', { bubbles: true }));
      ta.dispatchEvent(new parentWin.Event('change', { bubbles: true }));

      if (shouldSubmit) {
        setTimeout(() => {
          ta.dispatchEvent(new parentWin.FocusEvent('focusout', { bubbles: true }));
          ta.dispatchEvent(new parentWin.FocusEvent('blur', { bubbles: false }));
          ta.blur();

          setTimeout(() => {
            const submitBtn = parentDoc.querySelector('div[data-testid="stFormSubmitButton"] button') ||
                              parentDoc.querySelector('button[kind="primaryFormSubmit"]');
            if (submitBtn) {
              submitBtn.click();
              micStatus.textContent = 'Sent: ' + spokenText;
            } else {
              micStatus.textContent = 'Typed! Click Send Question';
            }
          }, 180);
        }, 150);
      }
    } catch (err) {
      micStatus.textContent = 'Error: ' + err.message;
    }
  }

  if (!SpeechRecognition) {
    micStatus.textContent = 'Use Chrome or Edge for Mic';
    micBtn.onclick = () => { alert('Browser SpeechRecognition requires Chrome or Edge.'); };
    return;
  }

  let recognition = null;
  let isListening = false;
  let latestTranscript = '';
  let hasSubmitted = false;

  micBtn.onclick = () => {
    if (isListening && recognition) {
      recognition.stop();
      return;
    }

    latestTranscript = '';
    hasSubmitted = false;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      isListening = true;
      micStatus.textContent = '🔴 Listening... Speak now!';
      micBtn.textContent = '⏹️ Stop & Send';
      micBtn.style.background = '#00bcd4';
      micBtn.style.color = '#fff';
    };

    recognition.onresult = (e) => {
      let transcript = '';
      let isFinal = false;
      for (let i = 0; i < e.results.length; i++) {
        transcript += e.results[i][0].transcript;
        if (e.results[i].isFinal) isFinal = true;
      }
      latestTranscript = transcript.trim();
      if (latestTranscript) {
        micStatus.textContent = 'Hearing: ' + latestTranscript;
        setChatTextareaValue(latestTranscript, false);
      }
      if (isFinal && latestTranscript && !hasSubmitted) {
        hasSubmitted = true;
        micStatus.textContent = 'Submitting: ' + latestTranscript;
        micBtn.style.background = '#00e676';
        micBtn.style.color = '#2b2d42';
        setChatTextareaValue(latestTranscript, true);
      }
    };

    recognition.onerror = (e) => {
      isListening = false;
      micStatus.textContent = 'Mic error (' + e.error + '). Click to retry.';
      micBtn.textContent = '🎙️ Speak to AI';
    };

    recognition.onend = () => {
      isListening = false;
      micBtn.textContent = '🎙️ Speak to AI';
      if (latestTranscript && !hasSubmitted) {
        hasSubmitted = true;
        micStatus.textContent = 'Submitting: ' + latestTranscript;
        setChatTextareaValue(latestTranscript, true);
      }
      setTimeout(() => {
        micBtn.style.background = '#ff4081';
        micBtn.style.color = '#fff';
      }, 1500);
    };

    try {
      recognition.start();
    } catch (err) {
      micStatus.textContent = 'Mic error: ' + err.message;
    }
  };
})();
</script>
</body>
</html>
"""

from seller_town_pages import render_page, PAGES

# SELLER ASSIST CROSS-PAGE HANDOFF v23
if st.session_state.get('nav_selector') not in PAGES:
    st.session_state['nav_selector'] = PAGES[0]
requested_page = st.session_state.pop('sa_page_request', None)
if requested_page in PAGES:
    st.session_state['nav_selector'] = requested_page
requested_model = st.session_state.pop('sa_mode_request', None)
if requested_model in ASSISTANTS:
    st.session_state['bit_mode'] = requested_model

# Sidebar Navigation with Gamification & Global Settings
with st.sidebar:
    st.markdown("## 🌸 SELLER ASSIST")
    st.caption(f"Kawaii Edition · XP: {st.session_state['seller_xp']} ⭐")
    st.markdown("### **MAIN NAVIGATION**")
    nav_mode = st.radio(
        "Select View",
        ["🏡 Home", "📦 Inventory Lab", "🎨 Listings & Marketing", "🚚 Orders & Suppliers", "💰 Finance Desk", "🤖 AI Team", "⚙️ Settings & Data"],
        index=0,
        key="nav_selector",
        label_visibility="collapsed",
    )

    currency_choice = st.selectbox("💱 Display Currency", list(CURRENCY_RATES.keys()), index=0)
    fx_rate, fx_sym = CURRENCY_RATES[currency_choice]

    market_choice = st.selectbox("🏷️ Marketplace Fee Model", list(MARKETPLACE_FEES.keys()), index=0)
    active_fee_rate = MARKETPLACE_FEES[market_choice]

    if nav_mode == "🤖 AI Team":
        st.markdown("### **CHOOSE AI LEVEL**")
        mode = st.radio("Select Level", list(ASSISTANTS), key="bit_mode", label_visibility="collapsed")
        info = ASSISTANTS[mode]
        data = workspaces[mode]

    st.divider()
    st.markdown("### **🛠️ Sentry APM & Telemetry**")
    tel = st.session_state["telemetry"]
    st.caption(f"🟢 Sentry Status: {'SDK installed (DSN not verified)' if SENTRY_AVAILABLE else 'SDK not installed'}")
    st.caption(f"⚡ Last AI Latency: {tel['last_latency_ms']} ms")
    st.caption(f"📡 Brain Calls: {tel['calls']} · Errors: {tel['errors']}")
    st.divider()
    if nav_mode == "🤖 AI Team" and st.button("Clear conversation", use_container_width=True):
        data["messages"] = []
        data["last_reply"] = ""
        st.rerun()

if nav_mode != "🤖 AI Team":
    # SELLER ASSIST ROUTING v23 — preserves the modular page branch.
    # Dedicated business pages reuse the existing live app tools and workspaces.
    render_page(nav_mode, {
        "workspaces": workspaces,
        "SAMPLE_DASHBOARD_CSV": SAMPLE_DASHBOARD_CSV,
        "SAMPLE_SELLER_CSV": SAMPLE_SELLER_CSV,
        "active_fee_rate": active_fee_rate,
        "fx_rate": fx_rate,
        "fx_sym": fx_sym,
        "add_xp": add_xp,
        "db_load_todos": db_load_todos,
        "db_add_todo": db_add_todo,
        "db_save_todo_status": db_save_todo_status,
        "db_save_budget": db_save_budget,
        "run_tabpfn_inventory_forecast": run_tabpfn_inventory_forecast,
        "generate_supplier_po": generate_supplier_po,
        "generate_shopify_etsy_listing_csv": generate_shopify_etsy_listing_csv,
        "fetch_serpapi_competitor_pricing": fetch_serpapi_competitor_pricing,
        "generate_schedule_c_pl": generate_schedule_c_pl,
        "render_dashboard_charts": render_dashboard_charts,
        "ASSISTANTS": ASSISTANTS,
        "secret": secret,
    })
else:
    st.markdown(
        f"""
        <div class="kawaii-header">
          <div>
            <h1>MEET YOUR AI TEAM<br><span style="color:#7e57c2;font-size:0.65em;">SUCCESS IS YOUR REALITY · {info['level']}</span></h1>
            <p>Private AI back-office for marketplace sellers. Upload your shop CSV under Settings &amp; Data, then consult {info['name']} by voice or text.</p>
            <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;">
              <span class="kawaii-badge">🎨 Active: {info['name']} ({mode})</span>
              <span class="kawaii-badge" style="background:#00e676;color:#2b2d42 !important;">🧠 {data['last_model_used']}</span>
              <span class="kawaii-badge">⭐ XP: {st.session_state['seller_xp']}</span>
            </div>
          </div>
          <div>
            <span class="kawaii-badge" style="background:#00e676;color:#2b2d42 !important;">● SHARED SESSION</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_center, col_right = st.columns([1.0, 1.32, 1.08], gap="medium")

    with col_left:
        _sa_specialist_room_tools(
            mode, data, inventory_csv=_sa_inventory_source(data), fee_rate=active_fee_rate,
            run_forecast=run_tabpfn_inventory_forecast, run_po=generate_supplier_po,
            run_listing=generate_shopify_etsy_listing_csv, run_pl=generate_schedule_c_pl,
        )

    with col_center:
        st.markdown(f"<div style='text-align:center; margin-bottom:6px;font-weight:800;color:#512da8;'><b>{info['name']}</b> · {info['level']}</div>", unsafe_allow_html=True)
        render_avatar(info, data)
        _sa_voice_status(mode, data)

    with col_right:
        st.markdown(f"<div style='color:#512da8;font-weight:700;margin-bottom:6px;'>💬 Consult with {info['name']}</div>", unsafe_allow_html=True)
        thread = st.container(height=340)
        with thread:
            if not data["messages"]:
                st.info(f"Type below or click **🎙️ Speak to AI** to talk to {info['name']}.")
            for m in data["messages"]:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])
                    st.caption(m["time"])

        components.html(MIC_HTML, height=52, scrolling=False)

        with st.form(key=f"form_{mode}", clear_on_submit=True):
            prompt = st.text_area("Question", placeholder="Ask about stockouts, EOQ, SEO, taxes...", height=85, label_visibility="collapsed")
            send = st.form_submit_button("Send Question →", type="primary", use_container_width=True)
        if send and prompt.strip():
            with st.spinner("Processing level..."):
                process_message(mode, data, prompt, ref=True)
            st.rerun()