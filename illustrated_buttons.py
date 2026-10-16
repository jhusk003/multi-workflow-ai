"""Seller Assist v18: locally bundled illustration-backed, native Streamlit buttons.

The graphics remain ordinary WebP files in assets/illustrated_buttons; they load
as data URLs so Render does not need to expose or separately serve a static folder.
The clickable surfaces are st.button widgets (not inert HTML or JavaScript).
"""
import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "illustrated_buttons"
BUTTON_ASSETS = {
    "sa_image_inventory": "inventory.webp",
    "sa_image_packing": "packing.webp",
    "sa_image_listing": "listing.webp",
    "sa_image_market": "market.webp",
}


@lru_cache(maxsize=1)
def _css():
    styles = ["""
/* ILLUSTRATED SELLER HEADQUARTERS v18 — native, keyboard-accessible buttons */
.sa-village-intro {padding:4px 0 15px;}
.sa-village-intro .eyebrow {font:800 .72rem 'Nunito Sans',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:#7052b8;}
.sa-village-intro h2 {font:700 clamp(1.55rem,2.9vw,2.2rem) 'Fredoka',sans-serif;color:#293047;margin:.25rem 0 .1rem;}
.sa-village-intro p {color:#635c74;font-size:.94rem;margin:0;}
.sa-village-caption {font:700 .82rem/1.45 'Nunito Sans',sans-serif;color:#655b74;text-align:center;margin:-8px 0 13px;}
/* The scoped key selectors intentionally win over the old broad button styling. */
.stApp [class*="st-key-sa_image_"] button[kind="primary"] {
  display:block!important;width:100%!important;min-width:0!important;
  height:auto!important;min-height:0!important;aspect-ratio: 7 / 4!important;
  padding:0!important;border:0!important;border-radius:19px!important;
  background-color:#fff!important;background-position:center!important;
  background-size:100% 100%!important;background-repeat:no-repeat!important;
  color:transparent!important;font-size:0!important;line-height:0!important;
  box-shadow:0 9px 20px rgba(44,32,92,.10)!important;
  cursor:pointer!important;overflow:hidden!important;
  transition:transform .19s ease,box-shadow .19s ease,filter .19s ease!important;
}
.stApp [class*="st-key-sa_image_"] button p,
.stApp [class*="st-key-sa_image_"] button span {font-size:0!important;color:transparent!important;line-height:0!important;}
.stApp [class*="st-key-sa_image_"] button:hover {transform:translateY(-4px) scale(1.012)!important;box-shadow:0 17px 29px rgba(44,32,92,.17)!important;filter:saturate(1.05)!important;}
.stApp [class*="st-key-sa_image_"] button:active {transform:translateY(0) scale(.99)!important;}
.stApp [class*="st-key-sa_image_"] button:focus-visible {outline:4px solid #7052b8!important;outline-offset:4px!important;}
@media (max-width:720px) {.stApp [class*="st-key-sa_image_"] button[kind="primary"] {border-radius:14px!important;}}
@media (prefers-reduced-motion:reduce) {.stApp [class*="st-key-sa_image_"] button[kind="primary"] {transition:none!important;}}
"""]
    for key, filename in BUTTON_ASSETS.items():
        file = ASSET_DIR / filename
        if not file.is_file():
            raise FileNotFoundError(f"Illustrated button is missing: {file}")
        encoded = base64.b64encode(file.read_bytes()).decode("ascii")
        # Exact st-key class, with class substring fallback for Streamlit variants.
        styles.append(
            f'.stApp [class*="st-key-{key}"] button[kind="primary"] {{'
            f'background-image:url("data:image/webp;base64,{encoded}")!important;'
            f'background-color:#fff!important;background-size:100% 100%!important;}}'
        )
    return "\n".join(styles)


def inject_illustrated_button_styles():
    st.markdown('<style>' + _css() + '</style>', unsafe_allow_html=True)
