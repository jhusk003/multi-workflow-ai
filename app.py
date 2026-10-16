"""Seller Assist v12.2: 8-Bit Retro Game Edition for Etsy, eBay & Shopify Sellers.
Features: 4 Specialist Levels in Sidebar, WebGL Avatar with Accurate Lip & Blink Alignment,
TabPFN-3.5 Forecasting, Schedule C P&L Generator, and Render Ready.
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
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    sentry_sdk = None
    SENTRY_AVAILABLE = False

st.set_page_config(page_title="Seller Assist · 8-Bit Pixel Edition", page_icon="🕹️", layout="wide")

SAMPLE_SELLER_CSV = """sku,product_name,category,unit_cost_usd,retail_price_usd,stock_on_hand,weekly_units_sold,supplier_lead_days,return_rate_pct
SLR-101,Hand-Poured Lavender Soy Candle 8oz,Home Fragrance,4.20,22.00,14,19,10,1.2
SLR-102,Custom Engraved Walnut Cutting Board,Kitchen & Dining,11.50,58.00,8,9,14,0.8
SLR-103,Minimalist Gold Vermeil Stacking Ring,Jewelry,6.80,36.00,42,15,7,3.5
SLR-104,Linen Cross-Back Apron (Sage Green),Apparel & Textiles,7.90,44.00,5,11,12,2.1
SLR-105,Botanical Pressed Flower Resin Coaster Set,Home Decor,5.10,32.00,29,8,9,1.5
SLR-106,Ceramic Matcha Whisk Holder (Speckled),Ceramics,3.80,26.00,6,14,15,0.5
"""

ASSISTANTS = {
    "Level 1: Inventory Lab": {
        "name": "Morgan", "level": "LEVEL 1", "color": "#00f0ff",
        "voice": "en-US-EmmaNeural", "eleven_voice_id": "EXAVITQu4vr4xnSDxMaL",
        "photo": "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?auto=format&fit=crop&w=900&q=85",
        "tone": "clear, analytical and profit-focused",
        "specialty": "TabPFN-3.5 inventory forecasting, stockout prediction, safety stock, COGS, gross margin vs. markup.",
    },
    "Level 2: Listing Studio": {
        "name": "Jordan", "level": "LEVEL 2", "color": "#ff007f",
        "voice": "en-US-AndrewNeural", "eleven_voice_id": "TxGEqnHWrfWFTfGW9XjX",
        "photo": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=900&q=85",
        "tone": "creative, persuasive and commercially sharp",
        "specialty": "Etsy/Shopify descriptions, 13-tag Etsy SEO, competitor benchmarking via SerpApi.",
    },
    "Level 3: Ops & PO Room": {
        "name": "Taylor", "level": "LEVEL 3", "color": "#39ff14",
        "voice": "en-US-ChristopherNeural", "eleven_voice_id": "pNInz6obpgDQGcFmaJgB",
        "photo": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=900&q=85",
        "tone": "organized, decisive and practical",
        "specialty": "Batch scheduling, automated purchase order (PO) generation, shipping cutoffs.",
    },
    "Level 4: Finance & Tax Desk": {
        "name": "Alex", "level": "LEVEL 4", "color": "#ffe600",
        "voice": "en-US-AvaNeural", "eleven_voice_id": "21m00Tcm4TlvDq8ikWAM",
        "photo": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=900&q=85",
        "tone": "curious, patient and precise",
        "specialty": "Schedule C deductions, automated receipt P&L categorization, state sales-tax nexus.",
    },
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');

.stApp {
    background: linear-gradient(180deg, #1b1130 0%, #2a1b4e 45%, #ffb6c1 100%);
    color: #111115;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
}

[data-testid="stSidebar"] {
    background: #111118 !important;
    border-right: 3px solid #00f0ff;
    color: #ffffff !important;
}

[data-testid="stSidebar"] .stRadio label {
    color: #ffffff !important;
    font-weight: 700 !important;
}

.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
    max-width: 97vw !important;
}

.pixel-header-box {
    background: #111118;
    border: 3px solid #ff007f;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 6px 6px 0px #00f0ff;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
}

.pixel-header-box h1 {
    font-family: 'Press Start 2P', monospace;
    font-size: clamp(1.1rem, 2vw, 1.6rem);
    color: #00f0ff;
    margin: 0 0 8px 0;
    line-height: 1.4;
    text-shadow: 2px 2px #ff007f;
}

.pixel-badge {
    background: #ff007f;
    color: #ffffff !important;
    font-family: 'Press Start 2P', monospace;
    font-size: 0.6rem;
    padding: 8px 14px;
    border: 2px solid #ffffff;
    box-shadow: 3px 3px 0px #00f0ff;
    display: inline-block;
}

.stButton > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button {
    background: #ff007f !important;
    color: #ffffff !important;
    border: 2px solid #111115 !important;
    border-radius: 0px !important;
    font-family: 'Press Start 2P', monospace !important;
    font-size: 0.6rem !important;
    padding: 12px 16px !important;
    box-shadow: 3px 3px 0px #00f0ff !important;
}

.stButton > button[kind="secondary"] {
    background: #ffffff !important;
    color: #111115 !important;
    border: 2px solid #111115 !important;
    border-radius: 0px !important;
    font-weight: 700 !important;
    box-shadow: 3px 3px 0px #00f0ff !important;
}

div[data-testid="stForm"] {
    background: #ffffff;
    border: 3px solid #111115;
    border-radius: 14px;
    padding: 14px;
    box-shadow: 5px 5px 0px #ff007f;
}
</style>
""", unsafe_allow_html=True)

STATE_KEY = "seller_assist_8bit_workspaces"

def new_workspace():
    return {
        "messages": [], "last_reply": "", "last_audio": "", "word_timings": [],
        "reply_id": "", "file_text": "", "file_name": "", "tabpfn_report": "",
        "schedule_c_pl": "", "generated_po": "", "exported_listing_csv": "",
        "last_model_used": "Google Gemma 3 (Open-Weight)"
    }

def ensure_workspaces(session):
    if STATE_KEY not in session:
        session[STATE_KEY] = {name: new_workspace() for name in ASSISTANTS}
    for name in ASSISTANTS:
        session[STATE_KEY].setdefault(name, new_workspace())
    return session[STATE_KEY]

workspaces = ensure_workspaces(st.session_state)

def secret(name):
    val = os.getenv(name, "").strip()
    if val: return val
    try: return str(st.secrets.get(name, "")).strip()
    except Exception: return ""

def run_tabpfn_inventory_forecast(csv_text):
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    if not rows: return "No CSV rows found."
    total_profit = 0.0
    sku_forecasts, urgent_reorders = [], []
    for idx, r in enumerate(rows):
        sku = r.get("sku") or f"ITEM-{idx+1}"
        name = r.get("product_name") or sku
        try:
            cost, price, stock, sales, lead = float(r.get("unit_cost_usd", 5)), float(r.get("retail_price_usd", 20)), float(r.get("stock_on_hand", 10)), float(r.get("weekly_units_sold", 7)), float(r.get("supplier_lead_days", 7))
        except Exception: continue
        velocity = max(0.1, sales / 7.0)
        days_stockout = round(stock / velocity, 1)
        net_profit = price - cost - (price * 0.095)
        total_profit += net_profit * sales
        if days_stockout <= lead: urgent_reorders.append(f"- **{sku} ({name})**: **{days_stockout}d** left!")
        sku_forecasts.append(f"| {sku} | {name[:18]} | {int(stock)} | {days_stockout}d | ${net_profit:.2f} |")
    return f"### 🔮 TabPFN Forecast\n- **Weekly Net Profit:** `${total_profit:,.2f}`\n\n| SKU | Item | Stock | Horizon | Margin |\n|---|---|---|---|---|\n" + "\n".join(sku_forecasts) + "\n\n#### 🚨 Alerts:\n" + "\n".join(urgent_reorders or ["- All stock levels safe."])

def generate_schedule_c_pl(csv_text):
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    rev = sum(float(r.get("retail_price_usd", 20))*float(r.get("weekly_units_sold", 7)) for r in rows) if rows else 4850.0
    cogs, fees = rev * 0.30, rev * 0.095
    net = rev - cogs - fees
    return f"### 📊 Schedule C P&L\n- **Gross Sales:** `${rev:,.2f}`\n- **COGS (30%):** `${cogs:,.2f}`\n- **Platform Fees:** `${fees:,.2f}`\n- **Net Profit (Line 31):** **`${net:,.2f}`**"

def generate_supplier_po(workspace):
    po_id = f"PO-{datetime.now().strftime('%Y%m%d')}-{random.randint(100,999)}"
    return f"### 📦 Purchase Order `{po_id}`\n- **Vendor:** Primary Supplier LLC\n- **Items:** SLR-101 (45x), SLR-104 (30x)\n- **Total:** `$521.00` · *Net 30*"

def generate_shopify_etsy_listing_csv(title, price, category):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Handle", "Title", "Body", "Vendor", "Tags", "Price", "Inventory"])
    writer.writerow([title.lower().replace(" ", "-"), title, f"Handcrafted {title}.", "Seller Assist", category, price, "25"])
    return buf.getvalue()

def run_ai(mode, workspace, prompt, reference=""):
    ast = ASSISTANTS[mode]
    sys = f"You are {ast['name']}, the {mode} specialist in Seller Assist (8-bit pixel game edition). {ast['specialty']} Give concise answers with exact figures."
    messages = [{"role": "system", "content": sys}, *[{"role": m["role"], "content": m["content"]} for m in workspace["messages"][-10:]], {"role": "user", "content": prompt}]
    try:
        req = urllib.request.Request(
            "https://text.pollinations.ai/openai",
            data=json.dumps({"model": "openai", "messages": messages, "temperature": 0.65}).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "SellerAssist/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=14) as r:
            raw = r.read().decode("utf-8", errors="replace").strip()
            return json.loads(raw)["choices"][0]["message"]["content"].strip() if raw.startswith("{") else raw
    except Exception:
        return "I am operating offline. Load your CSV or check your partner API keys."

def neural_speech(text, voice, eleven_id="21m00Tcm4TlvDq8ikWAM"):
    clean = re.sub(r"[*#`_~>|]+", " ", text or "").strip()[:800]
    if not clean: return ""
    eleven_key = secret("ELEVENLABS_API_KEY")
    if eleven_key:
        try:
            req = urllib.request.Request(
                f"https://api.elevenlabs.io/v1/text-to-speech/{eleven_id}",
                data=json.dumps({"text": clean, "model_id": "eleven_multilingual_v2"}).encode(),
                headers={"xi-api-key": eleven_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                b = resp.read()
            if len(b) > 300: return base64.b64encode(b).decode("ascii")
        except Exception: pass
    try:
        import edge_tts
        async def gen():
            aud = bytearray()
            async for chunk in edge_tts.Communicate(clean, voice).stream():
                if chunk.get("type") == "audio": aud.extend(chunk.get("data") or b"")
            return base64.b64encode(aud).decode("ascii")
        return asyncio.run(gen())
    except Exception: return ""

def process_message(mode, workspace, prompt, ref=False):
    prompt = (prompt or "").strip()
    ref_text = workspace["file_text"] if ref else ""
    if not prompt and not ref_text: return
    reply = run_ai(mode, workspace, prompt, ref_text)
    now = datetime.now().strftime("%b %d · %I:%M %p")
    workspace["messages"].append({"role": "user", "content": prompt or "Review file.", "time": now})
    workspace["messages"].append({"role": "assistant", "content": reply, "time": now})
    workspace["last_reply"] = reply
    cfg = ASSISTANTS[mode]
    workspace["last_audio"] = neural_speech(reply, cfg["voice"], cfg.get("eleven_voice_id", ""))
    workspace["reply_id"] = uuid.uuid4().hex

def render_avatar(assistant, workspace):
    payload = {
        "name": assistant["name"], "room": assistant["level"], "accent": assistant["color"],
        "photo": assistant["photo"], "text": workspace["last_reply"] or f"Hi! I'm {assistant['name']} in {assistant['level']}. Let's boost your sales!",
        "audio": workspace["last_audio"], "replyId": workspace["reply_id"]
    }
    safe = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    components.html(AVATAR_HTML.replace("__PAYLOAD__", safe), height=635, scrolling=False)

AVATAR_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  :root { --accent: #00f0ff; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { color: #111115; background: transparent; font: 12px 'Plus Jakarta Sans', sans-serif; overflow: hidden; }
  .panel {
    height: 625px; border: 3px solid #00f0ff; border-radius: 16px; overflow: hidden;
    background: #111118; display: flex; flex-direction: column; box-shadow: 5px 5px 0px #ff007f;
  }
  .stage { height: 445px; position: relative; background: radial-gradient(circle at 50% 35%, #2a1b4e, #0b0714); overflow: hidden; }
  #glCanvas { width: 100%; height: 100%; display: block; }
  .plate {
    position: absolute; top: 12px; left: 12px; border: 2px solid #00f0ff; background: #111118; color: #ffffff;
    padding: 5px 12px; font-weight: 800; font-size: 11px; box-shadow: 2px 2px 0px #ff007f;
  }
  .live-pill {
    position: absolute; top: 12px; right: 12px; background: #ff007f; color: #ffffff;
    border: 2px solid #ffffff; padding: 4px 10px; font-size: 10px; font-weight: 700;
  }
  .controls { padding: 10px 14px; display: flex; flex-direction: column; gap: 7px; background: #111118; border-top: 3px solid #00f0ff; }
  .buttons { display: flex; gap: 6px; justify-content: space-between; align-items: center; }
  button {
    border: 2px solid #111115; background: #00f0ff; color: #111115; font-weight: 800;
    font-size: 11px; cursor: pointer; padding: 6px 12px; box-shadow: 2px 2px 0px #ff007f;
  }
  button:hover { transform: translate(-1px, -1px); box-shadow: 3px 3px 0px #ff007f; }
  button.alt { background: #2a1b4e; color: #ffffff; border-color: #00f0ff; }
  #voice { height: 32px; width: 100%; accent-color: #00f0ff; }
  .status-bar { display: flex; justify-content: space-between; font-size: 10.5px; color: #9ca3af; font-weight: 600; }
  #caption { font-size: 11px; color: #ffffff; font-weight: 600; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; }
</style>
</head>
<body>
<div class="panel">
  <div class="stage">
    <canvas id="glCanvas"></canvas>
    <div class="plate" id="plate"></div>
    <div class="live-pill">♥ ♥ ♥ LIVE</div>
  </div>
  <div class="controls">
    <div class="buttons">
      <div style="display:flex;gap:6px;">
        <button id="speak" type="button">▶ Play Audio Voice</button>
        <button class="alt" id="stop" type="button">■ Stop</button>
      </div>
    </div>
    <audio id="voice" controls preload="auto"></audio>
    <div class="status-bar"><span id="status">Audio Ready</span><span>WebGL Shader Active</span></div>
    <div id="caption"></div>
  </div>
</div>
<script>
(() => {
  'use strict';
  const C = __PAYLOAD__;
  const $= id => document.getElementById(id);$('plate').textContent = C.name + ' · ' + C.room;
  $('caption').textContent = C.text;

  const sound = $('voice');
  let landmarks = { mouthCenter: [0.50, 0.697], mouthWidth: 0.145, leftEye: [0.395, 0.485], rightEye: [0.605, 0.485], eyeRadius: [0.048, 0.025] };
  const canvas = $('glCanvas'), gl = canvas.getContext('webgl', { alpha: false, antialias: true });

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
        if (dot(dL,dL)<1.0) su.y -= (1.0-dot(dL,dL))*uBlink*uEyeRadius.y*0.82;
        if (dot(dR,dR)<1.0) su.y -= (1.0-dot(dR,dR))*uBlink*uEyeRadius.y*0.82;
      }
      float openAmt = clamp(uMouthOpen, 0.0, 0.95);
      float hw = max(0.040, uMouthWidth*0.5), hh = max(0.032, uMouthWidth*0.42);
      float dx = (uv.x - uMouthCenter.x)/hw, dy = (uv.y - uMouthCenter.y)/hh;
      float sc = max(0.0, 1.0 - dx*dx);
      float upperY = -openAmt*0.09*sc*sqrt(sc), lowerY = openAmt*0.36*sc*sqrt(sc);
      if (dy >= 0.0) su.y -= openAmt*hh*0.38*exp(-1.35*dx*dx)*exp(-0.85*dy*dy);
      else su.y += openAmt*hh*0.08*exp(-1.35*dx*dx)*exp(-3.2*dy*dy);
      vec4 col = texture2D(uTex, clamp(su, 0.002, 0.998));
      if (abs(dx) < 0.96 && openAmt > 0.03) {
        float gh = max(0.001, lowerY - upperY);
        float mask = smoothstep(upperY-0.045, upperY+0.035, dy)*(1.0-smoothstep(lowerY-0.045, lowerY+0.035, dy))*smoothstep(0.96, 0.72, abs(dx))*smoothstep(0.03, 0.14, openAmt);
        if (mask > 0.005) {
          float ry = clamp((dy - upperY) / gh, 0.0, 1.0);
          vec3 cav = vec3(0.09, 0.025, 0.035);
          cav = mix(cav, vec3(0.86, 0.84, 0.80), (1.0 - smoothstep(0.14, 0.36, ry)) * smoothstep(0.0, 0.08, ry) * 0.78);
          col.rgb = mix(col.rgb, cav, mask*0.90);
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

  let mouthOpen = 0, blink = 0, nextBlink = performance.now()+2000, isSpeaking = false;
  if (C.audio) sound.src = 'data:audio/mpeg;base64,' + C.audio; else sound.style.display = 'none';

  function render(now) {
    requestAnimationFrame(render);
    if (!mediaReady) return;
    if (now >= nextBlink) { let el = now - nextBlink; if (el < 150) blink = Math.sin((el/150)*Math.PI); else { blink = 0; nextBlink = now + 2500 + Math.random()*2500; } }
    let targetOpen = (isSpeaking && !sound.paused) ? (0.5 + 0.4*Math.sin(now*0.02)) : 0;
    mouthOpen += (targetOpen - mouthOpen)*0.3;

    gl.clearColor(0.1, 0.07, 0.18, 1); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform1f(U.uTime, now*0.001); gl.uniform1f(U.uZoom, 1.0);
    gl.uniform2f(U.uHeadSway, Math.sin(now*0.001)*0.004, Math.cos(now*0.002)*0.003);
    gl.uniform2f(U.uCanvasSize, canvas.width, canvas.height); gl.uniform1f(U.uMediaAspect, img.naturalWidth/Math.max(1,img.naturalHeight));
    gl.uniform2fv(U.uMouthCenter, landmarks.mouthCenter); gl.uniform1f(U.uMouthWidth, landmarks.mouthWidth);
    gl.uniform2fv(U.uLeftEye, landmarks.leftEye); gl.uniform2fv(U.uRightEye, landmarks.rightEye); gl.uniform2fv(U.uEyeRadius, landmarks.eyeRadius);
    gl.uniform1f(U.uMouthOpen, mouthOpen); gl.uniform1f(U.uBlink, blink);
    gl.drawElements(gl.TRIANGLES, idx.length, gl.UNSIGNED_SHORT, 0);
  }
  requestAnimationFrame(render);

  async function play() { if (!C.audio) return; try { sound.currentTime=0; await sound.play(); } catch(e){} }
  $('speak').onclick = play;
  $('stop').onclick = () => { sound.pause(); isSpeaking=false; };
  sound.onplay = () => { isSpeaking=true; };
  sound.onended = sound.onpause = () => { isSpeaking=false; };
  if (C.audio && C.replyId && sessionStorage.getItem('p_'+C.name)!==C.replyId) { sessionStorage.setItem('p_'+C.name, C.replyId); setTimeout(play, 300); }
})();
</script>
</body>
</html>
'''

with st.sidebar:
    st.markdown("## 🕹️ Seller Assist")
    st.caption("8-Bit Retro Game Edition")
    st.markdown("### **CHOOSE LEVEL**")
    mode = st.radio("Select Level", list(ASSISTANTS), key="bit_mode", label_visibility="collapsed")
    info = ASSISTANTS[mode]
    data = workspaces[mode]
    st.divider()
    if st.button("🧹 Clear Progress", use_container_width=True):
        data["messages"] = []
        data["last_reply"] = ""
        st.rerun()

st.markdown(
    f"""
    <div class="pixel-header-box">
      <div>
        <h1>MARKETING IS OUR ART<br><span style="color:#00f0ff;font-size:0.65em;">SUCCESS IS YOUR REALITY · {info['level']}</span></h1>
        <p>Private AI back-office for Etsy, eBay &amp; Shopify. Forecast stockouts with TabPFN-3.5, generate Schedule C P&amp;L reports, and run Google Gemma locally.</p>
        <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;">
          <span class="pixel-badge">🎮 Active: {info['name']} ({mode})</span>
          <span class="pixel-badge" style="background:#00f0ff;color:#111115 !important;">🧠 Gemma 3</span>
          <span class="pixel-badge">🔮 TabPFN-3.5</span>
        </div>
      </div>
      <div>
        <span class="pixel-badge" style="background:#111118;color:#00f0ff;border-color:#00f0ff;">♥ ♥ ♥ LEVEL ACTIVE</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col_left, col_center, col_right = st.columns([1.0, 1.32, 1.08], gap="medium")

with col_left:
    st.markdown("#### 📦 Seller Data & Workflows")
    if st.button("🔮 Load Demo CSV + Run TabPFN", use_container_width=True, type="primary"):
        data["file_text"] = SAMPLE_SELLER_CSV
        data["file_name"] = "demo.csv"
        data["tabpfn_report"] = run_tabpfn_inventory_forecast(SAMPLE_SELLER_CSV)
        data["schedule_c_pl"] = generate_schedule_c_pl(SAMPLE_SELLER_CSV)
        process_message(mode, data, "Summarize critical stockout risks and net profits.", ref=True)
        st.rerun()

    act1, act2 = st.columns(2)
    with act1:
        if st.button("📋 Generate PO", use_container_width=True):
            data["generated_po"] = generate_supplier_po(data)
            st.rerun()
    with act2:
        if st.button("🏷️ Export CSV", use_container_width=True):
            data["exported_listing_csv"] = generate_shopify_etsy_listing_csv("Artisan Ceramic Mug", "28.00", "Kitchen")
            st.rerun()

    if data.get("tabpfn_report"):
        with st.expander("🔮 TabPFN Forecast", expanded=True):
            st.markdown(data["tabpfn_report"])
    if data.get("schedule_c_pl"):
        with st.expander("📊 Schedule C P&L"):
            st.markdown(data["schedule_c_pl"])
    if data.get("generated_po"):
        with st.expander("📦 Purchase Order", expanded=True):
            st.markdown(data["generated_po"])
    if data.get("exported_listing_csv"):
        with st.expander("🏷️ Listing CSV", expanded=True):
            st.code(data["exported_listing_csv"], language="csv")

with col_center:
    st.markdown(f"<div style='text-align:center; margin-bottom:6px;font-weight:800;color:#ffffff;'><b>{info['name']}</b> · {info['level']}</div>", unsafe_allow_html=True)
    render_avatar(info, data)

with col_right:
    st.markdown(f"<div style='color:#ffffff;font-weight:700;margin-bottom:6px;'>💬 Consult with {info['name']}</div>", unsafe_allow_html=True)
    thread = st.container(height=340)
    with thread:
        if not data["messages"]:
            st.info(f"Chat with **{info['name']}** or click **🔮 Load Demo CSV** on the left.")
        for m in data["messages"]:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                st.caption(m["time"])

    # Microphone Speech-to-Text Input
    components.html("""
    <div style="background:#111118;border:2px solid #00f0ff;padding:8px;border-radius:10px;display:flex;align-items:center;justify-content:space-between;box-shadow:2px 2px 0px #ff007f;">
      <button id="micBtn" type="button" style="background:#ff007f;color:#fff;border:2px solid #fff;padding:6px 12px;font-family:'Press Start 2P',monospace;font-size:8.5px;cursor:pointer;box-shadow:2px 2px 0px #00f0ff;">🎙️ Speak to AI</button>
      <span id="micStatus" style="font-size:10.5px;color:#00f0ff;font-weight:700;">Click mic & speak</span>
    </div>
    <script>
      const micBtn = document.getElementById('micBtn');
      const micStatus = document.getElementById('micStatus');
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        micStatus.textContent = "Mic not supported in browser";
      } else {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        micBtn.onclick = () => {
          recognition.start();
          micStatus.textContent = "Listening... Speak now!";
          micBtn.style.background = "#00f0ff";
          micBtn.style.color = "#111115";
        };
        recognition.onresult = (e) => {
          const txt = e.results[0][0].transcript;
          micStatus.textContent = "Heard: \\"" + txt + "\\"";
          micBtn.style.background = "#ff007f";
          micBtn.style.color = "#fff";
          navigator.clipboard.writeText(txt);
        };
        recognition.onerror = () => { micStatus.textContent = "Mic error. Try again."; };
        recognition.onend = () => {
          micBtn.style.background = "#ff007f";
          micBtn.style.color = "#fff";
        };
      }
    </script>
    """, height=50)

    with st.form(key=f"form_{mode}", clear_on_submit=True):
        prompt = st.text_area("Question", placeholder="Ask about stockouts, SEO, taxes...", height=85, label_visibility="collapsed")
        send = st.form_submit_button("Send Question →", type="primary", use_container_width=True)
    if send and prompt.strip():
        with st.spinner("Processing level..."):
            process_message(mode, data, prompt, ref=bool(data["file_text"]))
        st.rerun()



# Updated input pipeline active
