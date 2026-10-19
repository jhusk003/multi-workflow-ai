"""Seller Assist v19: expanded illustrated dashboard with a town hero and extra image buttons."""
import base64
import csv
import io
from functools import lru_cache
from pathlib import Path

import streamlit as st

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "illustrated_buttons"
BUTTON_ASSETS = {
    "sa_image_inventory": "inventory.webp",
    "sa_image_packing": "packing.webp",
    "sa_image_listing": "listing.webp",
    "sa_image_market": "market.webp",
    "sa_image_finance": "finance.webp",
    "sa_image_supplier": "supplier.webp",
    "sa_image_messages": "messages.webp",
    "sa_image_promo": "promo.webp",
    "sa_image_settings": "settings.webp",
    "sa_image_team": "team.webp",
    "sa_image_home_inventory": "inventory.webp",
    "sa_image_home_listing": "listing.webp",
    "sa_image_home_packing": "packing.webp",
}
HERO_ASSET = "town.webp"


def _b64(filename: str) -> str:
    file = ASSET_DIR / filename
    if not file.is_file():
        raise FileNotFoundError(f"Missing illustrated asset: {file}")
    return base64.b64encode(file.read_bytes()).decode("ascii")


@lru_cache(maxsize=1)
def _css() -> str:
    hero = _b64(HERO_ASSET)
    styles = [f"""
/* SELLER ASSIST TOWN v19 */
.sa-town-hero {{
  position:relative; border-radius:30px; min-height:360px; overflow:hidden;
  background-image:linear-gradient(115deg, rgba(255,255,255,.08), rgba(255,255,255,.0)), url('data:image/webp;base64,{hero}');
  background-size:cover; background-position:center; box-shadow:0 18px 36px rgba(44,32,92,.12);
  border:1px solid rgba(113,82,184,.16); margin:.2rem 0 1.1rem;
}}
.sa-town-hero:before {{content:''; position:absolute; inset:0; background:linear-gradient(90deg, rgba(255,255,255,.88) 0%, rgba(255,255,255,.72) 34%, rgba(255,255,255,.24) 68%, rgba(255,255,255,.10) 100%);}}
.sa-town-overlay {{position:relative; z-index:2; padding:26px 28px; max-width:650px;}}
.sa-town-chip {{display:inline-block; background:#fff6d6; border:1px solid #f4d774; color:#705200; padding:6px 12px; border-radius:999px; font:800 .72rem 'Nunito Sans', sans-serif; letter-spacing:.08em; text-transform:uppercase;}}
.sa-town-hero h1 {{font:700 clamp(1.9rem, 4vw, 3.2rem) 'Fredoka', sans-serif; color:#2c3150; margin:.65rem 0 .35rem; line-height:1.02;}}
.sa-town-hero p {{font:600 .98rem/1.62 'Nunito Sans', sans-serif; color:#4d5971; margin:0; max-width:520px;}}
.sa-town-badges {{display:flex; flex-wrap:wrap; gap:.45rem; margin-top:1rem;}}
.sa-town-badge {{background:rgba(255,255,255,.86); color:#5f5674; border:1px solid #e5dcf4; padding:7px 11px; border-radius:14px; font:700 .78rem 'Nunito Sans',sans-serif;}}
.sa-village-intro {{padding:2px 0 15px;}}
.sa-village-intro .eyebrow {{font:800 .72rem 'Nunito Sans',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:#7052b8;}}
.sa-village-intro h2 {{font:700 clamp(1.45rem,2.8vw,2rem) 'Fredoka',sans-serif;color:#293047;margin:.25rem 0 .1rem;}}
.sa-village-intro p {{color:#635c74;font-size:.94rem;margin:0;}}
.sa-village-caption {{font:700 .82rem/1.45 'Nunito Sans',sans-serif;color:#655b74;text-align:center;margin:-8px 0 13px;}}
.stApp [class*="st-key-sa_image_"] button[kind="primary"] {{
  display:block!important;width:100%!important;min-width:0!important;
  height:auto!important;min-height:0!important;aspect-ratio:7 / 4!important;
  padding:0!important;border:0!important;border-radius:19px!important;
  background-color:#fff!important;background-position:center!important;
  background-size:100% 100%!important;background-repeat:no-repeat!important;
  color:transparent!important;font-size:0!important;line-height:0!important;
  box-shadow:0 9px 20px rgba(44,32,92,.10)!important;
  cursor:pointer!important;overflow:hidden!important;
  transition:transform .19s ease,box-shadow .19s ease,filter .19s ease!important;
}}
.stApp [class*="st-key-sa_image_"] button p,
.stApp [class*="st-key-sa_image_"] button span {{font-size:0!important;color:transparent!important;line-height:0!important;}}
.stApp [class*="st-key-sa_image_"] button:hover {{transform:translateY(-4px) scale(1.012)!important;box-shadow:0 17px 29px rgba(44,32,92,.17)!important;filter:saturate(1.05)!important;}}
.stApp [class*="st-key-sa_image_"] button:active {{transform:translateY(0) scale(.99)!important;}}
.stApp [class*="st-key-sa_image_"] button:focus-visible {{outline:4px solid #7052b8!important;outline-offset:4px!important;}}
@media (max-width: 900px) {{ .sa-town-hero {{min-height:300px;}} .sa-town-overlay {{padding:20px;}} }}
@media (max-width: 720px) {{ .stApp [class*="st-key-sa_image_"] button[kind="primary"] {{border-radius:14px!important;}} .sa-town-hero:before {{background:linear-gradient(180deg, rgba(255,255,255,.90) 0%, rgba(255,255,255,.78) 48%, rgba(255,255,255,.35) 100%);}} }}
@media (prefers-reduced-motion: reduce) {{ .stApp [class*="st-key-sa_image_"] button[kind="primary"] {{transition:none!important;}} }}
"""
    ]
    for key, filename in BUTTON_ASSETS.items():
        encoded = _b64(filename)
        styles.append(
            f'.stApp [class*="st-key-{key}"] button[kind="primary"] {{'
            f'background-image:url("data:image/webp;base64,{encoded}")!important;'
            f'background-color:#fff!important;background-size:100% 100%!important;}}'
        )
    return "\n".join(styles)


@lru_cache(maxsize=1)
def _finance_csv() -> bytes:
    rows = [
        ["metric", "value"],
        ["sample_revenue", "12450"],
        ["sample_cogs", "5120"],
        ["sample_gross_profit", "7330"],
        ["sample_ad_spend", "860"],
        ["sample_net_after_ads", "6470"],
        ["sample_margin_percent", "51.97"],
        ["recommended_price", "24.99"],
    ]
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode("utf-8")


@lru_cache(maxsize=1)
def _supplier_csv() -> bytes:
    rows = [
        ["supplier", "lead_days", "minimum_order", "notes"],
        ["Sunbeam Packs", "7", "100", "Low shipping cost, good for starter orders"],
        ["Mint Harbor Goods", "14", "250", "Better unit cost for larger orders"],
        ["Lavender Lane Studio", "10", "150", "Cute packaging and inserts"],
    ]
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode("utf-8")


@lru_cache(maxsize=1)
def _promo_text() -> str:
    return """Promo ideas for this week\n\n1. New drop alert 🌈 Fresh picks just landed in the shop.\n2. Limited bundle 💌 Pair your bestseller with a matching add-on.\n3. Weekend reminder ✨ Restock your faves before they sell out.\n4. Customer love 💖 Share a short review and a styled product photo.\n5. Behind the scenes 🎨 Show packing, sketching, or sourcing clips.\n"""


@lru_cache(maxsize=1)
def _messages_text() -> str:
    return """Customer reply starters\n\nOrder update\nHi! Thanks so much for your order. I’m packaging it now and will send tracking as soon as it ships.\n\nShipping delay\nHi! I wanted to keep you updated — your package is on the way, but the carrier is moving a little slower than usual.\n\nCustom request\nHi! I’d love to help with that custom request. Send me the quantity, colors, and deadline you have in mind and I’ll suggest the best option.\n"""


def inject_illustrated_button_styles():
    st.markdown('<style>' + _css() + '</style>', unsafe_allow_html=True)


def render_illustrated_town_hero():
    st.markdown(
        """
    <div class="sa-town-hero">
      <div class="sa-town-overlay">
        <div class="sa-town-chip">Seller Assist Town · v19</div>
        <h1>Your whole shop as a tiny kawaii city</h1>
        <p>Use the original working shortcut buttons plus a new set of playful shop helpers. The town graphic can also double as a hero banner or dashboard background.</p>
        <div class="sa-town-badges">
          <span class="sa-town-badge">Amazon, Shopify, Etsy & eBay corners</span>
          <span class="sa-town-badge">Design, analytics, shipping & support</span>
          <span class="sa-town-badge">Real clickable image buttons below</span>
        </div>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_town_bonus_panel(panel_name: str):
    if not panel_name:
        return

    if panel_name == "finance":
        st.markdown("### 💰 Finance Desk")
        m1, m2, m3 = st.columns(3)
        m1.metric("Sample revenue", "$12,450")
        m2.metric("Gross margin", "51.97%")
        m3.metric("Suggested price", "$24.99")
        st.info("Use this panel for price checks, margin math, break-even thinking, and lightweight planning before you ask Morgan for a deeper analysis.")
        st.download_button("Download sample finance snapshot CSV", _finance_csv(), file_name="seller_assist_finance_snapshot.csv", mime="text/csv", use_container_width=True)

    elif panel_name == "supplier":
        st.markdown("### 📦 Supplier Hub")
        st.markdown("- Compare lead time, minimum order quantity, and packaging quality.\n- Keep backup suppliers for your fastest sellers.\n- Ask Taylor or Morgan to turn these into reorder rules.")
        st.download_button("Download sample supplier list CSV", _supplier_csv(), file_name="seller_assist_supplier_shortlist.csv", mime="text/csv", use_container_width=True)

    elif panel_name == "messages":
        st.markdown("### 💌 Customer Messages")
        st.code(_messages_text(), language="markdown")
        st.download_button("Download customer reply starters", _messages_text().encode("utf-8"), file_name="seller_assist_customer_replies.txt", mime="text/plain", use_container_width=True)

    elif panel_name == "promo":
        st.markdown("### 📣 Promo Studio")
        st.code(_promo_text(), language="markdown")
        st.download_button("Download promo copy ideas", _promo_text().encode("utf-8"), file_name="seller_assist_promo_ideas.txt", mime="text/plain", use_container_width=True)

    elif panel_name == "settings":
        st.markdown("### ⚙️ Shop Settings")
        st.success("Use this visual hub for future store controls like banners, color themes, fee assumptions, shipping profiles, packaging notes, and default message templates.")
        st.markdown("**Suggested settings to add next:**\n- Brand palette and hero image\n- Marketplace fee assumptions\n- Shipping speed presets\n- Packaging insert text\n- Favorite promo hashtags")

    elif panel_name == "team":
        st.markdown("### 🤖 AI Team")
        c1, c2, c3, c4 = st.columns(4)
        cards = [
            (c1, "Alex", "Student", "Explain math, inventory formulas, and technical logic."),
            (c2, "Jordan", "Freelancer", "Handle listings, copy, offers, and client-facing wording."),
            (c3, "Morgan", "Inventory & Business", "Run numbers for stock, margin, and budgets."),
            (c4, "Taylor", "Resource & Task", "Plan operations, timelines, and next actions."),
        ]
        for col, name, role, desc in cards:
            with col:
                st.markdown(f"**{name}**  \\n*{role}*  \\n{desc}")
        st.info("This button is a quick visual summary of how the four assistants split responsibilities inside Seller Assist.")
