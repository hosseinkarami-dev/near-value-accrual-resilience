"""Shared helpers for the independent historical data generators."""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
START_DATE = date(2025, 5, 10)
DAY_MS = 86_400_000
DEFINITIONS = {
 "near_intents_tvl":"DeFiLlama historical protocol TVL in USD, retained as separate total and chain-level series.",
 "near_intents_dex_volume":"DeFiLlama daily NEAR Intents DEX volume in USD; distinct from total NEAR Intents volume.",
 "near_intents_gross_fees":"Gross fees charged on NEAR Intents swaps, including protocol and affiliate/distribution fees.",
 "near_intents_net_revenue":"NEAR net captured revenue measured through NEAR/wNEAR swept into revenue wallets.",
 "near_intents_holders_revenue_buyback":"Holders revenue classification; treasury revenue before 2026-02-23 and buyback from that date, not token burn.",
}
def utc_now(): return datetime.now(timezone.utc)
def iso_now(): return utc_now().isoformat().replace('+00:00','Z')
def dec(value):
 if value is None or isinstance(value,bool): return None
 try:
  result=Decimal(str(value)); return result if result.is_finite() else None
 except (InvalidOperation,ValueError): return None
def validate(name,path,rows,endpoint,unit,error=None,limitations=None,series_by_id=False):
 rows=sorted(rows,key=lambda r:(r['date'],str(r.get('breakdown','')))); dates=[r['date'] for r in rows]; unique=sorted(set(dates))
 missing=[]
 if unique:
  seen=set(unique); cursor=date.fromisoformat(unique[0]); end=date.fromisoformat(unique[-1])
  while cursor<=end:
   if cursor.isoformat() not in seen:missing.append(cursor.isoformat())
   cursor+=timedelta(days=1)
 invalid=[]
 for r in rows:
  v=dec(r.get('close') if r.get('metric')=='near_usdt_daily_candle' else r.get('value'))
  if v is None:invalid.append(r.get('date'))
  if r.get('metric')=='near_usdt_daily_candle':
   p=[dec(r.get(k)) for k in ('open','high','low','close')]
   if any(x is None or x<=0 for x in p) or (p[2] is not None and p[0] is not None and p[3] is not None and p[1] is not None and (p[2]>min(p[0],p[3]) or p[1]<max(p[0],p[3]))):invalid.append(r.get('date'))
 series_ids=sorted({r.get('chain','total') if r.get('scope') else 'primary' for r in rows}) if series_by_id else ['primary']
 per_series={}
 for sid in series_ids:
  sr=[r for r in rows if (r.get('chain','total') if r.get('scope') else 'primary')==sid]; ds=[r['date'] for r in sr]; us=sorted(set(ds)); gaps=[]
  if us:
   cur=date.fromisoformat(us[0]); end=date.fromisoformat(us[-1]); seen=set(us)
   while cur<=end:
    if cur.isoformat() not in seen:gaps.append(cur.isoformat())
    cur+=timedelta(days=1)
  per_series[sid]={'observation_count':len(sr),'unique_utc_dates':len(us),'duplicate_dates':len(ds)-len(set(ds)),'missing_dates':gaps}
 keys=[(r['date'],r.get('chain','total') if r.get('scope') else 'primary') for r in rows]
 return {'dataset':name,'path':str(path.relative_to(ROOT)).replace('\\','/'),'source':'Binance Spot' if 'binance' in endpoint else 'DeFiLlama','source_endpoint':endpoint,'metric_definition':DEFINITIONS.get(name,'UTC daily Binance Spot NEAR/USDT candle; close is primary price metric.'),'unit':unit,'earliest_available_date':unique[0] if unique else None,'latest_available_finalized_date':max((r['date'] for r in rows if r.get('is_final',True)),default=None),'observation_count':len(rows),'unique_utc_dates':len(unique),'missing_dates':missing,'duplicate_observations':len(keys)-len(set(keys)),'duplicate_dates':sum(v['duplicate_dates'] for v in per_series.values()),'series_validation':per_series,'null_or_invalid_values':invalid,'expected_daily_coverage':(date.fromisoformat(unique[-1])-date.fromisoformat(unique[0])).days+1 if unique else 0,'actual_daily_coverage':len(unique),'known_limitations':limitations or [],'data_kind':'normalized','retrieval_error':error,'status':'unavailable' if error else ('no_observations' if not rows else 'retrieved')}
