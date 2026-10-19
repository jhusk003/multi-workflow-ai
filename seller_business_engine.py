"""Seller Assist v22 — deterministic business calculations, standard-library only.

No TabPFN model, trademark database, tax filing, or live integration is implied.
All quantities are estimates based on supplied inventory CSV and explicit assumptions.
"""
from __future__ import annotations

import csv
import io
import math
import re
from datetime import datetime, timedelta

REQUIRED = {"sku", "product_name", "unit_cost_usd", "retail_price_usd", "stock_on_hand", "weekly_units_sold", "supplier_lead_days"}
WATCHLIST = {"disney", "sanrio", "hello kitty", "velcro", "onesie", "tupperware", "stanley"}


def _f(value: str, column: str, index: int) -> float:
    try:
        n = float(str(value or "0").strip())
    except (ValueError, TypeError) as e:
        raise ValueError(f"Row {index}: {column} must be numeric.") from e
    if not math.isfinite(n):
        raise ValueError(f"Row {index}: {column} must be finite.")
    return n


def parse_inventory(csv_text: str) -> list[dict]:
    if not isinstance(csv_text, str) or not csv_text.strip():
        raise ValueError("Upload a nonempty inventory CSV in Settings & Data.")
    reader = csv.DictReader(io.StringIO(csv_text.lstrip('\ufeff')))
    if not reader.fieldnames:
        raise ValueError("The CSV needs a header row.")
    h = {str(k).strip().lower(): k for k in reader.fieldnames if k}
    missing = REQUIRED - h.keys()
    if missing:
        raise ValueError("Missing inventory columns: " + ", ".join(sorted(missing)))
    items = []
    seen = set()
    for number, row in enumerate(reader, 2):
        if not row or not any(str(x or "").strip() for x in row.values()):
            continue
        if None in row:
            raise ValueError(f"Row {number} has more fields than its header.")
        sku = str(row.get(h["sku"]) or "").strip()
        if not sku or sku in seen:
            raise ValueError(f"Row {number}: SKU must be unique and nonempty.")
        seen.add(sku)
        name = str(row.get(h["product_name"]) or "").strip()
        if not name:
            raise ValueError(f"Row {number}: product_name cannot be empty.")
        item = {
            "sku": sku, "name": name,
            "category": str(row.get(h.get("category", "")) or "General").strip(),
            "cost": _f(row.get(h["unit_cost_usd"]), "unit_cost_usd", number),
            "price": _f(row.get(h["retail_price_usd"]), "retail_price_usd", number),
            "stock": _f(row.get(h["stock_on_hand"]), "stock_on_hand", number),
            "weekly": _f(row.get(h["weekly_units_sold"]), "weekly_units_sold", number),
            "lead": _f(row.get(h["supplier_lead_days"]), "supplier_lead_days", number),
            "returns": _f(row.get(h.get("return_rate_pct", ""), "0"), "return_rate_pct", number),
        }
        if min(item[k] for k in ("cost", "price", "stock", "weekly", "lead")) < 0:
            raise ValueError(f"Row {number}: costs, prices, quantities and lead time cannot be negative.")
        if item['returns'] < 0 or item['returns'] > 100:
            raise ValueError(f"Row {number}: return_rate_pct must be 0–100.")
        items.append(item)
    if not items:
        raise ValueError("No inventory rows found.")
    return items


def stock_plan(item: dict, setup_cost=18.0, annual_holding_fraction=.22, safety_days=4):
    velocity = item['weekly'] / 7.0
    annual = item['weekly'] * 52
    hold = max(.75, item['cost'] * annual_holding_fraction)
    eoq = math.ceil(math.sqrt(2 * annual * setup_cost / hold)) if annual else 0
    safety = math.ceil(velocity * safety_days)
    reorder_point = math.ceil(velocity * item['lead'] + safety)
    days_left = item['stock'] / velocity if velocity else None
    needs_order = item['stock'] <= reorder_point and item['weekly'] > 0
    quantity = max(eoq, math.ceil(max(0, reorder_point - item['stock']))) if needs_order else 0
    return {"eoq": eoq, "rop": reorder_point, "safety": safety,
            "days_left": days_left, "needs_order": needs_order, "order_qty": quantity,
            "estimated_cost": quantity * item['cost']}


def inventory_report(csv_text: str, fee_rate=.095) -> str:
    items = parse_inventory(csv_text)
    rows, urgent = [], []
    for item in items:
        s = stock_plan(item)
        days = f"{s['days_left']:.1f}d" if s['days_left'] is not None else 'No current sales'
        status = '🔴 Restock' if s['needs_order'] else '✅ Monitor'
        rows.append(f"| `{item['sku']}` | {item['name'].replace('|','/')[:25]} | {item['stock']:g} | {days} | {s['rop']} | {s['eoq']} | {s['order_qty']} | {status} |")
        if s['needs_order']:
            urgent.append(f"- `{item['sku']}`: order about **{s['order_qty']}** units (estimated purchase cost **${s['estimated_cost']:,.2f}**).")
    unit_contribution = sum((i['price'] * (1-fee_rate) - i['cost']) * i['weekly'] for i in items)
    return ("### Inventory planning — Wilson EOQ + reorder point\n"
            f"Estimated weekly contribution before other expenses: **${unit_contribution:,.2f}**.\n\n"
            "| SKU | Product | In stock | Days left | ROP | EOQ | Suggested order | Status |\n"
            "|---|---|---:|---:|---:|---:|---:|---|\n" + "\n".join(rows) +
            "\n\n**Restock suggestions**\n" + ("\n".join(urgent) if urgent else "No items currently below their reorder point.") +
            "\n\n*Assumptions: $18 order/setup cost, 22% annual holding fraction (minimum $0.75 per unit), four days of safety stock, stable weekly demand. EOQ is a mathematical estimate, not a TabPFN prediction.*")


def purchase_order(csv_text: str, *, now=None) -> tuple[str, list[str]]:
    items = parse_inventory(csv_text)
    now = now or datetime.now()
    poid = 'DRAFT-' + now.strftime('%Y%m%d-%H%M%S')
    lines, tasks, total = [], [], 0.0
    for item in items:
        p = stock_plan(item)
        if not p['needs_order']:
            continue
        amount = p['estimated_cost']
        total += amount
        eta = (now + timedelta(days=item['lead'])).date().isoformat()
        lines.append(f"| `{item['sku']}` | {item['name'].replace('|','/')[:27]} | {p['order_qty']} | ${item['cost']:,.2f} | ${amount:,.2f} | {eta} |")
        tasks.append(f"Review draft restock for {item['sku']} — {p['order_qty']} units (estimated ${amount:,.2f})")
    if not lines:
        return "### Purchase order draft\nNo SKUs currently meet the reorder-point threshold. No order generated.", []
    report = (f"### Itemized purchase order draft `{poid}`\n"
              "For review only; vendor, payment terms, and shipping charges are not confirmed.\n\n"
              "| SKU | Product | Qty | Unit cost | Est. line cost | ETA if ordered today |\n"
              "|---|---|---:|---:|---:|---|\n" + '\n'.join(lines) +
              f"\n\n**Estimated merchandise total: ${total:,.2f}.** Shipping/tax excluded.")
    return report, tasks


def _tags(item: dict) -> list[str]:
    terms = re.findall(r'[a-zA-Z]+', item['name'].lower())
    seed = next((s for s in terms if len(s)>=4), 'handmade')
    category = re.sub(r'[^a-z0-9 ]+', '', item['category'].lower()).strip()[:12] or 'artisan'
    raw = [f'{seed} gift',f'handmade {seed}',f'{category} item', 'small shop gift', 'artisan made',
           'gift idea', 'custom style', 'thoughtful gift', 'modern decor', 'unique present',
           'gift for friend','everyday favorite','shop collection']
    # For CSV convenience: 13 candidate tags, all <= 20 characters. NOT verified trends/compliance.
    return [s[:20] for s in raw]


def bulk_listing_csv(csv_text: str) -> tuple[str, list[str]]:
    items = parse_inventory(csv_text)
    out = io.StringIO(newline='')
    w = csv.writer(out)
    w.writerow(['SKU','Handle','Title','Description_Draft','Category','Price_USD','Inventory','Etsy_Tag_Ideas_13','Review_Notes'])
    warnings = []
    for i in items:
        slug = re.sub(r'[^a-z0-9]+','-',i['name'].lower()).strip('-') + '-' + re.sub(r'[^a-z0-9]+','-',i['sku'].lower()).strip('-')
        found = [s for s in WATCHLIST if re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',i['name'].lower())]
        note = ('Review brand/IP use: '+', '.join(sorted(found))) if found else 'Review description and marketplace import schema'
        if found:
            warnings.append(f"`{i['sku']}` contains potential brand terms: {', '.join(sorted(found))}. Check context; this is NOT a trademark clearance result.")
        w.writerow([i['sku'],slug,i['name'],f"Draft: {i['name']} — {i['category']}. Verify materials, sizes and claims before publishing.",
                   i['category'],f"{i['price']:.2f}",int(i['stock']), ', '.join(_tags(i)),note])
    return out.getvalue(), warnings


def estimate_pl(csv_text: str, fee_rate=.095) -> str:
    items = parse_inventory(csv_text)
    if not 0 <= fee_rate <= 1:
        raise ValueError('Fee rate must be between 0 and 1.')
    gross = sum(i['price']*i['weekly'] for i in items)
    returns = sum(i['price']*i['weekly']*i['returns']/100 for i in items)
    cogs = sum(i['cost']*i['weekly'] for i in items)   # simplified units sold, not inventory valuation
    fees = gross*fee_rate
    net = gross-returns-cogs-fees
    return ("### Estimated product-level P&L (weekly)\n"
            "Uses item-level costs and expected returns from the uploaded CSV. **Not a completed tax return.**\n\n"
            f"- Gross sales before expected returns: **${gross:,.2f}**\n"
            f"- Expected returns/allowances (CSV percentages): **−${returns:,.2f}**\n"
            f"- Cost estimate (unit cost × weekly units): **−${cogs:,.2f}**\n"
            f"- Percentage-based marketplace fee estimate ({fee_rate*100:.2f}%): **−${fees:,.2f}**\n"
            f"- **Estimated contribution: ${net:,.2f} per week**\n\n"
            "*Excludes shipping, ads, fixed transaction fees, payroll, tax, overhead, inventory adjustments and other expenses. Sales-tax nexus and quarterly tax cannot be determined from this data alone.*")


def answer_from_shop_data(question: str, csv_text: str, fee_rate=.095) -> str:
    items = parse_inventory(csv_text)
    q = question.lower()
    enriched = [(i,stock_plan(i)) for i in items]
    if any(x in q for x in ('low stock','stockout','restock','urgent','run out','reorder')):
        ranked = sorted(enriched, key=lambda t: t[1]['days_left'] if t[1]['days_left'] is not None else float('inf'))
        lines = [f"- `{i['sku']}` {i['name']}: {p['days_left']:.1f} days remaining; suggested order {p['order_qty']} units." for i,p in ranked if p['days_left'] is not None]
        return '### Stockout risk (current sales pace)\n' + ('\n'.join(lines) if lines else 'No sell-through data available.')
    if any(x in q for x in ('profit','margin','best seller','best product')):
        ranked=sorted(items,key=lambda i: (i['price']*(1-fee_rate)-i['cost'])*i['weekly'],reverse=True)
        return '### Estimated weekly product contribution\n'+'\n'.join(f"- `{i['sku']}` {i['name']}: ${(i['price']*(1-fee_rate)-i['cost'])*i['weekly']:,.2f}" for i in ranked)
    if any(x in q for x in ('revenue','sales','gross')):
        return f"**Estimated gross weekly sales:** ${sum(i['price']*i['weekly'] for i in items):,.2f} across {len(items)} SKUs (from uploaded unit/velocity assumptions)."
    m = next((i for i in items if i['sku'].lower() in q or i['name'].lower() in q),None)
    if m:
        p=stock_plan(m)
        return f"`{m['sku']}` {m['name']}: {m['stock']:g} units, {m['weekly']:g} sold/week, ${m['price']:.2f} retail, ${m['cost']:.2f} cost, EOQ {p['eoq']}, reorder point {p['rop']}."
    return ('I can calculate **stockout risk**, **profit contribution**, or **gross sales**, or summarize a specific SKU. '
            'This is a deterministic CSV calculator rather than an unrestricted AI model.')
