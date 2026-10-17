"""DUSK_PAGES_V20_2 — Seller Assist short Home plus dedicated business-workflow pages.

Calls the existing app's calculation and export functions; does not replace AI, DB, or avatar logic.
All shop uploads are held in Streamlit session state. Sample data is always labeled.
"""
from __future__ import annotations

import csv
import io
import html
from dataclasses import dataclass
from typing import Any

import streamlit as st

from illustrated_buttons import (
    inject_illustrated_button_styles,
    render_illustrated_town_hero,
    render_town_bonus_panel,
)

HOME = "🏡 Home"
EXPLORE = "🗺️ Explore Town"  # SELLER ASSIST EXPLORE MODE v21
INVENTORY = "📦 Inventory Lab"
LISTINGS = "🎨 Listings & Marketing"
OPERATIONS = "🚚 Orders & Suppliers"
FINANCE = "💰 Finance Desk"
DATA = "📁 Shop Data"
TEAM = "🤖 AI Team"
SETTINGS = "⚙️ Settings"
PAGES = [HOME, EXPLORE, INVENTORY, LISTINGS, OPERATIONS, FINANCE, DATA, TEAM, SETTINGS]

MORGAN = "Level 1: Inventory Lab"
JORDAN = "Level 2: Listing Studio"
TAYLOR = "Level 3: Ops & PO Room"
ALEX = "Level 4: Finance & Tax Desk"


def go(page: str, model: str | None = None):
    """Defer changes to widget keys until the next rerun (Streamlit safety)."""
    st.session_state["sa_page_request"] = page
    if model:
        st.session_state["sa_mode_request"] = model
    st.rerun()


def _caption(text: str):
    st.markdown(f'<div class="sa-village-caption">{html.escape(text)}</div>', unsafe_allow_html=True)


def _image_button(key: str, label: str, help_text: str) -> bool:
    return st.button(label, key=key, help=help_text, type="primary", use_container_width=True)


def _top(eyebrow: str, title: str, subtitle: str):
    st.markdown(
        '<div class="sa-v20-header">'
        f'<div class="sa-v20-eyebrow">{html.escape(eyebrow)}</div>'
        f'<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


@dataclass
class ShopData:
    periods: list[str]
    sales: list[float]
    profit: list[float]
    sku_labels: list[str]
    sku_stock: list[int]
    sku_sales: list[int]
    inventory_csv: str
    kind: str
    source: str


def _records(raw: str):
    return list(csv.DictReader(io.StringIO(raw)))


def _safe_float(value, fallback=0.0) -> float:
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return fallback


def shop_data(c: dict[str, Any]) -> ShopData:
    raw = st.session_state.get("sa_shared_csv", "")
    demo = not raw
    if not raw:
        raw = c["SAMPLE_DASHBOARD_CSV"]
    rows = _records(raw)
    if not rows:
        raw, rows, demo = c["SAMPLE_DASHBOARD_CSV"], _records(c["SAMPLE_DASHBOARD_CSV"]), True
    keys = {k.strip().lower(): k for k in rows[0] if k}
    adj = 1 + st.session_state.get("sa_price_adjust", 0) / 100.0
    stock_rows = _records(c["SAMPLE_SELLER_CSV"])
    if "sales" in keys and "profit" in keys:
        period_key = keys.get("day") or keys.get("date") or keys.get("period")
        periods = [str(r.get(period_key, f"Period {i+1}")) if period_key else f"Period {i+1}" for i, r in enumerate(rows)]
        sales = [_safe_float(r.get(keys["sales"])) * adj for r in rows]
        profit = [_safe_float(r.get(keys["profit"])) * adj for r in rows]
        kind = "financial"
        inventory_csv = c["SAMPLE_SELLER_CSV"]
    elif "retail_price_usd" in keys and "weekly_units_sold" in keys:
        periods = [r.get(keys.get("sku", ""), f"SKU-{i+1}") for i, r in enumerate(rows)]
        sales, profit = [], []
        for r in rows:
            price = _safe_float(r.get(keys["retail_price_usd"])) * adj
            units = _safe_float(r.get(keys["weekly_units_sold"]))
            cost = _safe_float(r.get(keys.get("unit_cost_usd", "")))
            sales.append(price * units)
            profit.append((price - cost - price * c["active_fee_rate"]) * units)
        kind, inventory_csv, stock_rows = "inventory", raw, rows
    else:
        st.warning("The uploaded CSV isn't a recognized inventory or financial format. Showing the sample financial overview instead.")
        return _sample_data(c)
    sku_labels = [r.get("sku", f"SKU-{i+1}") for i, r in enumerate(stock_rows)]
    sku_stock = [int(_safe_float(r.get("stock_on_hand"))) for r in stock_rows]
    sku_sales = [int(_safe_float(r.get("weekly_units_sold"))) for r in stock_rows]
    return ShopData(periods, sales, profit, sku_labels, sku_stock, sku_sales,
                    inventory_csv, kind, "Sample data" if demo else "Your uploaded CSV")


def _sample_data(c):
    old = st.session_state.get("sa_shared_csv", "")
    st.session_state["sa_shared_csv"] = ""
    try:
        return shop_data(c)
    finally:
        st.session_state["sa_shared_csv"] = old


def _metrics(data: ShopData, c, compact=False):
    fx, sym = c["fx_rate"], c["fx_sym"]
    sales, profit = sum(data.sales)*fx, sum(data.profit)*fx
    margin = profit / sales * 100 if sales else 0
    cols = st.columns(3 if compact else 4)
    with cols[0]: st.metric("Sales · uploaded period", f"{sym}{sales:,.0f}")
    with cols[1]: st.metric("Estimated profit · period", f"{sym}{profit:,.0f}")
    with cols[2]: st.metric("Estimated margin", f"{margin:.1f}%")
    if not compact:
        with cols[3]: st.metric("SKUs tracked", len(data.sku_labels))
    st.caption(f"{data.source} · {('What-if price adjustment applied · ' if st.session_state.get('sa_price_adjust', 0) else '')}Do not interpret projections as booked revenue.")


def _model_link(model: str, text: str):
    if st.button(text, key=f"sa_open_{model.split(':')[0].replace(' ','_')}_{st.session_state.get('nav_selector','')}", use_container_width=True):
        go(TEAM, model)


def _styles():
    st.markdown("""<style>
    .sa-v20-header{background:linear-gradient(135deg,#5f4d94,#69568f 58%,#7460a7);border:1px solid rgba(255,255,255,.12);
      border-radius:24px;padding:22px 27px;margin:.1rem 0 1rem;box-shadow:0 12px 24px rgba(32,20,64,.14)}
    .sa-v20-header h1{font:700 clamp(1.7rem,3vw,2.5rem) Fredoka,sans-serif;color:#fff;margin:.25rem 0}
    .sa-v20-header p{color:#f5f2ff;font-size:.96rem;margin:0}
    .sa-v20-eyebrow{font:800 .72rem 'Nunito Sans',sans-serif;color:#fff7d7;letter-spacing:.12em;text-transform:uppercase}
    .sa-v20-title{font:700 1.3rem Fredoka,sans-serif;margin:14px 0 6px;color:#ffffff;text-shadow:0 1px 1px rgba(0,0,0,.08)}
    .sa-v20-panel{background:#fff;border:1px solid #e9def4;border-radius:17px;padding:14px 16px;margin:12px 0}
    .sa-town-hero{min-height:275px!important;background-position:center 51%!important;margin-top:0!important}
    .sa-town-hero h1{font-size:clamp(1.55rem,3vw,2.4rem)!important}
    .sa-town-hero .sa-town-overlay{padding:20px 24px!important}
    .sa-town-hero .sa-town-badges{display:none!important}
    @media (max-width:720px){.sa-town-hero{min-height:255px!important}.sa-v20-header{padding:17px}}
    </style>""", unsafe_allow_html=True)


def home(c, data):
    render_illustrated_town_hero()
    st.markdown('<div class="sa-v20-title">Your shop at a glance</div>', unsafe_allow_html=True)
    _metrics(data,c,compact=True)
    st.markdown('<div class="sa-v20-title">Where would you like to start?</div>', unsafe_allow_html=True)
    col1,col2,col3=st.columns(3,gap="small")
    with col1:
        if _image_button("sa_image_home_inventory", "Go to Inventory Lab", "Stock and restock tools"): go(INVENTORY)
        _caption("Review stock")
    with col2:
        if _image_button("sa_image_home_listing", "Go to Listings & Marketing", "Product listings and promotions"): go(LISTINGS)
        _caption("Grow listings")
    with col3:
        if _image_button("sa_image_home_packing", "Go to Orders & Suppliers", "Orders, suppliers and tasks"): go(OPERATIONS)
        _caption("Plan orders")
    todos=c["db_load_todos"]()
    left=len([t for t in todos if not t["done"]])
    st.caption(f"✅ {left} open shop tasks · ⭐ {st.session_state['seller_xp']} XP · Detailed tools are in the left menu.")
    if st.button("🗺️ Explore the town with my avatar →", key="sa_home_explore", use_container_width=True): go(EXPLORE)
    if st.button("Meet your talking AI specialists →", key="sa_home_team",use_container_width=True): go(TEAM)


def inventory(c, data):
    _top("Morgan's workspace", "Inventory Lab", "Upload inventory in Shop Data, review stock and create an explanatory restock estimate.")
    col1,col2=st.columns([1,1])
    with col1:
        if _image_button("sa_image_inventory","Inventory Lab — analyze synced stock","Run the rule-based stock estimate"):
            c["workspaces"][MORGAN]["tabpfn_report"] = c["run_tabpfn_inventory_forecast"](data.inventory_csv, c["active_fee_rate"])
            c["add_xp"](50)
            st.success("Inventory estimate saved in Morgan's workspace. +50 XP")
        _caption("Stock and restock estimate")
    with col2:
        st.markdown("#### Current stock snapshot")
        rows=_records(data.inventory_csv)
        if rows:
            st.dataframe([{"SKU":r.get("sku",""),"Product":r.get("product_name",""),"Units":r.get("stock_on_hand", ""),"Weekly sold":r.get("weekly_units_sold", "")} for r in rows],hide_index=True,use_container_width=True,height=260)
        st.caption("Sample stock is shown unless an inventory CSV is uploaded.")
    report=c["workspaces"][MORGAN].get("tabpfn_report")
    if report:
        with st.expander("Latest inventory result", expanded=True): st.markdown(report)
    _model_link(MORGAN,"Ask Morgan about my inventory →")
    if st.button("Upload / replace shop CSV",key="sa_inventory_upload",use_container_width=True): go(DATA)


def listings(c, data):
    _top("Jordan's workspace", "Listings & Marketing", "Keep creative work together: product listings, competitor research, customer replies and promos.")
    a,b=st.columns(2)
    with a:
        if _image_button("sa_image_listing","Create example listing CSV","Export a sample Etsy/Shopify listing"):
            c["workspaces"][JORDAN]["exported_listing_csv"] = c["generate_shopify_etsy_listing_csv"]("Artisan Ceramic Mug",f"{28*(1+c['active_fee_rate']):.2f}","Kitchen")
            c["add_xp"](50)
            st.success("Sample listing created in Jordan's workspace. +50 XP")
        _caption("Listing Studio · sample export")
    with b:
        if _image_button("sa_image_market","Market research","Run comparable-price lookup"):
            st.session_state["sa_listing_market"] = True
        _caption("Market Research · optional SerpApi")
    if c["workspaces"][JORDAN].get("exported_listing_csv"):
        st.download_button("Download latest listing CSV",c["workspaces"][JORDAN]["exported_listing_csv"],file_name="seller_listing.csv",mime="text/csv",key="sa_listing_export")
    if st.session_state.get("sa_listing_market"):
        query=st.text_input("Product to research",value="Hand-Poured Lavender Soy Candle",key="sa_market_query")
        if st.button("Check market",key="sa_market_run") and query.strip():
            st.markdown(c["fetch_serpapi_competitor_pricing"](query.strip()))
    st.markdown("#### Communication & promotions")
    m,p=st.columns(2)
    with m:
        if _image_button("sa_image_messages","Customer reply starters","Open the customer reply sample pack"):
            st.session_state["sa_bonus_panel"]="messages"
        _caption("Customer Messages")
    with p:
        if _image_button("sa_image_promo","Promotional copy ideas","Open a sample promotional copy pack"):
            st.session_state["sa_bonus_panel"]="promo"
        _caption("Promo Studio")
    if st.session_state.get("sa_bonus_panel") in ("messages","promo"):
        render_town_bonus_panel(st.session_state["sa_bonus_panel"])
    _model_link(JORDAN,"Talk to Jordan about listings or marketing →")


def operations(c, data):
    _top("Taylor's workspace", "Orders & Suppliers", "Organize the practical work: purchase orders, sourcing, delivery planning and tasks.")
    a,b=st.columns(2)
    with a:
        if _image_button("sa_image_packing","Create example purchase order","Generate the sample PO in Taylor's workspace"):
            c["workspaces"][TAYLOR]["generated_po"] = c["generate_supplier_po"](c["workspaces"][TAYLOR])
            c["add_xp"](50)
            st.success("Sample purchase order created. +50 XP")
        _caption("Packing Orders · sample PO")
    with b:
        if _image_button("sa_image_supplier","Supplier Hub","Open sample supplier comparison"):
            st.session_state["sa_bonus_panel"]="supplier"
        _caption("Supplier Hub")
    if c["workspaces"][TAYLOR].get("generated_po"):
        po=c["workspaces"][TAYLOR]["generated_po"]
        with st.expander("Current purchase order",expanded=True): st.markdown(po)
        st.download_button("Download purchase order",po,file_name="purchase_order.txt",mime="text/plain")
    if st.session_state.get("sa_bonus_panel")=="supplier": render_town_bonus_panel("supplier")
    st.markdown("### ✅ Your seller tasks")
    todos=c["db_load_todos"]()
    done=0
    for item in todos:
        check=st.checkbox(item["task"],value=item["done"],key=f"sa_v20_task_{item['id']}")
        if check!=item["done"]:
            c["db_save_todo_status"](item["id"],check)
            if check: c["add_xp"](50)
            st.rerun()
        done+=int(check)
    st.progress(done/max(1,len(todos)),text=f"{done} of {len(todos)} tasks complete")
    with st.form("sa_v20_new_task",clear_on_submit=True):
        txt=st.text_input("Add a seller task",placeholder="Prepare weekend orders")
        if st.form_submit_button("Add task",use_container_width=True) and txt.strip():
            c["db_add_todo"](txt.strip()); st.rerun()
    _model_link(TAYLOR,"Ask Taylor to plan my next steps →")


def finance(c, data):
    _top("Alex's workspace", "Finance Desk", "The full picture lives here: budgets, what-if planning, financial charts, exports and reporting.")
    if _image_button("sa_image_finance","Finance Desk — open analysis","Show a sample finance helper"):
        st.session_state["sa_bonus_panel"]="finance"
    _caption("Finance helper")
    if st.session_state.get("sa_bonus_panel")=="finance": render_town_bonus_panel("finance")
    with st.expander("Budgets and what-if prices", expanded=False):
        vals=st.session_state["dash_budgets"]
        x,y,z=st.columns(3)
        new_vals={}
        with x: new_vals["daily"]=st.number_input("Daily budget ($)",min_value=10.0,value=float(vals["daily"]),step=50.0,key="sa_v20_budget_daily")
        with y: new_vals["monthly"]=st.number_input("Monthly budget ($)",min_value=100.0,value=float(vals["monthly"]),step=500.0,key="sa_v20_budget_monthly")
        with z: new_vals["annual"]=st.number_input("Annual budget ($)",min_value=1000.0,value=float(vals["annual"]),step=5000.0,key="sa_v20_budget_annual")
        for k,v in new_vals.items():
            if vals[k]!=v:
                vals[k]=v; c["db_save_budget"](k,v)
        adj=st.slider("What-if selling-price adjustment (%)",min_value=-20,max_value=30,value=int(st.session_state.get("sa_price_adjust",0)),step=5,key="sa_v20_price_adj")
        st.session_state["sa_price_adjust"] = adj
        st.caption("What-if adjustments are hypothetical estimates, not measured sales.")
    data=shop_data(c)
    _metrics(data,c)
    c["render_dashboard_charts"](data.periods,[v*c["fx_rate"] for v in data.sales],
        [v*c["fx_rate"] for v in data.profit],st.session_state["dash_budgets"]["daily"]*c["fx_rate"],
        data.sku_labels,data.sku_stock,data.sku_sales,c["fx_sym"])
    st.markdown("### Financial exports")
    report=c["generate_schedule_c_pl"](data.inventory_csv,c["active_fee_rate"])
    with st.expander("Illustrative P&L summary (review tax assumptions)"):
        st.markdown(report)
    st.download_button("Download P&L example",report,file_name="illustrative_pl.txt",mime="text/plain")
    _model_link(ALEX,"Ask Alex about profit or budgeting →")


def shop_upload(c, data):
    _top("Your shop's numbers", "Shop Data", "Upload once. Use your records across overview, charts and all four AI specialist rooms during this session.")
    st.info("Choose a financial CSV (Day, Sales, Profit) or an inventory CSV with retail_price_usd and weekly_units_sold. Files remain in this Streamlit session; uploaded data is sent to a configured AI provider if you explicitly reference it in chat.")
    file=st.file_uploader("Upload your shop CSV",type=["csv"],key="sa_v20_uploader")
    if file is not None:
        raw=file.getvalue().decode("utf-8-sig",errors="replace")
        try:
            rows=_records(raw)
            if not rows: raise ValueError("CSV has no data rows.")
            keys={str(k).strip().lower() for k in rows[0] if k}
            kind="inventory" if {"retail_price_usd","weekly_units_sold"}.issubset(keys) else "financial" if {"sales","profit"}.issubset(keys) else ""
            if not kind: raise ValueError("Expected financial columns Sales + Profit or inventory columns retail_price_usd + weekly_units_sold.")
            if raw != st.session_state.get("sa_shared_csv",""):
                st.session_state["sa_shared_csv"] = raw
                st.session_state["sa_shared_kind"] = kind
                for ws in c["workspaces"].values():
                    ws["file_text"] = raw
                st.success(f"Synced {len(rows)} {kind} rows across the shop session.")
        except Exception as exc:
            st.error(f"Could not accept CSV: {exc}")
    current=st.session_state.get("sa_shared_csv","")
    if current:
        st.success(f"Active upload: {st.session_state.get('sa_shared_kind','CSV')} data")
        st.dataframe(_records(current)[:30],hide_index=True,use_container_width=True)
        if st.button("Return to sample data",key="sa_reset_upload"):
            for ws in c["workspaces"].values():
                if ws.get("file_text") == current:
                    ws["file_text"] = ""
            st.session_state["sa_shared_csv"] = ""
            st.session_state["sa_shared_kind"] = ""
            st.rerun()
    else:
        st.caption("No upload yet. The overview and tools show clearly labeled sample values.")
    a,b=st.columns(2)
    with a:
        st.download_button("Download sample financial CSV",c["SAMPLE_DASHBOARD_CSV"],file_name="sample_financial_metrics.csv",mime="text/csv",use_container_width=True)
    with b:
        st.download_button("Download sample inventory CSV",c["SAMPLE_SELLER_CSV"],file_name="sample_seller_inventory.csv",mime="text/csv",use_container_width=True)
    if st.button("View my overview →",key="sa_data_home"): go(HOME)


def settings(c, data):
    _top("Your workspace", "Shop Settings", "Customize how you work. Currency and marketplace fee preferences are available under Preferences in the sidebar.")
    if _image_button("sa_image_settings","Shop Settings", "Open the setting ideas and customization plan"):
        st.session_state["sa_bonus_panel"]="settings"
    _caption("Shop preferences")
    if st.session_state.get("sa_bonus_panel")=="settings": render_town_bonus_panel("settings")
    st.markdown("### System information")
    st.caption("Stored demo budgets and tasks currently use the app's existing SQLite behavior. On an ephemeral Render filesystem, those records may reset after restart or redeploy.")
    telemetry=st.session_state.get("telemetry",{})
    st.write({"AI calls this session":telemetry.get("calls",0),"Last AI latency (ms)":telemetry.get("last_latency_ms",0),"Session errors":telemetry.get("errors",0)})



def explore_mode():
    """Free-roam 2D town. Local in-session avatar and building routing."""
    from town_game import explore_town

    _top("Playful navigation · optional", "Explore Seller Assist Town",
         "Choose your mini character, wander through town, and step inside a building to open its real workspace.")

    st.session_state.setdefault("sa_avatar_type", "Bunny")
    st.session_state.setdefault("sa_avatar_outfit", "#FFB5D0")
    st.session_state.setdefault("sa_avatar_nickname", "Shopkeeper")
    st.session_state.setdefault("sa_avatar_position", {"x": 50, "y": 63})
    st.session_state.setdefault("sa_town_last_event", "")

    with st.expander("🎀 Customize my mini avatar", expanded=False):
        kind_col, color_col, nick_col = st.columns([1, 1, 2])
        with kind_col:
            st.selectbox("Character", ["Bunny", "Frog", "Kitty", "Bear"], key="sa_avatar_type")
        with color_col:
            st.color_picker("Outfit color", key="sa_avatar_outfit")
        with nick_col:
            st.text_input("Character name", key="sa_avatar_nickname", max_chars=18)
        st.caption("Customization and location are retained during your current Streamlit session; they are not account-wide permanent saves.")

    event = explore_town(
        kind=st.session_state["sa_avatar_type"],
        outfit=st.session_state["sa_avatar_outfit"],
        nickname=st.session_state["sa_avatar_nickname"],
        position=st.session_state["sa_avatar_position"],
    )
    if isinstance(event, dict) and event.get("id") != st.session_state["sa_town_last_event"]:
        st.session_state["sa_town_last_event"] = event.get("id")
        pos = event.get("pos", {})
        if isinstance(pos, dict):
            try:
                x = max(3.0, min(97.0, float(pos.get("x", 50))))
                y = max(7.0, min(94.0, float(pos.get("y", 63))))
                st.session_state["sa_avatar_position"] = {"x": x, "y": y}
            except (ValueError, TypeError):
                pass
        if event.get("event") == "enter":
            mapping = {
                "home": HOME, "inventory": INVENTORY, "listings": LISTINGS,
                "operations": OPERATIONS, "finance": FINANCE, "data": DATA,
                "team": TEAM, "settings": SETTINGS,
            }
            target = mapping.get(event.get("page"))
            if target:
                go(target)
        elif event.get("event") == "save":
            st.success("Your avatar's position was saved for this session.")

    st.caption("Movement: click the map, use WASD/arrow keys after focusing the town, or use the touch pad. Select a glowing entrance and choose Enter building.")
    with st.expander("Direct navigation (accessible fallback)", expanded=False):
        choices = [HOME, INVENTORY, LISTINGS, OPERATIONS, FINANCE, DATA, TEAM, SETTINGS]
        target = st.selectbox("Choose a building", choices, key="sa_town_fallback_destination")
        if st.button("Open selected workspace", key="sa_town_fallback_open", use_container_width=True):
            go(target)


def render_page(page: str, context: dict[str, Any]):
    inject_illustrated_button_styles()
    _styles()
    st.session_state.setdefault("sa_shared_csv","")
    st.session_state.setdefault("sa_shared_kind","")
    st.session_state.setdefault("sa_bonus_panel","")
    st.session_state.setdefault("sa_price_adjust",0)
    data=shop_data(context)
    if page==HOME: home(context,data)
    elif page==EXPLORE: explore_mode()
    elif page==INVENTORY: inventory(context,data)
    elif page==LISTINGS: listings(context,data)
    elif page==OPERATIONS: operations(context,data)
    elif page==FINANCE: finance(context,data)
    elif page==DATA: shop_upload(context,data)
    elif page==SETTINGS: settings(context,data)
    else: st.error("Unknown page. Please choose a destination from the left menu.")
