"""Multi-Workflow AI v6: visible photo-lip compositing, neural playback and isolated assistants."""
import asyncio
import base64
import csv
import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Multi-Workflow AI · v6", page_icon="✨", layout="wide")

ASSISTANTS = {
    "Student": {
        "name": "Alex", "room": "Study Studio", "color": "#ec4899", "gender": "female",
        "voice": "en-US-AvaNeural", "photo": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=900&q=85", "tone": "curious, patient and precise",
        "specialty": "Calculus, algebra, mechanics, statics, physics, thermodynamics, programming, "
                     "academic writing, exam preparation, worked solutions and concept tutoring. "
                     "Work through technical reasoning correctly. Explain units and assumptions; admit uncertainty.",
        "hair": "#211526", "skin": "#a86e51", "outfit": "#b74f80", "hairStyle": "long",
    },
    "Freelancer": {
        "name": "Jordan", "room": "Creative Office", "color": "#0ea5e9", "gender": "male",
        "voice": "en-US-AndrewNeural", "photo": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=900&q=85", "tone": "collaborative, creative and commercially practical",
        "specialty": "Client discovery, proposals, portfolio positioning, contracts and scopes, pricing, "
                     "invoicing, deliverables, revisions, branding, marketing and negotiation. "
                     "Differentiate estimates from confirmed commitments.",
        "hair": "#211a1a", "skin": "#956646", "outfit": "#235b82", "hairStyle": "short",
    },
    "Inventory & Business": {
        "name": "Morgan", "room": "Business Workspace", "color": "#10b981", "gender": "female",
        "voice": "en-US-EmmaNeural", "photo": "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?auto=format&fit=crop&w=900&q=85", "tone": "clear, analytical and approachable",
        "specialty": "Inventory counts, unit economics, budgets, break-even, revenue, COGS, "
                     "cash flow, margin versus markup, reorder points, safety stock, forecasts, "
                     "spreadsheet and CSV analysis. Perform arithmetic and show assumptions and units.",
        "hair": "#38231b", "skin": "#c89470", "outfit": "#176a58", "hairStyle": "long",
    },
    "Resource & Task": {
        "name": "Taylor", "room": "Planning Room", "color": "#f59e0b", "gender": "male",
        "voice": "en-US-ChristopherNeural", "photo": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=900&q=85", "tone": "organized, decisive and realistic",
        "specialty": "Project milestones, scheduling, task decomposition, dependency mapping, "
                     "critical path, priorities, capacity, resource allocation, risk, deadlines "
                     "and practical next actions. Never fabricate dates or resource availability.",
        "hair": "#30231f", "skin": "#8f6249", "outfit": "#9a672a", "hairStyle": "short",
    },
}

st.markdown("""
<style>
.stApp {background:linear-gradient(135deg,#0b1221,#111b30 58%,#101526);color:#f1f5f9}
[data-testid="stSidebar"] {background:#0a1120}
.block-container {padding-top:1.1rem;max-width:1450px}
.mwai-heading {border:1px solid #39445a;border-radius:18px;padding:18px 23px;
background:linear-gradient(105deg,#15243c,#152038);margin-bottom:16px}
.mwai-heading h1 {margin:0;color:#f8fafc;font-size:2rem}
.mwai-heading p {margin:7px 0 0;color:#b6c6db}
div[data-testid="stForm"] {border:1px solid #344052;border-radius:14px;padding:15px}
</style>
""", unsafe_allow_html=True)

# Only ONE location owns conversation data: workspaces[assistant]. There are no
# shared chat_history/last_response aliases to overwrite during Streamlit reruns.
STATE_KEY = "mwai_v6_workspaces"
def new_workspace():
    return {"messages": [], "last_reply": "", "last_audio": "", "word_timings": [],
            "reply_id": "", "file_text": "", "file_name": "", "seen_upload_digest": "",
            "seen_mic_digest": "", "tasks": [], "audio_error": ""}

def ensure_workspaces(session):
    if STATE_KEY not in session:
        session[STATE_KEY] = {name: new_workspace() for name in ASSISTANTS}
    for name in ASSISTANTS:
        session[STATE_KEY].setdefault(name, new_workspace())
        session[STATE_KEY][name].setdefault("audio_error", "")
    return session[STATE_KEY]

workspaces = ensure_workspaces(st.session_state)

with st.sidebar:
    st.title("✨ Multi-Workflow AI")
    st.caption("Version 6 · independent conversations and photo avatars")
    mode = st.radio("Choose your assistant", list(ASSISTANTS), key="mwai_v6_active_mode")
    info = ASSISTANTS[mode]
    data = workspaces[mode]  # A direct reference to ONLY the selected assistant.
    st.divider()
    st.caption(f"{info['name']} · {info['room']}")
    st.caption(f"Private conversation: {sum(m['role']=='user' for m in data['messages'])} messages")
    if st.button(f"Clear {info['name']}'s chat", use_container_width=True):
        data["messages"] = []
        data["last_reply"] = ""
        data["last_audio"] = ""
        data["word_timings"] = []
        data["reply_id"] = ""
        data["audio_error"] = ""
        st.rerun()
    if st.button(f"Clear {info['name']}'s reference file", use_container_width=True):
        data["file_text"] = ""
        data["file_name"] = ""
        data["seen_upload_digest"] = ""
        st.rerun()

# Read secrets from env (Render) or .streamlit/secrets.toml (local development).
def secret(name):
    val = os.getenv(name, "").strip()
    if val:
        return val
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""


def provider_messages(active_mode, workspace, prompt, reference):
    assistant = ASSISTANTS[active_mode]
    system = (f"You are {assistant['name']}, the {active_mode} assistant, speaking in a "
              f"{assistant['tone']} style. YOUR SPECIALIZED EXPERTISE: {assistant['specialty']} "
              "Respond conversationally to the actual question, without canned templates. "
              "Use the prior messages IN THIS THREAD only. Other assistants' chats are private "
              "and unavailable to you. Do not claim to remember anything outside this conversation. "
              "Be truthful, solve math carefully, and ask for missing details only when essential.")
    history = [{"role": m["role"], "content": m["content"]} for m in workspace["messages"][-16:]]
    user_text = prompt.strip() or "Please examine the attached reference."
    if reference:
        user_text += "\n\nREFERENCE FROM THIS WORKSPACE:\n" + reference[:11500]
    return [{"role": "system", "content": system}, *history,
            {"role": "user", "content": user_text}]


def run_ai(active_mode, workspace, prompt, reference):
    messages = provider_messages(active_mode, workspace, prompt, reference)
    errors = []
    ollama = secret("OLLAMA_HOST") or ("http://127.0.0.1:11434" if os.name == "nt" and not os.getenv("RENDER") else "")
    if ollama:
        try:
            base = ollama.rstrip("/")
            with urllib.request.urlopen(base + "/api/tags", timeout=2) as r:
                models = [m["name"] for m in json.load(r).get("models", [])]
            if models:
                preferred = ["qwen2.5:3b", "qwen2.5:1.5b", "llama3.2:3b", "gemma3:4b"]
                model = next((m for m in preferred if m in models), models[0])
                payload = {"model": model, "messages": messages, "stream": False,
                           "options": {"temperature": 0.65, "num_ctx": 4096}}
                req = urllib.request.Request(base + "/api/chat", json.dumps(payload).encode(),
                                             {"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=100) as r:
                    reply = json.load(r).get("message", {}).get("content", "").strip()
                if reply:
                    return reply
        except Exception as exc:
            errors.append(f"Ollama: {type(exc).__name__}")
    if secret("GROQ_API_KEY"):
        try:
            payload = {"model": "llama-3.3-70b-versatile", "messages": messages,
                       "temperature": 0.65, "max_tokens": 850}
            req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions",
                json.dumps(payload).encode(), {"Content-Type": "application/json",
                "Authorization": "Bearer " + secret("GROQ_API_KEY")})
            with urllib.request.urlopen(req, timeout=30) as r:
                reply = json.load(r)["choices"][0]["message"]["content"].strip()
            if reply:
                return reply
        except Exception as exc:
            errors.append(f"Groq: {type(exc).__name__}")
    if secret("GEMINI_API_KEY") or secret("GOOGLE_API_KEY"):
        try:
            key = secret("GEMINI_API_KEY") or secret("GOOGLE_API_KEY")
            contents = [{"role": "model" if m["role"] == "assistant" else "user",
                         "parts": [{"text": m["content"]}]} for m in messages[1:]]
            payload = {"systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
                       "contents": contents, "generationConfig": {"temperature": 0.65, "maxOutputTokens": 850}}
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + urllib.parse.quote(key)
            req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                reply = "".join(part.get("text", "") for part in json.load(r)["candidates"][0]["content"]["parts"]).strip()
            if reply:
                return reply
        except Exception as exc:
            errors.append(f"Gemini: {type(exc).__name__}")
    # An explicit error is preferable to identical fake 'AI thinking' on all four tabs.
    return ("I couldn't reach an AI model for this response. Run Ollama locally, or set "
            "GROQ_API_KEY or GEMINI_API_KEY in your environment. "
            + ("Connection attempts: " + ", ".join(errors) if errors else "No model provider configured."))


def neural_speech(text, voice):
    """Generate a neural MP3 with optional word timings. Never silently switch voices."""
    clean = re.sub(r"[*#`_~>|]+", " ", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()[:1800]
    if not clean:
        return "", [], "No response text to synthesize."
    try:
        import edge_tts
    except ImportError:
        return "", [], "edge-tts is not installed. Run: python -m pip install -r requirements.txt"

    async def generate(with_timings):
        audio = bytearray()
        timings = []
        opts = {"rate": "+0%"}
        if with_timings:
            opts["boundary"] = "WordBoundary"
        communicator = edge_tts.Communicate(clean, voice, **opts)
        async for chunk in communicator.stream():
            if chunk.get("type") == "audio":
                audio.extend(chunk.get("data") or b"")
            elif chunk.get("type") == "WordBoundary":
                timings.append({"text": str(chunk.get("text", "")),
                                "start": int(chunk.get("offset", 0)) / 10_000_000,
                                "duration": int(chunk.get("duration", 0)) / 10_000_000})
        if len(audio) < 200:
            raise RuntimeError("The neural voice service returned no MP3 audio.")
        return base64.b64encode(audio).decode("ascii"), timings

    first_error = ""
    try:
        audio, timings = asyncio.run(generate(True))
        return audio, timings, ""
    except Exception as exc:
        first_error = f"{type(exc).__name__}: {str(exc)[:180]}"
    # Some edge-tts service versions do not return word timing metadata.
    # Retry for the SAME voice without word boundaries; keep audio functional.
    try:
        audio, _ = asyncio.run(generate(False))
        return audio, [], "Word timings were unavailable; lip motion will follow audio duration."
    except Exception as exc:
        second_error = f"{type(exc).__name__}: {str(exc)[:180]}"
        return "", [], (f"Neural speech could not be generated for {voice}. "
                         f"First attempt: {first_error}. Retry: {second_error}. "
                         "Check internet access and Edge TTS connectivity; no unknown browser voice is substituted.")


def extract_file(upload):
    name = upload.name.lower()
    raw = upload.getvalue()
    try:
        if name.endswith(".pdf"):
            from pypdf import PdfReader
            return "\n\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(raw)).pages)
        if name.endswith((".txt", ".md", ".csv", ".json", ".py", ".html", ".ics")):
            return raw.decode("utf-8-sig", errors="replace")
        return "Unsupported file format."
    except Exception as exc:
        return f"Unable to extract file: {exc}"


def process_message(active_mode, workspace, prompt, attach_reference=False):
    prompt = (prompt or "").strip()
    reference = workspace["file_text"] if attach_reference else ""
    if not prompt and not reference:
        return
    reply = run_ai(active_mode, workspace, prompt, reference)
    now = datetime.now().strftime("%b %d, %Y · %I:%M %p")
    workspace["messages"].append({"role": "user", "content": prompt or "Please review my reference file.", "time": now})
    workspace["messages"].append({"role": "assistant", "content": reply, "time": now})
    workspace["last_reply"] = reply
    workspace["last_audio"], workspace["word_timings"], workspace["audio_error"] = neural_speech(reply, ASSISTANTS[active_mode]["voice"])
    workspace["reply_id"] = uuid.uuid4().hex


# The iframe contains one photo avatar and one native HTMLAudioElement. It does not
# attempt Web Speech browser voice fallback or paint a black fake mouth on a photo.
def render_avatar(assistant, workspace):
    payload = {
        "name": assistant["name"], "room": assistant["room"], "accent": assistant["color"],
        "photo": assistant["photo"],
        "text": workspace["last_reply"] or f"Hi, I'm {assistant['name']}. How can I help you today?",
        "audio": workspace["last_audio"], "timings": workspace["word_timings"],
        "audioError": workspace.get("audio_error", ""), "replyId": workspace["reply_id"],
    }
    safe = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    components.html(AVATAR_HTML.replace("__PAYLOAD__", safe), height=625, scrolling=False)


AVATAR_HTML = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--accent:#ec4899}*{box-sizing:border-box}body{margin:0;color:#edf3ff;background:transparent;font:13px system-ui,sans-serif}
.panel{height:616px;border:1px solid var(--accent);border-radius:16px;overflow:hidden;background:#101a2c}
.stage{height:434px;position:relative;background:radial-gradient(circle,#31445c,#141e31);overflow:hidden}
#photoCanvas{height:100%;width:100%;display:block;object-fit:cover}
.plate{position:absolute;top:12px;left:12px;border-left:4px solid var(--accent);border-radius:7px;background:#101827d9;padding:7px 11px;font-weight:700}
#calLabel{position:absolute;top:12px;right:12px;background:#101827dc;padding:6px 8px;border-radius:7px;font-size:11px;display:none}
#marker{display:none;position:absolute;width:28px;height:28px;border:2px solid #facc15;border-radius:50%;transform:translate(-50%,-50%);pointer-events:none;box-shadow:0 0 3px #000;background:transparent}
.controls{padding:11px 13px;display:flex;flex-direction:column;gap:8px}.buttons{display:flex;gap:7px;flex-wrap:wrap;align-items:center}
button{border:0;background:var(--accent);border-radius:8px;color:white;font-weight:700;cursor:pointer;padding:7px 11px}
button.alt{background:#334155}.hint{font-size:11px;color:#bfcfe5}.meter{font-size:11px;color:#bbf7d0;min-height:14px}#photoCanvas{touch-action:manipulation}.status{font-size:12px;color:#d7e4f2;white-space:nowrap;text-overflow:ellipsis;overflow:hidden}
#voice{height:31px;width:100%;accent-color:var(--accent)}#caption{font-size:12px;color:#e4eaf5;white-space:nowrap;text-overflow:ellipsis;overflow:hidden}
#photoCanvas.calibrating{cursor:crosshair}
</style></head><body>
<div class="panel"><div class="stage"><canvas id="photoCanvas" width="440" height="434" aria-label="Realistic portrait with subtle speaking motion"></canvas><div class="plate" id="plate"></div><div id="calLabel">Click the center of the lips</div><div id="marker"></div></div>
<div class="controls"><div class="buttons"><button id="speak">▶ Speak response</button><button class="alt" id="stop">■ Stop</button><button class="alt" id="demo">Test lip motion</button><button class="alt" id="calibrate">Align lips</button><button class="alt" id="reset">Reset alignment</button></div>
<audio id="voice" controls preload="auto"></audio><div id="status" class="status" role="status">Loading avatar…</div><div id="meter" class="meter">Mouth motion: idle</div><div id="caption"></div><div class="hint">Soft photo-pixel lip deformation · v6.1. No graphic mouth overlay. Approximate motion, not generated talking-head video. Assigned neural MP3 only.</div></div></div>
<script>
(()=>{'use strict';
const C=__PAYLOAD__,$=id=>document.getElementById(id),canvas=$('photoCanvas'),ctx=canvas.getContext('2d');
document.documentElement.style.setProperty('--accent',C.accent);$('plate').textContent=C.name+' · '+C.room;
const img=new Image();img.referrerPolicy='no-referrer';let ready=false,active=false,demoUntil=0,clock=0,aligning=false,hasSavedAlignment=false;
const defaults={Alex:[.50,.665],Jordan:[.50,.665],Morgan:[.50,.693],Taylor:[.50,.673]};
const key='mwai-v6-photo-mouth-'+C.name;
let position=defaults[C.name]||[.5,.68];try{const v=JSON.parse(localStorage.getItem(key));if(Array.isArray(v)&&v.length===2&&v.every(n=>typeof n==='number'&&n>=0&&n<=1)){position=v;hasSavedAlignment=true;}}catch(e){}
if(!hasSavedAlignment){aligning=true;canvas.classList.add('calibrating');$('calLabel').style.display='block';$('calLabel').textContent='FIRST: click the center of the real lips';}
const sound=$('voice');let words=C.text.match(/\S+/g)||[];let mouthOpen=0,mouthWidth=1,lastWord='';
if(C.audio){sound.src='data:audio/mpeg;base64,'+C.audio;$('status').textContent=C.audioError||'Neural voice is ready. Click Speak response or Play.';}
else{$('status').textContent=C.audioError||'No neural MP3 yet. Send a message to generate speech.';sound.style.display='none';}
$('caption').textContent=C.text;
img.onload=()=>{ready=true;status(!hasSavedAlignment?'CLICK THE CENTER OF THE REAL LIPS to set animation position.':C.audio?'Portrait ready. Play neural voice or use Test lip motion.':'Portrait ready. Use Test lip motion; send a message for neural audio.');};img.onerror=()=>{$('status').textContent='PHOTO LOAD FAILED: images.unsplash.com is unreachable; mouth movement cannot render. Check internet access.'};img.src=C.photo;
function status(text){$('status').textContent=text}
// Exact audio.currentTime is the single playback clock; no timer or browser TTS.
function shape(word,p){
 const w=String(word||'').replace(/[^a-z]/gi,'').toLowerCase();
 if(!w)return {open:.09,wide:1};
 const parts=w.match(/[^aeiouy]*[aeiouy]+[^aeiouy]*/g)||[w];
 const part=parts[Math.min(parts.length-1,Math.floor(p*parts.length))]||w;
 let o=.50,wide=1;
 if(/^[bmp]/.test(part)&&p<.22)o=.015;
 else if(/[ou]/.test(part)){o=.78;wide=.67;}
 else if(/(ee|ea|i|e|y)/.test(part)){o=.43;wide=1.30;}
 else if(/[a]/.test(part)){o=1;wide=1.08;}
 else if(/[fv]/.test(part))o=.20;
 if(p>.85)o*=.25;
 return {open:o,wide};
}
function sayWord(){
 const t=sound.currentTime,timings=C.timings||[];
 if(timings.length){
   for(const w of timings){
    const start=Math.max(0,Number(w.start)||0),dur=Math.max(.08,Number(w.duration)||0);
    if(t>=start&&t<start+dur){lastWord=w.text;return shape(lastWord,(t-start)/dur);}
   }
   lastWord='';return {open:0,wide:1};
 }
 if(!words.length)return {open:0,wide:1};
 const d=(Number.isFinite(sound.duration)&&sound.duration>0)?sound.duration:Math.max(2,words.length*.31);
 const span=d/words.length,n=Math.min(words.length-1,Math.floor(t/span));
 lastWord=words[n];return shape(lastWord,(t/span)%1);
}
// Version 6.1: deform only the original portrait texture using a feathered
// photo patch. No added mouth paint, teeth, solid oval, sharp clipping edge,
// pixel readback (cross-origin photos can remain untouched), or other overlay.
const patch=document.createElement('canvas'),pctx=patch.getContext('2d');
patch.width=84;patch.height=62;
function smooth(a,b,v){const t=Math.max(0,Math.min(1,(v-a)/(b-a)));return t*t*(3-2*t)}
let widthScale=1;
function renderPhoto(open,now){
 ctx.clearRect(0,0,440,434);
 if(!ready){ctx.fillStyle='#17263b';ctx.fillRect(0,0,440,434);return;}
 const scale=Math.max(440/img.naturalWidth,434/img.naturalHeight);
 const sw=440/scale,sh=434/scale;
 const sx=(img.naturalWidth-sw)/2,sy=(img.naturalHeight-sh)/2;
 ctx.drawImage(img,sx,sy,sw,sh,0,0,440,434);
 const cx=position[0]*440,cy=position[1]*434;
 const rx=35,ry=24,openAmount=Math.max(0,Math.min(1,open));
 const gap=7.4*openAmount; // Previous renderer split the mouth by up to 21px.
 if(gap>.035){
  // Draw the portrait's own pixels into a small deformed texture patch. Each
  // row uses a smooth inverse map: lip pixels shift away from the center while
  // the original seam is stretched very slightly, with the cheeks held still.
  pctx.clearRect(0,0,patch.width,patch.height);
  for(let row=-ry;row<ry;row+=.65){
   const ny=Math.abs(row)/ry;
   const fadeY=1-smooth(.64,1,ny);
   const nearSeam=smooth(0,.10,ny);
   const delta=(row<0?1:-1)*gap*.5*fadeY*nearSeam;
   const fromY=cy+row+delta;
   const destY=patch.height*.5+row;
   const fromX=cx-rx;
   const mouthScale=1+(widthScale-1)*.05*(1-smooth(.5,1,ny));
   const sampleWidth=2*rx/mouthScale;
   pctx.drawImage(img,sx+(fromX+(2*rx-sampleWidth)*.5)/scale,
      sy+fromY/scale,sampleWidth/scale,.92/scale,
      patch.width*.5-rx,destY,2*rx,1.16);
  }
  // Feather the *photo patch*, not a synthetic mouth: at the outer edge the
  // original unmodified portrait shows through continuously in every direction.
  pctx.save();pctx.globalCompositeOperation='destination-in';
  pctx.translate(patch.width*.5,patch.height*.5);pctx.scale(rx,ry);
  const mask=pctx.createRadialGradient(0,0,.30,0,0,1);
  mask.addColorStop(0,'rgba(0,0,0,1)');
  mask.addColorStop(.53,'rgba(0,0,0,.98)');
  mask.addColorStop(.78,'rgba(0,0,0,.60)');
  mask.addColorStop(1,'rgba(0,0,0,0)');
  pctx.fillStyle=mask;pctx.fillRect(-1,-1,2,2);pctx.restore();
  ctx.drawImage(patch,cx-patch.width*.5,cy-patch.height*.5);
 }
 // A placement guide only while calibrating (never over the speaking face).
 if(aligning){
  ctx.save();ctx.strokeStyle='#facc15';ctx.lineWidth=1.4;
  ctx.beginPath();ctx.ellipse(cx,cy,rx,ry,0,0,Math.PI*2);ctx.stroke();
  ctx.beginPath();ctx.moveTo(cx-4,cy);ctx.lineTo(cx+4,cy);ctx.moveTo(cx,cy-4);ctx.lineTo(cx,cy+4);ctx.stroke();ctx.restore();
 }
}
let lastMeter=0;
function draw(now){
 requestAnimationFrame(draw);
 if(!ready)return;
 const demo=now<demoUntil;
 // Vary the demo on a slower speech-like cadence, with a real rest between
 // phrases. Avoid abrupt word-boundary snapping using a time-based envelope.
 const phase=now/1000;
 let demoOpen=Math.max(0,Math.sin(phase*7.1))*.51+Math.max(0,Math.sin(phase*10.8+.9))*.20;
 demoOpen*=.65+.35*Math.max(0,Math.sin(phase*1.7));
 let v=demo?{open:demoOpen,wide:1+.07*Math.sin(phase*3.9)}:(active&&!sound.paused&&!sound.ended?sayWord():{open:0,wide:1});
 const dt=Math.min(.06,Math.max(.008,(now-(clock||now))/1000));clock=now;
 const follow=1-Math.exp(-dt/(v.open>mouthOpen?.085:.120));
 widthScale+=(v.wide-widthScale)*(1-Math.exp(-dt/.115));
 mouthOpen+=(v.open-mouthOpen)*follow;
 renderPhoto(mouthOpen,now);
 if(now-lastMeter>100){
  $('meter').textContent='Mouth motion: '+(demo?'TEST':active?'VOICE':'IDLE')+' · '+Math.round(mouthOpen*100)+'% · lip center '+Math.round(position[0]*100)+'%, '+Math.round(position[1]*100)+'%';
  if(demo||active)$('caption').textContent=(lastWord?'Speaking: '+lastWord+' · ':'')+C.text;
  lastMeter=now;
 }
 if(!demo&&demoUntil){demoUntil=0;status('Test completed. If motion was misplaced, select Align lips.');}
}
$('speak').onclick=async()=>{
 if(!C.audio){status(C.audioError||'Neural MP3 unavailable. Use Test lip motion to test the photo.');return;}
 try{demoUntil=0; if(!sound.paused)sound.pause();sound.currentTime=0;await sound.play();}
 catch(e){status('Audio playback was blocked: '+(e.message||e.name)+'. Try the native audio Play control.');}
};
$('stop').onclick=()=>{sound.pause();demoUntil=0;active=false;lastWord='';status('Stopped')};
$('demo').onclick=()=>{if(!ready){status('Portrait is still loading. Try again when visible.');return;}sound.pause();active=false;lastWord='';demoUntil=performance.now()+5000;status('Mouth test ACTIVE: soft movement at aligned lip position. Use Align lips if misplaced.');};
sound.onplay=()=>{demoUntil=0;active=true;status('Speaking with '+C.name+' neural voice')};
sound.onpause=()=>{active=false;if(!sound.ended)status('Paused')};
sound.onended=()=>{active=false;lastWord='';status('Finished')};
sound.onerror=()=>status('MP3 playback error '+(sound.error?sound.error.code:'unknown')+'. Please report this number.');
$('reset').onclick=()=>{position=defaults[C.name]||[.5,.68];hasSavedAlignment=false;aligning=true;canvas.classList.add('calibrating');$('calLabel').style.display='block';try{localStorage.removeItem(key)}catch(e){}status('Alignment reset. CLICK THE CENTER OF THE REAL LIPS.');};
$('calibrate').onclick=()=>{aligning=!aligning;canvas.classList.toggle('calibrating',aligning);$('calLabel').style.display=aligning?'block':'none';status(aligning?'Click directly on the center of the real lips in the portrait.':'Lip alignment saved.');};
canvas.onclick=e=>{if(!aligning)return;const r=canvas.getBoundingClientRect();position=[Math.max(.05,Math.min(.95,(e.clientX-r.left)/r.width)),Math.max(.1,Math.min(.9,(e.clientY-r.top)/r.height))];try{localStorage.setItem(key,JSON.stringify(position))}catch(e){}hasSavedAlignment=true;aligning=false;canvas.classList.remove('calibrating');$('calLabel').style.display='none';status('Lip position saved for '+C.name+'. Click Test lip motion.');};
window.addEventListener('pagehide',()=>{sound.pause()});requestAnimationFrame(draw);
})();
</script></body></html>'''


st.markdown('<div class="mwai-heading"><h1>Multi-Workflow AI</h1><p>Four specialists. Four independent conversations. Real portrait avatars and neural voices.</p></div>', unsafe_allow_html=True)
st.caption(f"Current assistant: **{info['name']}** · {mode} · {info['room']}")
left, right = st.columns([1, 1.12], gap="large")
with left:
    st.subheader(f"Talk with {info['name']}")
    render_avatar(info, data)
    st.caption("Realistic portrait. First click **Align lips**, then click the center of the lips in the photo. **Test lip motion** previews subtle, feathered photo movement without audio. Accurate neural video lip-sync requires a dedicated talking-head model.")
    if data.get("audio_error"):
        st.warning(f"Voice status for {info['name']}: {data['audio_error']}")
    if data["last_reply"] and st.button(f"Retry {info['name']} neural audio", key=f"retry_audio_{mode}"):
        data["last_audio"], data["word_timings"], data["audio_error"] = neural_speech(data["last_reply"], info["voice"])
        data["reply_id"] = uuid.uuid4().hex
        st.rerun()
    st.markdown("#### 📎 Private reference file")
    upload = st.file_uploader(f"Upload for {info['name']} only", type=["txt","md","csv","json","py","html","ics","pdf"], key=f"mwai_v6_upload_{mode}")
    if upload is not None:
        digest = hashlib.sha256(upload.getvalue()).hexdigest()
        if digest != data["seen_upload_digest"]:
            data["file_text"] = extract_file(upload)
            data["file_name"] = upload.name
            data["seen_upload_digest"] = digest
        st.success(f"{info['name']} has: {upload.name} · {len(data['file_text']):,} characters")
    elif data["file_name"]:
        st.info(f"Reference retained in this session: {data['file_name']}")
    if data["file_text"]:
        with st.expander("Preview this assistant's file"):
            st.text(data["file_text"][:2000])

with right:
    st.subheader(f"{info['name']}'s conversation")
    # Display ONLY data for the currently selected assistant.
    thread = st.container(height=390)
    with thread:
        if not data["messages"]:
            st.info(f"This is {info['name']}'s own conversation. Other assistants cannot see it.")
        for m in data["messages"]:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                st.caption(m["time"])

    if hasattr(st, "audio_input"):
        recording = st.audio_input(f"Record a message for {info['name']}", key=f"mwai_v6_mic_{mode}")
        if recording:
            raw = recording.getvalue()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != data["seen_mic_digest"]:
                data["seen_mic_digest"] = digest
                try:
                    import speech_recognition as sr
                    recognizer = sr.Recognizer()
                    with sr.AudioFile(io.BytesIO(raw)) as src:
                        recognized = recognizer.recognize_google(recognizer.record(src), language="en-US")
                    with st.spinner(f"{info['name']} is answering..."):
                        process_message(mode, data, recognized, attach_reference=bool(data["file_text"]))
                    st.rerun()
                except Exception:
                    st.warning("Couldn't transcribe that recording. Please type your message below.")
    with st.form(key=f"mwai_v6_form_{mode}", clear_on_submit=True):
        prompt = st.text_area("Your message", placeholder=f"Ask {info['name']} anything in their specialty...", height=95)
        include_reference = st.checkbox("Include this workspace's reference file", value=bool(data["file_text"]), disabled=not bool(data["file_text"]))
        send = st.form_submit_button(f"Send to {info['name']}", type="primary", use_container_width=True)
    if send:
        if not prompt.strip() and not (include_reference and data["file_text"]):
            st.warning("Type a message or include a reference file.")
        else:
            with st.spinner(f"{info['name']} is thinking and preparing speech..."):
                process_message(mode, data, prompt, include_reference)
            st.rerun()

st.divider()
st.subheader(f"{info['name']}'s task list")
with st.form(key=f"mwai_v6_tasks_{mode}", clear_on_submit=True):
    task = st.text_input("New task", placeholder="Add a private task for this assistant")
    add = st.form_submit_button("Add task")
if add and task.strip():
    data["tasks"].append({"id": uuid.uuid4().hex, "text": task.strip(), "done": False})
    st.rerun()
for t in list(data["tasks"]):
    a,b=st.columns([10,1])
    with a:
        t["done"] = st.checkbox(t["text"], value=t["done"], key=f"mwai_v6_task_{mode}_{t['id']}")
    with b:
        if st.button("✕", key=f"mwai_v6_del_{mode}_{t['id']}"):
            data["tasks"] = [x for x in data["tasks"] if x["id"] != t["id"]]
            st.rerun()
st.caption("Conversation and task data live in this Streamlit browser session; a server restart or new session can reset them. No other assistant's history is included in AI requests.")
