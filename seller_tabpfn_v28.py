"""Real, opt-in Prior Labs TabPFN API regression. Never relabel Wilson EOQ as inference.

TabPFN needs a labeled HISTORY file, not just a current SKU snapshot. The CSV is
sent to Prior Labs only after a user clicks Run with TABPFN_TOKEN configured.
"""
from __future__ import annotations
import csv
import io
import math
import os
from collections import defaultdict
from seller_business_engine import parse_inventory, stock_plan

HISTORY_COLUMNS = ('sku','week_index','unit_cost_usd','retail_price_usd',
                   'stock_on_hand','supplier_lead_days','return_rate_pct','weekly_units_sold')
HISTORY_TEMPLATE = ','.join(HISTORY_COLUMNS) + '\n'

class ForecastInputError(ValueError):
    pass


def _history(text):
    reader = csv.DictReader(io.StringIO((text or '').lstrip('\ufeff')))
    if not reader.fieldnames:
        raise ForecastInputError('Upload a historical weekly-sales CSV with a header.')
    headers = {str(name).strip().lower(): name for name in reader.fieldnames if name}
    missing = set(HISTORY_COLUMNS) - set(headers)
    if missing:
        raise ForecastInputError('Historical CSV is missing: '+', '.join(sorted(missing)))
    results=[]
    seen=set()
    for line, row in enumerate(reader,2):
        if not row or not any(str(x or '').strip() for x in row.values()):
            continue
        if None in row:
            raise ForecastInputError(f'Historical row {line} has too many values.')
        sku = str(row.get(headers['sku']) or '').strip()
        if not sku:
            raise ForecastInputError(f'Historical row {line} needs a SKU.')
        obj={'sku':sku}
        for column in HISTORY_COLUMNS[1:]:
            try:
                num = float(row.get(headers[column]) or '')
                if not math.isfinite(num) or num<0:
                    raise ValueError()
                obj[column]=num
            except (TypeError,ValueError):
                raise ForecastInputError(f'Historical row {line}: {column} must be a nonnegative finite number.') from None
        if obj['return_rate_pct']>100:
            raise ForecastInputError(f'Historical row {line}: return_rate_pct must be at most 100.')
        key=(sku,obj['week_index'])
        if key in seen:
            raise ForecastInputError(f'Duplicate SKU/week row: {sku} week {obj["week_index"]:g}.')
        seen.add(key)
        results.append(obj)
    if len(results)<12:
        raise ForecastInputError('TabPFN demonstration needs at least 12 historical weekly observations, not one current inventory snapshot.')
    if len({x['week_index'] for x in results})<3:
        raise ForecastInputError('Supply at least three distinct historic week_index values for a meaningful trend.')
    if len({x['weekly_units_sold'] for x in results})<2:
        raise ForecastInputError('Historical target weekly_units_sold needs variation; identical sample figures cannot establish a forecast.')
    return results


def make_dataset(history_text, current_text):
    rows=_history(history_text)
    current=parse_inventory(current_text)
    skus=sorted(set(x['sku'] for x in rows)|set(x['sku'] for x in current))
    known={x['sku'] for x in rows}
    missing=[x['sku'] for x in current if x['sku'] not in known]
    # Keep schema fixed across train and inference. SKU indicators permit a per-item trend.
    def f(sku, week, cost, price, stock, lead, returns):
        return ([float(week),float(cost),float(price),float(stock),float(lead),float(returns)] +
            [1.0 if s==sku else 0.0 for s in skus])
    x_train=[f(r['sku'],r['week_index'],r['unit_cost_usd'],r['retail_price_usd'],
        r['stock_on_hand'],r['supplier_lead_days'],r['return_rate_pct']) for r in rows]
    y_train=[r['weekly_units_sold'] for r in rows]
    latest=defaultdict(float)
    for r in rows:latest[r['sku']]=max(latest[r['sku']],r['week_index'])
    x_test=[f(i['sku'],latest[i['sku']]+1,i['cost'],i['price'],i['stock'],i['lead'],i['returns']) for i in current]
    return current, x_train, y_train, x_test, missing, len(rows)


def predict(history_text, current_text, *, token='', model_path='v3.5_default', regressor_cls=None):
    token = (token or os.getenv('TABPFN_TOKEN') or '').strip()
    if not token:
        raise ForecastInputError('To run actual TabPFN, add TABPFN_TOKEN from Prior Labs to Render Environment. No inference was performed.')
    current, train, targets, test, unknown, n = make_dataset(history_text, current_text)
    if regressor_cls is None:
        try:
            from tabpfn_client import TabPFNRegressor
            import tabpfn_client
        except ImportError as error:
            raise ForecastInputError('The TabPFN client is missing. Add tabpfn-client to requirements.txt and redeploy.') from error
        tabpfn_client.set_access_token(token)
        regressor_cls=TabPFNRegressor
    # SELLER ASSIST TABPFN NDARRAY COMPATIBILITY v38
    # Prior Labs' sklearn-compatible estimators expect array-like objects with
    # a .shape, not nested Python lists. Keep the CSV/dataset API unchanged.
    stage = 'preparing numeric inputs'
    try:
        import numpy as np
        x_train = np.asarray(train, dtype=np.float64)
        y_train = np.asarray(targets, dtype=np.float64)
        x_test = np.asarray(test, dtype=np.float64)
        if (x_train.ndim != 2 or x_test.ndim != 2 or y_train.ndim != 1
                or x_train.shape[0] != y_train.shape[0]
                or x_train.shape[1] != x_test.shape[1]):
            raise ValueError('Historical and current feature dimensions do not match.')
        stage = 'creating the requested regressor'
        estimator = regressor_cls() if model_path == 'default' else regressor_cls(model_path=model_path)
        stage = 'fitting historical sales'
        estimator.fit(x_train, y_train)
        stage = 'predicting current products'
        values = np.asarray(estimator.predict(x_test), dtype=np.float64).reshape(-1)
    except Exception as error:
        # Never echo a token, and do not relabel a programming error as a
        # token/quota failure. Show the underlying type, stage and short detail.
        detail = str(error).replace(token, '[REDACTED]').strip()
        detail = detail.replace('\n', ' ').replace('\r', ' ')
        detail = detail[:240] or 'No additional detail returned.'
        raise ForecastInputError(
            f'Prior Labs failed while {stage} ({type(error).__name__}): {detail}'
        ) from error
    if len(values)!=len(current):
        raise ForecastInputError('TabPFN returned an unexpected prediction count. No estimates displayed.')
    name=('Prior Labs server default (exact version must be verified in account)' if model_path=='default' else model_path)
    lines=[f'### Actual Prior Labs TabPFN inference — {name}',
           f'**Historical observations used:** {n} · **Current products predicted:** {len(current)}',
           'Predicted next-week units are model estimates; stockout and order suggestions use Wilson EOQ and the prediction.',
           '', '| SKU | Next-week predicted units | Estimated stockout | EOQ order* |',
           '|---|---:|---:|---:|']
    for i,v in zip(current, values):
        v=max(0.0,float(v))
        if not math.isfinite(v):
            raise ForecastInputError('TabPFN produced a non-finite prediction.')
        adjusted=dict(i, weekly=v)
        plan=stock_plan(adjusted)
        horizon=('Not forecast (zero demand)' if plan['days_left'] is None else f'{plan["days_left"]:.1f} days')
        lines.append(f'| `{i["sku"]}` | {v:.1f} | {horizon} | {plan["order_qty"]} |')
    if unknown:
        lines.extend(['', '**Caution:** Current SKUs without historical examples: '+', '.join(unknown)+'. These extrapolations may be unreliable.'])
    lines.extend(['', '*EOQ and reorder point are deterministic calculations using the predicted weekly demand; TabPFN does NOT directly predict an EOQ. No accuracy claim without held-out validation.*',
                  'Historical SKU data was sent to Prior Labs for model inference at your request.'])
    return '\n'.join(lines)
