"""Incrementally update historical Binance candles and current NEAR price."""
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlencode

from src.contracts.datasets import DATASETS
from src.normalize.binance import normalize_klines
from src.normalize.common import START_DATE, iso_now, utc_now, validate
from src.sources.binance.client import ENDPOINT, TICKER_ENDPOINT, fetch_current_price, fetch_klines
from src.storage.all_time import save_metric
from src.storage.json_store import DATA_DIR as NORMALIZED, existing_rows, save_rows, upsert


def _midnight_ms(day):
    return int(datetime.combine(day, time.min, timezone.utc).timestamp() * 1000)


def run():
    contract = DATASETS["near_daily_price"]
    path = NORMALIZED / contract.filename
    old = existing_rows(path)
    today = utc_now().date()
    latest_day = max((date.fromisoformat(row["date"]) for row in old if row.get("date")), default=None)
    start_day = max(START_DATE, latest_day + timedelta(days=1)) if latest_day else START_DATE
    start_ms, end_ms = _midnight_ms(start_day), _midnight_ms(today)
    exact_endpoint = f"{ENDPOINT}?" + urlencode({"symbol": "NEARUSDT", "interval": "1d"})
    if start_day < today:
        exact_endpoint += "&" + urlencode({"startTime": start_ms, "endTime": end_ms - 1, "limit": 1000})
    retrieved = iso_now()
    error = None
    try:
        incoming = normalize_klines(fetch_klines(start_ms, end_ms), retrieved, today) if start_day < today else []
        if start_day < today:
            save_rows(path, contract.key, upsert(old, incoming), exact_endpoint, contract.unit, "Daily Binance Spot Kline; source timestamps retained. Close is the canonical NEAR/USDT price.", contract)
    except Exception as exc:
        error = str(exc)
    current_price_error = None
    current_price = None
    try:
        current_price = fetch_current_price()
        save_metric("network", "current_token_price", current_price, "USDT", TICKER_ENDPOINT + "?symbol=NEARUSDT", "Latest Binance Spot ticker price for NEAR/USDT; a live snapshot, not a daily candle close.", source="Binance Spot")
    except Exception as exc:
        current_price_error = str(exc)
    result = validate("NEAR daily price", path, existing_rows(path), exact_endpoint, contract.unit, error, ["UTC daily Spot candle; incomplete current UTC day excluded.", "Historical requests use the stored latest date + 1 through the current UTC date, with Binance startTime/endTime partitioning."])
    result["queried_start_date"] = start_day.isoformat()
    result["queried_end_date_exclusive"] = today.isoformat()
    result["new_observations"] = len(incoming) if error is None else 0
    result["current_token_price_usdt"] = current_price
    result["current_token_price_error"] = current_price_error
    return result
