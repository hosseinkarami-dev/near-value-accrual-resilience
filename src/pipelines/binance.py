"""Dataset update orchestration for Binance Spot."""
from datetime import date, datetime, timedelta, timezone
from src.contracts.datasets import DATASETS
from src.normalize.binance import normalize_klines
from src.normalize.common import START_DATE, iso_now, utc_now, validate
from src.sources.binance.client import ENDPOINT, INITIAL_START_MS, fetch_klines
from src.storage.json_store import DATA_DIR as NORMALIZED, existing_rows, save_rows, upsert


def run():
    contract = DATASETS["near_daily_price"]
    path = NORMALIZED / contract.filename
    old = existing_rows(path)
    today = utc_now().date()
    overlap = date.fromisoformat(old[-1]["date"]) - timedelta(days=2) if old else START_DATE
    start_ms = INITIAL_START_MS if not old else max(int(datetime.combine(overlap, datetime.min.time(), timezone.utc).timestamp() * 1000), INITIAL_START_MS)
    exact_endpoint = f"{ENDPOINT}?symbol=NEARUSDT&interval=1d&startTime={INITIAL_START_MS}&limit=1000"
    retrieved = iso_now()
    error = None
    try:
        incoming = normalize_klines(fetch_klines(start_ms), retrieved, today)
    except Exception as exc:
        error = str(exc)
        incoming = []
    old = [{k: v for k, v in row.items() if k != "value"} for row in old]
    if error is None:
        save_rows(path, contract.key, upsert(old, incoming), exact_endpoint, contract.unit, "Daily Binance Spot Kline; source timestamps retained. Close is the canonical NEAR/USDT price.", contract)
    return validate("NEAR daily price", path, existing_rows(path), exact_endpoint, contract.unit, error, ["UTC daily Spot candle; incomplete current UTC day excluded.", "Initial request preserves supplied January 1, 2025 timestamp; normalized observations start May 10, 2025."])
