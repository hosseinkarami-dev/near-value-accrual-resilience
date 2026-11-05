"""Binance Spot source adapter: returns raw klines without transforming them."""
from __future__ import annotations
import time
import urllib.parse
from src.normalize.common import DAY_MS, dec
from src.sources.http_json import fetch_json

ENDPOINT = "https://data-api.binance.vision/api/v3/klines"
TICKER_ENDPOINT = "https://data-api.binance.vision/api/v3/ticker/price"
PAGE_SIZE = 1000


def fetch_klines(start_ms: int, end_ms: int) -> list[list]:
    """Fetch daily candles in the half-open UTC range [start_ms, end_ms)."""
    if end_ms <= start_ms:
        return []
    rows = []
    cursor = start_ms
    while True:
        query = urllib.parse.urlencode({"symbol": "NEARUSDT", "interval": "1d", "startTime": cursor, "endTime": end_ms - 1, "limit": PAGE_SIZE})
        page = fetch_json(f"{ENDPOINT}?{query}")
        if not isinstance(page, list):
            raise RuntimeError("Unexpected Binance response: expected an array")
        if not page:
            break
        rows.extend(page)
        next_cursor = int(page[-1][0]) + DAY_MS
        if next_cursor <= cursor:
            raise RuntimeError("Binance pagination did not advance")
        cursor = next_cursor
        if len(page) < PAGE_SIZE:
            break
        time.sleep(0.15)
    return rows


def fetch_current_price():
    """Fetch the current NEAR/USDT ticker price."""
    query = urllib.parse.urlencode({"symbol": "NEARUSDT"})
    payload = fetch_json(f"{TICKER_ENDPOINT}?{query}")
    if not isinstance(payload, dict) or payload.get("symbol") != "NEARUSDT" or payload.get("price") is None:
        raise RuntimeError("Unexpected Binance ticker response for NEARUSDT")
    price = dec(payload["price"])
    if price is None:
        raise RuntimeError("Invalid Binance ticker price for NEARUSDT")
    return price
