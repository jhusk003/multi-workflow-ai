"""Finance Desk-only contrast fix for native Streamlit controls.

This is deliberately injected ONLY when finance() renders, after the v26 style fix.
No business data is touched.
"""

import streamlit as st

FINANCE_CSS = r"""
<style>
/* Seller Assist Finance v27: remove dark theme leakage into white surfaces. */
.stApp div[data-testid="stExpander"],
.stApp div[data-testid="stExpander"] details,
.stApp div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
  background-color:#fff!important;color:#253047!important;
  border-color:#d7c9e7!important;
}
/* Header is always light lavender; no dark-on-dark expander summary. */
.stApp div[data-testid="stExpander"] details > summary,
.stApp div[data-testid="stExpander"] summary,
.stApp div[data-testid="stExpander"] summary:hover,
.stApp div[data-testid="stExpander"] summary:focus-visible {
  background:#ede5fa!important;color:#25243f!important;
  border-color:#d7c9e7!important;
}
.stApp div[data-testid="stExpander"] summary *,
.stApp div[data-testid="stExpander"] summary p,
.stApp div[data-testid="stExpander"] summary span,
.stApp div[data-testid="stExpander"] summary svg,
.stApp div[data-testid="stExpander"] details [data-testid="stExpanderDetails"] p,
.stApp div[data-testid="stExpander"] details [data-testid="stExpanderDetails"] label,
.stApp div[data-testid="stExpander"] details [data-testid="stExpanderDetails"] small,
.stApp div[data-testid="stExpander"] details [data-testid="stExpanderDetails"] h1,
.stApp div[data-testid="stExpander"] details [data-testid="stExpanderDetails"] h2,
.stApp div[data-testid="stExpander"] details [data-testid="stExpanderDetails"] h3,
.stApp div[data-testid="stExpander"] details [data-testid="stExpanderDetails"] span,
.stApp div[data-testid="stExpander"] details [data-testid="stExpanderDetails"] [data-testid="stWidgetLabel"] * {
  color:#253047!important;fill:#253047!important;opacity:1!important;
  -webkit-text-fill-color:#253047!important;
}
/* Target Streamlit versions which omit stExpanderDetails on the inner wrapper. */
.stApp div[data-testid="stExpander"] label,
.stApp div[data-testid="stExpander"] [data-testid="stWidgetLabel"] *,
.stApp div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
.stApp div[data-testid="stExpander"] div[data-testid="stNumberInput"] label,
.stApp div[data-testid="stExpander"] div[data-testid="stSlider"] label {
  color:#253047!important;opacity:1!important;
  -webkit-text-fill-color:#253047!important;
}
.stApp div[data-testid="stExpander"] input,
.stApp div[data-testid="stExpander"] textarea,
.stApp div[data-testid="stExpander"] [data-baseweb="input"] input {
  background:#fff!important;color:#253047!important;caret-color:#253047!important;
  -webkit-text-fill-color:#253047!important;
  border-color:#a89abf!important;opacity:1!important;
}
.stApp div[data-testid="stExpander"] input::placeholder,
.stApp div[data-testid="stExpander"] textarea::placeholder {
  color:#665a7a!important;-webkit-text-fill-color:#665a7a!important;
}
/* Retain accessible white glyphs on dark +/- number steppers. */
.stApp div[data-testid="stExpander"] [data-testid="stNumberInput"] button {
  background:#332b48!important;color:#fff!important;
  -webkit-text-fill-color:#fff!important;
}
.stApp div[data-testid="stExpander"] [data-testid="stNumberInput"] button svg {
  fill:#fff!important;stroke:#fff!important;color:#fff!important;
}
/* Primary save button remains white-on-purple, not white-on-white. */
.stApp div[data-testid="stExpander"] .stButton button[kind="primary"],
.stApp div[data-testid="stExpander"] [data-testid="stBaseButton-primary"] {
  background:#58428e!important;color:#fff!important;
  -webkit-text-fill-color:#fff!important;border-color:#58428e!important;
}
.stApp div[data-testid="stExpander"] .stButton button[kind="primary"] * {
  color:#fff!important;-webkit-text-fill-color:#fff!important;
}
.stApp div[data-testid="stExpander"] .stButton button[kind="secondary"] {
  background:#f6f0ff!important;color:#382b5b!important;
  -webkit-text-fill-color:#382b5b!important;border-color:#d7c9e7!important;
}
/* All finance metric cards have dark type on white. */
.stApp [data-testid="stMetric"] {
  background:#fff!important;color:#253047!important;
}
.stApp [data-testid="stMetric"] *,
.stApp [data-testid="stMetricLabel"] p,
.stApp [data-testid="stMetricValue"] {
  color:#253047!important;-webkit-text-fill-color:#253047!important;
}
/* Keep large custom lavender page heading white. */
.stApp .sa-v20-header h1,.stApp .sa-v20-header p {color:#fff!important;-webkit-text-fill-color:#fff!important;}
.stApp .sa-v20-header .sa-v20-eyebrow{color:#fff4c9!important;-webkit-text-fill-color:#fff4c9!important;}
</style>
"""


def apply_finance_readability() -> None:
    st.markdown(FINANCE_CSS, unsafe_allow_html=True)
