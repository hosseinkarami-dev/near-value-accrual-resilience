"""Binance Spot source adapter: returns raw klines without transforming them."""
from __future__ import annotations
import time
import urllib.parse
from src.normalize.common import DAY_MS
from src.sources.http_json import fetch_json

ENDPOINT = "https://data-api.binance.vision/api/v3/klines"
INITIAL_START_MS = 1735689600000
PAGE_SIZE = 1000


def fetch_klines(start_ms: int) -> list[list]:
    rows = []
    cursor = start_ms
    while True:
        query = urllib.parse.urlencode({"symbol": "NEARUSDT", "interval": "1d", "startTime": cursor, "limit": PAGE_SIZE})
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
