"""Seller Assist premium-pastel design layer. Loaded after the legacy v16 stylesheet.

Purely a presentation layer; no business records, AI settings, or API keys here.
"""
import streamlit as st

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&family=Nunito+Sans:wght@400;500;600;700;800&family=Quicksand:wght@600;700&display=swap');
:root {
  --sa-lavender:#f7f2ff; --sa-purple:#7052b8; --sa-pink:#ff75ad;
  --sa-mint:#bdece1; --sa-honey:#ffe4aa; --sa-ink:#293047;
  --sa-muted:#5c6177; --sa-line:#e8dff4; --sa-white:#fff;
  --sa-shadow:0 12px 28px rgba(71,45,118,.075);
}
html { scroll-behavior: smooth; }
.stApp, [data-testid="stAppViewContainer"] {
  color:var(--sa-ink)!important; font-family:'Nunito Sans',sans-serif!important;
  background:
    radial-gradient(circle at 14% 12%, rgba(255,255,255,.12) 0, transparent 18%),
    radial-gradient(circle at 88% 10%, rgba(255,194,220,.16) 0, transparent 21%),
    radial-gradient(circle at 7% 72%, rgba(189,236,225,.13) 0, transparent 18%),
    linear-gradient(180deg, #9080be 0%, #8372b3 100%)!important;
  background-attachment:fixed!important;
}
.block-container {max-width:1500px!important; padding:1.9rem 2.1rem 3.5rem!important;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#7969ac 0%,#8a79bd 100%)!important; border-right:1px solid rgba(255,255,255,.12)!important;}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:1.45rem;}
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div {color:#fff!important;}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] {gap:.42rem;}
[data-testid="stSidebar"] .stRadio label:has(input:checked) {background:rgba(255,255,255,.18)!important;border-radius:12px;}
[data-testid="stSidebar"] .stRadio label {padding:.42rem .55rem;border-radius:12px;transition:background .18s ease;}
[data-testid="stSidebar"] .stRadio label:hover {background:rgba(255,255,255,.10)!important;}
.stApp p, .stApp li, .stApp label, .stApp small {font-family:'Nunito Sans',sans-serif;}
.stApp h1,.stApp h2,.stApp h3,.stApp h4 {font-family:'Fredoka',sans-serif;letter-spacing:-.018em;color:var(--sa-ink);}
.stApp h2 {font-size:clamp(1.45rem,2.1vw,1.8rem);} .stApp h3{font-size:1.24rem;}
.stApp p {line-height:1.58;} .stCaptionContainer p,[data-testid="stCaptionContainer"] p {color:var(--sa-muted)!important;font-size:.83rem!important;}
hr {border-color:var(--sa-line)!important;}
.kawaii-header {background:linear-gradient(130deg,#7f6bad 0%,#947fc1 58%,#b590cc 100%)!important;
  border:1px solid rgba(255,255,255,.12)!important;border-radius:28px!important;
  box-shadow:var(--sa-shadow)!important;padding:clamp(22px,3vw,38px)!important;
  margin-bottom:24px!important;position:relative;overflow:hidden;}
.kawaii-header:after {content:'✿';position:absolute;right:16%;top:-38px;font-size:165px;color:rgba(255,117,173,.085);pointer-events:none;line-height:1;}
.kawaii-header h1 {font-size:clamp(1.75rem,3vw,2.65rem)!important;line-height:1.15!important;
 color:#fff!important;font-family:'Fredoka',sans-serif!important;max-width:750px;text-shadow:0 1px 1px rgba(0,0,0,.08);}
.kawaii-header h1 span{display:block!important;margin-top:11px;color:#fdf2ff!important;
  font:800 .78rem 'Nunito Sans',sans-serif!important;letter-spacing:.105em;line-height:1.5;}
.kawaii-header p {font-size:1rem!important;max-width:680px;line-height:1.7!important;color:#f7f4ff!important;}
.kawaii-badge {background:rgba(255,255,255,.18)!important;color:#fff!important;border:1px solid rgba(255,255,255,.22)!important;
  box-shadow:none!important;font:800 .74rem 'Nunito Sans',sans-serif!important;padding:8px 13px!important;}
.kawaii-card,.kawaii-panel {background:#fff!important;border:1px solid var(--sa-line)!important;
 border-radius:21px!important;box-shadow:var(--sa-shadow)!important;padding:21px!important;}
.kawaii-card {min-height:157px;transition:transform .2s ease,box-shadow .2s ease!important;}
.kawaii-card:hover {transform:translateY(-3px)!important;box-shadow:0 16px 30px rgba(71,45,118,.12)!important;}
.kawaii-card h4 {color:#625674!important;font:800 .73rem 'Nunito Sans',sans-serif!important;letter-spacing:.08em!important;}
.kawaii-card .big-num {color:#443268!important;font:700 clamp(1.7rem,2.6vw,2.4rem) 'Fredoka',sans-serif!important;
 letter-spacing:-.035em;font-variant-numeric:tabular-nums;}
.kawaii-card small {color:#676075!important;font-size:.82rem!important;font-weight:650!important;}
/* Streamlit's native containers own their widgets; do not wrap them across markdown calls. */
[data-testid="stVerticalBlockBorderWrapper"] > div {border-radius:21px!important;}
[data-testid="stExpander"] {background:#fff!important;border:1px solid var(--sa-line)!important;
 border-radius:17px!important;box-shadow:0 5px 18px rgba(71,45,118,.035)!important;overflow:hidden;}
[data-testid="stExpander"] summary {padding:.3rem .45rem;}
[data-testid="stForm"] {background:#fff!important;border:1px solid var(--sa-line)!important;
 border-radius:20px!important;box-shadow:var(--sa-shadow)!important;padding:1rem!important;}
[data-testid="stChatMessage"] {border-radius:16px!important;background:#f9f6ff!important;border:1px solid #eee7f9!important;margin-bottom:.42rem;}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] p {font-size:.92rem!important;}
[data-testid="stFileUploader"] section {border:1.5px dashed #c9b7e6!important;border-radius:16px!important;background:#fdfbff!important;padding:.6rem;}
[data-testid="stFileUploader"] section:hover {background:#f7f2ff!important;}
.stButton > button,.stDownloadButton > button,div[data-testid="stFormSubmitButton"] > button {
 background:#fff!important;color:#544276!important;border:1px solid #ddd2ef!important;
 border-radius:13px!important;box-shadow:0 3px 8px rgba(63,41,105,.06)!important;
 font:800 .88rem 'Nunito Sans',sans-serif!important;padding:.58rem .95rem!important;
 min-height:43px;transition:transform .17s ease,box-shadow .17s ease,background .17s ease!important;white-space:normal;}
.stButton > button:hover,.stDownloadButton > button:hover,div[data-testid="stFormSubmitButton"] > button:hover {
 background:#f6efff!important;transform:translateY(-2px);box-shadow:0 9px 18px rgba(63,41,105,.12)!important;}
.stButton > button[kind="primary"],div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
 background:linear-gradient(110deg,#7052b8,#9167ce)!important;border:1px solid #7052b8!important;
 color:#fff!important;box-shadow:0 7px 16px rgba(112,82,184,.17)!important;}
.stButton > button[kind="primary"]:hover,div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
 background:linear-gradient(110deg,#6345ad,#8357c0)!important;color:#fff!important;}
.stButton > button:focus-visible,.stDownloadButton > button:focus-visible,button:focus-visible,
input:focus-visible,textarea:focus-visible,select:focus-visible {outline:3px solid #e694c1!important;outline-offset:3px!important;}

[data-testid="stMetric"] {background:rgba(255,255,255,.96)!important;border:1px solid #e9def4!important;border-radius:17px!important;padding:12px 14px!important;box-shadow:0 8px 18px rgba(32,20,64,.10)!important;}
[data-testid="stMetricLabel"] p, [data-testid="stMetricDelta"] {color:#62587a!important;}
[data-testid="stMetricValue"] {color:#2f3550!important;}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,[data-testid="stSelectbox"] [data-baseweb="select"] > div {
 border-radius:12px!important;border-color:#ddd3ea!important;background:#fff!important;
 color:var(--sa-ink)!important;font-family:'Nunito Sans',sans-serif!important;}
[data-testid="stProgressBar"] > div > div {background:#7052b8!important;border-radius:99px!important;}
[data-testid="stAlert"] {border-radius:15px!important;border-width:1px!important;}
.premium-section {margin:1.3rem 0 1rem;}
.premium-eyebrow {font:800 .73rem 'Nunito Sans',sans-serif;color:#8663b1;letter-spacing:.16em;text-transform:uppercase;}
.premium-section h2 {margin:.28rem 0 .1rem;font:600 clamp(1.35rem,2vw,1.75rem) 'Fredoka',sans-serif;color:#443268;}
.premium-section p {color:#686176;font-size:.93rem;margin:0;}
.premium-mascot {min-height:108px;display:flex;align-items:center;gap:12px;margin:0 0 .55rem;
 padding:17px 15px;border-radius:18px;border:1px solid #ebdff4;background:#fff;
 box-shadow:0 8px 18px rgba(71,45,118,.045);transition:transform .18s ease;}
.premium-mascot:hover {transform:translateY(-2px);}
.premium-mascot .premium-emoji {font-size:2.3rem;line-height:1;flex:0 0 46px;text-align:center;}
.premium-mascot strong {display:block;color:#45345f;font:700 1.06rem 'Fredoka',sans-serif;}
.premium-mascot small {display:block;color:#6e6478;font:600 .75rem/1.5 'Nunito Sans',sans-serif;margin-top:3px;}
.premium-mascot--pink{background:linear-gradient(130deg,#fff,#fff0f6);}
.premium-mascot--yellow{background:linear-gradient(130deg,#fff,#fff7e4);}
.premium-mascot--mint{background:linear-gradient(130deg,#fff,#eaf9f3);}
.premium-mascot--blue{background:linear-gradient(130deg,#fff,#e9f5ff);}
.premium-note {font:700 .78rem 'Nunito Sans',sans-serif;color:#665c75;background:#fff9e9;
 border:1px solid #f2e6c1;border-radius:12px;padding:9px 13px;margin:.3rem 0 1.2rem;}
.premium-avatar-title{text-align:center;color:#544276;font:700 1.02rem 'Fredoka',sans-serif;margin-bottom:.45rem;}
@media (max-width:1100px) {.block-container{padding:1.1rem 1.15rem 2.3rem!important;}}
@media (max-width:780px) {
 .block-container {padding:.9rem .8rem 2.4rem!important;}
 .kawaii-header {padding:21px!important;border-radius:20px!important;}
 .kawaii-header h1 {font-size:1.8rem!important;}
 .kawaii-header:after{right:-24px;top:-12px;font-size:100px;}
 .kawaii-card{min-height:auto;}
 .premium-mascot{min-height:88px;padding:12px;}
 [data-testid="stHorizontalBlock"] {flex-wrap:wrap!important;}
 [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {min-width:min(100%,260px)!important;flex:1 1 250px!important;}
 [data-testid="stVerticalBlock"] {gap:.7rem;}
}
@media (prefers-reduced-motion: reduce) {
 *,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important;scroll-behavior:auto!important;}
}
"""


def apply_premium_theme():
    st.markdown('<style>' + CSS + '</style>', unsafe_allow_html=True)
