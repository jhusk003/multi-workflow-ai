# SELLER ASSIST OPEN-WEIGHT GEMMA + REAL TABPFN v28
# SELLER ASSIST FINANCE READABILITY v27
# SELLER ASSIST SHARED BRAINS v23
"""Seller Assist v20: short Home plus dedicated business-workflow pages.

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
from seller_finance_readability_v27 import apply_finance_readability as _sa_apply_finance_readability

from seller_business_engine import answer_from_shop_data as sa_answer_shop, parse_inventory as sa_parse_inventory
from seller_ai_workflows import workflow_panel as sa_workflow, brand_settings as sa_brand_settings, inventory_reference as sa_inventory_reference
from illustrated_buttons import (
    inject_illustrated_button_styles,
    render_illustrated_town_hero,
    render_town_bonus_panel,
)

HOME = "🏡 Home"
INVENTORY = "📦 Inventory Lab"
LISTINGS = "🎨 Listings & Marketing"
OPERATIONS = "🚚 Orders & Suppliers"
FINANCE = "💰 Finance Desk"
DATA = "📁 Shop Data"
TEAM = "🤖 AI Team"
SETTINGS = "⚙️ Settings & Data"
PAGES = [HOME, INVENTORY, LISTINGS, OPERATIONS, FINANCE, TEAM, SETTINGS]

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
    .sa-v20-header{background:linear-gradient(135deg,#7d6aac,#907ec0 58%,#b18dc7);border:1px solid rgba(255,255,255,.12);
      border-radius:24px;padding:22px 27px;margin:.1rem 0 1rem;box-shadow:0 12px 24px rgba(32,20,64,.14)}
    .sa-v20-header h1{font:700 clamp(1.7rem,3vw,2.5rem) Fredoka,sans-serif;color:#fff;margin:.25rem 0}
    .sa-v20-header p{color:#f5f2ff;font-size:.96rem;margin:0}
    .sa-v20-eyebrow{font:800 .72rem 'Nunito Sans',sans-serif;color:#fff7d7;letter-spacing:.12em;text-transform:uppercase}
    .sa-v20-title{font:700 1.3rem Fredoka,sans-serif;margin:14px 0 6px;color:#ffffff}
    .sa-v20-panel{background:#fff;border:1px solid #e9def4;border-radius:17px;padding:14px 16px;margin:12px 0}
    .sa-town-hero{min-height:275px!important;background-position:center 51%!important;margin-top:0!important}
    .sa-town-hero h1{font-size:clamp(1.55rem,3vw,2.4rem)!important}
    .sa-town-hero .sa-town-overlay{padding:20px 24px!important}
    .sa-town-hero .sa-town-badges{display:none!important}
    @media (max-width:720px){.sa-town-hero{min-height:255px!important}.sa-v20-header{padding:17px}}
    </style>""", unsafe_allow_html=True)


def _home_quick(c, data):
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
    if st.button("Meet your talking AI specialists →", key="sa_home_team",use_container_width=True): go(TEAM)


def inventory(c, data):
    _top("Morgan's workspace", "Inventory Lab", "Upload inventory under Settings & Data, review stock and create an explanatory restock estimate.")
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
    # SELLER ASSIST BUSINESS ENGINE v22 — deterministic uploaded-SKU Q&A.
    with st.expander("Ask my inventory data (calculated from the CSV)", expanded=False):
        question = st.text_input("Ask about stockout risk, gross sales, a SKU, or profit", key="sa_v22_inventory_question")
        if st.button("Analyze my CSV", key="sa_v22_inventory_ask") and question.strip():
            try:
                st.markdown(sa_answer_shop(question.strip(), data.inventory_csv, c["active_fee_rate"]))
            except ValueError as error:
                st.error(f"Invalid inventory CSV: {error}")
    # SELLER ASSIST TRUE TABPFN INTEGRATION v28 — separate from Wilson EOQ.
    with st.expander('🔮 Actual TabPFN prediction (optional historical-data model)', expanded=False):
        from seller_tabpfn_v28 import HISTORY_TEMPLATE, predict as _sa_tabpfn_predict, ForecastInputError
        st.caption('The existing inventory analysis above uses Wilson EOQ, not TabPFN. To use the REAL Prior Labs model, provide a labeled historical weekly-sales CSV (12+ observations across 3+ weeks) and your own uploaded current inventory CSV.')
        st.download_button('Download blank historical CSV template', HISTORY_TEMPLATE,
            file_name='tabpfn_historical_weekly_template.csv', mime='text/csv',key='sa_tabpfn_template_v28')
        history_file=st.file_uploader('Historical weekly sales CSV',type=['csv'],key='sa_tabpfn_history_v28')
        import hashlib
        digest=hashlib.sha256(data.inventory_csv.encode('utf-8')).hexdigest()
        if st.session_state.get('sa_tabpfn_source_sha_v28') not in (None,digest):
            st.session_state['sa_tabpfn_last_report_v28']=''  # Prevent applying outdated predictions to a new file.
        has_token=bool(c['secret']('TABPFN_TOKEN'))
        st.caption('Prior Labs key: ' + ('Configured' if has_token else 'Not configured — use TABPFN_TOKEN in Render Environment.'))
        model_choice=st.selectbox('TabPFN model request',['v3.5_default','default'],key='sa_tabpfn_model_v28',
            help='3.5 requires Prior Labs access. Server default is still real model inference, but must not be claimed as 3.5 unless confirmed.')
        consent=st.checkbox('I confirm I have permission to send this historical data to Prior Labs for hosted inference.',key='sa_tabpfn_consent_v28')
        if st.button('Run genuine TabPFN regression',key='sa_tabpfn_run_v28',disabled=not (history_file and consent and has_token),use_container_width=True):
            if data.source == 'Sample data' or st.session_state.get('sa_shared_kind') != 'inventory':
                st.warning('Upload your own CURRENT inventory CSV under Settings & Data first. Predictions are not run against built-in showcase data.')
            else:
                try:
                    history_text=history_file.getvalue().decode('utf-8-sig')
                    with st.spinner('Running the actual Prior Labs model on your historical data…'):
                        report=_sa_tabpfn_predict(history_text, data.inventory_csv, token=c['secret']('TABPFN_TOKEN'), model_path=model_choice)
                    st.session_state['sa_tabpfn_source_sha_v28']=digest
                    st.session_state['sa_tabpfn_last_report_v28']=report
                    c['workspaces'][MORGAN]['tabpfn_report']=report
                    st.success('Real TabPFN inference returned and was saved for Morgan. Review its assumptions below.')
                except (ForecastInputError,UnicodeDecodeError) as error:
                    st.error(str(error))
        forecast=st.session_state.get('sa_tabpfn_last_report_v28','')
        if forecast:
            st.markdown(forecast)
            st.download_button('Download TabPFN forecast',forecast,
                file_name='tabpfn_historical_forecast.md',mime='text/markdown',key='sa_tabpfn_export_v28')

    st.markdown("### 🐰 Morgan’s AI inventory planner")
    source, source_label = sa_inventory_reference(c,data)
    st.caption(source_label)
    sa_workflow('morgan_stock',MORGAN,'inventory',c,reference=source + '\n\nMost recent TabPFN model report (if any):\n' + st.session_state.get('sa_tabpfn_last_report_v28',''),
                label='Interpret my stock and suggest next steps',
                default_instruction='Using my data, prioritize urgent stock and recommend realistic actions. State assumptions.')
    _model_link(MORGAN,"Continue with Morgan →")
    if st.button("Upload / replace shop CSV",key="sa_inventory_upload",use_container_width=True):
        st.session_state["sa_settings_section_request"] = "📁 Data & Uploads"
        go(SETTINGS)


def listings(c, data):
    _top("Jordan’s creative workspace", "Listings & Marketing", "Create original editable drafts using Jordan’s AI brain and your uploaded product sheet.")
    src,label=sa_inventory_reference(c,data)
    st.caption('Product context: '+label)
    opts=['🏷️ AI Listing','📣 Campaign Ideas','💌 Customer Messages','🐝 Research']
    choice=st.radio('Select a creative tool',opts,horizontal=True,key='sa_v23_jordan_tool')
    if choice==opts[0]:
        left,right=st.columns([1,1.3])
        with left:
            if _image_button('sa_image_listing','Bulk listing CSV draft','Generate an itemized planning CSV from the uploaded SKU sheet'):
                c['workspaces'][JORDAN]['exported_listing_csv']=c['generate_shopify_etsy_listing_csv'](src)
            _caption('Bulk planning CSV — deterministic, editable after download')
            out=c['workspaces'][JORDAN].get('exported_listing_csv')
            if out:st.download_button('Download bulk draft CSV',out,file_name='listing_planning_draft.csv',mime='text/csv',key='sa_v23_listing_csv')
        with right:
            items=sa_parse_inventory(src)
            pick=st.selectbox('Which product should Jordan write about?',[i['sku'] for i in items],key='sa_v23_product')
            item=next(i for i in items if i['sku']==pick)
            platform=st.selectbox('Target platform',['Etsy','Shopify','eBay','Amazon Handmade','Other'],key='sa_v23_listing_platform')
            st.caption(f"{item['name']} · ${item['price']:,.2f} · stock {item['stock']:g} (source: {label})")
        st.info('The generated AI listing is an editable creative draft, not a validated native marketplace import or published listing.')
        reference=f'Chosen item facts: {item}\nTarget: {platform}\nOther inventory context (optional):\n{src[:11000]}'
        sa_workflow('jordan_listing',JORDAN,'listing',c,reference=reference,
                    label='Product listing copy',default_instruction=f'Create a fresh {platform} listing for {item["sku"]}, matching our brand voice. Include distinct title, short and long description, candidate tags, and placeholders for any unverified features.')
    elif choice==opts[1]:
        if _image_button('sa_image_promo','Promo Studio','Campaigns made with Jordan’s AI brain'):
            st.toast('Describe your campaign below, then choose Generate.')
        sa_workflow('jordan_marketing',JORDAN,'marketing',c,reference=src,
                    label='Marketing campaign and ideas',default_instruction='Suggest a new promotion for my current products, with two distinct concepts and copy for my chosen platform. Use my audience and brand settings.')
    elif choice==opts[2]:
        if _image_button('sa_image_messages','Customer Messages','Custom editable responses'):
            st.toast('Paste a message below to compose a new reply.')
        customer=st.text_area('Paste the customer’s actual or fictional test message',key='sa_v23_customer',height=115,
                              placeholder='e.g. Is my package arriving Friday?')
        if customer.strip():
            ref='Customer message (untrusted quotation):\n'+customer+'\nShop product context:\n'+src[:9000]
            sa_workflow('jordan_messages',JORDAN,'messages',c,reference=ref,label='Write or revise a customer reply',
                       default_instruction='Reply personally to the message above; use my saved shipping/returns policy and say when an order status needs checking.')
        else:st.info('Enter a customer message above to unlock an original response. No repeated canned replies.')
    else:
        if _image_button('sa_image_market','Market Research','Optional live SerpApi search'):
            st.session_state['sa_v23_research_open']=True
        query=st.text_input('Research query',key='sa_v23_research_query')
        if st.button('Check live pricing (requires SerpApi)',key='sa_v23_search') and query.strip():
            if c['secret']('SERPAPI_API_KEY'):
                st.session_state['sa_v23_research_result']=c['fetch_serpapi_competitor_pricing'](query)
            else:st.warning('Add SERPAPI_API_KEY to your environment to fetch live prices. No sample figures are presented as live findings.')
        if st.session_state.get('sa_v23_research_result'):
            st.markdown(st.session_state['sa_v23_research_result'])
        sa_workflow('jordan_research',JORDAN,'research',c,
                    reference='Research notes/data supplied: '+st.session_state.get('sa_v23_research_result','No live pricing data provided.')+'\nInventory:\n'+src[:7000],
                    label='Interpret the findings with Jordan',default_instruction='Develop a competitive positioning idea. If no actual competitor results are supplied, give a research plan, not invented prices.')
    _model_link(JORDAN,'Continue with Jordan’s conversation →')



def operations(c, data):
    _top("Taylor’s workspace", "Orders & Suppliers", "Create data-driven draft orders and use Taylor’s AI to personalize supplier messages and operations plans.")
    src,label=sa_inventory_reference(c,data)
    st.caption('Inventory context: '+label)
    choices=['📦 Purchase Orders','✉️ Supplier AI','✅ Tasks']
    choice=st.radio('Operations tool',choices,horizontal=True,key='sa_v23_ops_tool')
    workspace=c['workspaces'][TAYLOR]
    if choice==choices[0]:
        if _image_button('sa_image_packing','Generate data-driven PO','Creates a draft using reorder-point estimates'):
            workspace['generated_po']=c['generate_supplier_po'](workspace)
        if workspace.get('generated_po'):
            po=workspace['generated_po']
            st.markdown(po)
            st.download_button('Download draft purchase order',po,file_name='draft_purchase_order.md',key='sa_v23_po_download')
            suggested=st.session_state.get('sa_latest_po_tasks',[])
            if suggested and st.button('Add suggested restocks to my tasks',key='sa_v23_tasks_from_po'):
                existing={t['task'] for t in c['db_load_todos']()}
                count=0
                for task in suggested:
                    if task not in existing:c['db_add_todo'](task);existing.add(task);count+=1
                st.success(f'Added {count} new task(s).')
        sa_workflow('taylor_plan',TAYLOR,'operations',c,
                    reference='Current inventory:\n'+src[:10000]+'\nLatest DRAFT purchase order:\n'+workspace.get('generated_po','Not generated'),
                    label='AI order and packing plan',default_instruction='Review my draft purchase order and produce a sensible packing, procurement or delivery coordination plan. Do not claim an order has been sent.')
    elif choice==choices[1]:
        if _image_button('sa_image_supplier','Supplier Hub','Personalized sourcing and communications'):
            st.toast('Provide supplier facts below, then generate a custom plan.')
        notes=st.text_area('Enter real or test supplier details / constraints',key='sa_v23_supplier_notes',height=110,
                           placeholder='e.g. Supplier A offers MOQ 50 and 12-day lead time; need delivery before a pop-up')
        sa_workflow('taylor_supplier',TAYLOR,'supplier',c,
                    reference='Inventory:\n'+src[:8500]+'\nSupplier details supplied by user:\n'+notes+'\nDraft PO:\n'+workspace.get('generated_po','Not generated'),
                    label='Supplier comparison or outreach',default_instruction='Prepare a supplier inquiry email with questions about availability, minimum quantities, shipping costs, and lead time; [VERIFY] details I did not provide.')
    else:
        st.markdown('### Shop tasks')
        todos=c['db_load_todos']()
        done=0
        for item in todos:
            checked=st.checkbox(item['task'],value=item['done'],key=f"sa_v23_task_{item['id']}")
            if checked!=item['done']:
                c['db_save_todo_status'](item['id'],checked)
                if checked:c['add_xp'](50)
                st.rerun()
            done+=int(checked)
        st.progress(done/max(len(todos),1),text=f'{done}/{len(todos)} complete')
        with st.form('sa_v23_task_form',clear_on_submit=True):
            task=st.text_input('Add task')
            if st.form_submit_button('Add task') and task.strip():c['db_add_todo'](task.strip());st.rerun()
    _model_link(TAYLOR,'Continue with Taylor’s conversation →')



def finance(c, data):
    _sa_apply_finance_readability()
    _top("Alex’s workspace", "Finance Desk", "Calculated estimates based on your inventory or uploaded finance sheet, followed by AI interpretation.")
    with st.expander('Budgets & hypothetical pricing',expanded=False):
        vals=st.session_state['dash_budgets']
        a,b,d=st.columns(3)
        with a:vals['daily']=st.number_input('Daily budget ($)',min_value=10.0,value=float(vals['daily']),key='sa_v23_budget_d')
        with b:vals['monthly']=st.number_input('Monthly budget ($)',min_value=100.0,value=float(vals['monthly']),key='sa_v23_budget_m')
        with d:vals['annual']=st.number_input('Annual budget ($)',min_value=1000.0,value=float(vals['annual']),key='sa_v23_budget_y')
        if st.button('Save budget settings',key='sa_v23_budget_save'):
            for k,v in vals.items():c['db_save_budget'](k,v)
        st.slider('Hypothetical selling price adjustment (%)',min_value=-20,max_value=30,step=5,key='sa_price_adjust')
    data=shop_data(c)
    _metrics(data,c)
    c['render_dashboard_charts'](data.periods,[v*c['fx_rate'] for v in data.sales],
         [v*c['fx_rate'] for v in data.profit],st.session_state['dash_budgets']['daily']*c['fx_rate'],
         data.sku_labels,data.sku_stock,data.sku_sales,c['fx_sym'])
    src,label=sa_inventory_reference(c,data)
    report=c['generate_schedule_c_pl'](src,c['active_fee_rate'])
    with st.expander('Estimated product-level P&L — educational, not tax filing',expanded=False):st.markdown(report)
    st.download_button('Download estimate',report,file_name='estimated_profit.md',key='sa_v23_pl_download')
    if st.session_state.get('sa_shared_kind')=='financial':
        financial=st.session_state.get('sa_shared_csv','')
        reference='User-uploaded financial data:\n'+financial[:12000]+'\nProduct estimate:\n'+report
    else:reference='Inventory source: '+label+'\n'+src[:10000]+'\nEstimated product-level P&L:\n'+report
    sa_workflow('alex_finance',ALEX,'finance',c,reference=reference,
                label='AI finance and scenario analysis',default_instruction='Explain the most important profit or cash-flow levers in my real uploaded data; distinguish estimates, note unknowns, propose two practical improvements.')
    _model_link(ALEX,'Continue with Alex’s conversation →')



def shop_upload(c, data):
    st.markdown("#### Upload, preview & manage shop data")
    st.caption("Upload once to share data across the overview and all four AI rooms in this session.")
    st.info("Upload a financial CSV or inventory CSV. Inventory calculations require SKU, product name, unit cost, retail price, stock, weekly sales and lead days. Session uploads may reset on restart; export a backup. Data enters an AI request only when explicitly referenced in chat.")
    file=st.file_uploader("Upload your shop CSV",type=["csv"],key="sa_v20_uploader")
    if file is not None:
        raw=file.getvalue().decode("utf-8-sig",errors="replace")
        try:
            rows=_records(raw)
            if not rows: raise ValueError("CSV has no data rows.")
            keys={str(k).strip().lower() for k in rows[0] if k}
            kind="inventory" if {"retail_price_usd","weekly_units_sold"}.issubset(keys) else "financial" if {"sales","profit"}.issubset(keys) else ""
            if not kind: raise ValueError("Expected financial columns Sales + Profit or inventory columns retail_price_usd + weekly_units_sold.")
            if kind == "inventory":
                sa_parse_inventory(raw)  # Validate before synchronizing any workspace.
            if raw != st.session_state.get("sa_shared_csv", ""):
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
        st.download_button("Back up active upload CSV", current, file_name="seller_assist_active_upload.csv", mime="text/csv", key="sa_v22_backup_upload")
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
    if st.button("View my overview →",key="sa_data_home"):
        st.session_state["sa_home_view_request"] = "quick"
        go(HOME)


def settings(c, data):
    # SELLER ASSIST SETTINGS DATA v21.2
    _top("Your workspace", "Settings & Data", "Manage shared shop data, review workspace settings, and download sample files in one place.")
    section_request = st.session_state.pop("sa_settings_section_request", None)
    if section_request in ("⚙️ Preferences & Status", "📁 Data & Uploads"):
        st.session_state["sa_settings_section_v21_2"] = section_request
    section = st.radio(
        "Settings section",
        ["⚙️ Preferences & Status", "📁 Data & Uploads"],
        horizontal=True,
        key="sa_settings_section_v21_2",
    )
    if section == "📁 Data & Uploads":
        shop_upload(c, data)
        return
    st.caption("Currency and marketplace fee preferences are available under Preferences in the sidebar.")
    if _image_button("sa_image_settings", "Shop Settings", "Open the setting ideas and customization plan"):
        st.session_state["sa_bonus_panel"] = "settings"
    _caption("Shop preferences")
    if st.session_state.get("sa_bonus_panel") == "settings":
        render_town_bonus_panel("settings")
    sa_brand_settings()
    st.markdown('### AI brain connection check')
    st.caption('Uses your existing Google API key; no Groq account is required. This tests the real provider, not a simulated result.')
    if st.button('Test primary Gemma AI',key='sa_gemma_health_v28'):
        from seller_character_brain import reply as _sa_health_reply, BrainUnavailable as _sa_health_error
        try:
            with st.spinner('Checking accessible Gemma models…'):
                result,provider=_sa_health_reply(MORGAN,c['ASSISTANTS'][MORGAN],{'messages':[]},
                    'Reply with one short sentence confirming that you can assist a small business.',
                    '',{},c['secret'],timeout=16)
            if 'Gemma open-weight' in provider:
                st.success('OPEN-WEIGHT AI VERIFIED: '+provider)
            else:
                st.warning('AI request succeeded, but open-weight Gemma did NOT run. Provider: '+provider)
            st.caption('Provider response: '+result[:400])
        except _sa_health_error as error:
            st.error(str(error))
    st.markdown("### System information")
    st.caption("Stored demo budgets and tasks currently use the app's existing SQLite behavior. On an ephemeral Render filesystem, those records may reset after restart or redeploy.")
    telemetry = st.session_state.get("telemetry", {})
    st.write({"AI calls this session": telemetry.get("calls", 0), "Last AI latency (ms)": telemetry.get("last_latency_ms", 0), "Session errors": telemetry.get("errors", 0)})



def explore_mode():
    """Free-roam 2D town. Local in-session avatar and building routing."""
    from town_game import explore_town

    st.caption("Wander around the town or tap a glowing entrance to open the matching shop tool.")

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
                "operations": OPERATIONS, "finance": FINANCE, "data": SETTINGS,
                "team": TEAM, "settings": SETTINGS,
            }
            target = mapping.get(event.get("page"))
            if event.get("page") == "home":
                st.session_state["sa_home_view_request"] = "quick"
            if event.get("page") == "data":
                st.session_state["sa_settings_section_request"] = "📁 Data & Uploads"
            elif event.get("page") == "settings":
                st.session_state["sa_settings_section_request"] = "⚙️ Preferences & Status"
            if target:
                go(target)
        elif event.get("event") == "save":
            st.success("Your avatar's position was saved for this session.")

    st.caption("Movement: click the map, use WASD/arrow keys after focusing the town, or use the touch pad. Select a glowing entrance and choose Enter building.")
    with st.expander("Direct navigation (accessible fallback)", expanded=False):
        choices = [HOME, INVENTORY, LISTINGS, OPERATIONS, FINANCE, TEAM, SETTINGS]
        target = st.selectbox("Choose a building", choices, key="sa_town_fallback_destination")
        if st.button("Open selected workspace", key="sa_town_fallback_open", use_container_width=True):
            go(target)


def home(c, data):
    # SELLER ASSIST EXPLORE ON HOME v21.1
    # The map and compact dashboard are alternative views, not one long page.
    _top("Your little business village", "Welcome to Seller Assist Town",
         "Explore the town with your mini avatar or jump straight into your shop tools.")
    if st.session_state.pop("sa_home_view_request", None) == "quick":
        st.session_state["sa_home_view_v21_1"] = "📊 Quick Dashboard"
    choice = st.radio(
        "Home view",
        ["🗺️ Explore Town", "📊 Quick Dashboard"],
        horizontal=True,
        key="sa_home_view_v21_1",
        label_visibility="collapsed",
    )
    if choice == "🗺️ Explore Town":
        explore_mode()
    else:
        _home_quick(c, data)

def render_page(page: str, context: dict[str, Any]):
    inject_illustrated_button_styles()
    _styles()
    st.session_state.setdefault("sa_shared_csv","")
    st.session_state.setdefault("sa_shared_kind","")
    st.session_state.setdefault("sa_bonus_panel","")
    st.session_state.setdefault("sa_price_adjust",0)
    data=shop_data(context)
    if page==HOME: home(context,data)
    elif page==INVENTORY: inventory(context,data)
    elif page==LISTINGS: listings(context,data)
    elif page==OPERATIONS: operations(context,data)
    elif page==FINANCE: finance(context,data)
    elif page==SETTINGS: settings(context,data)
    else: st.error("Unknown page. Please choose a destination from the left menu.")
