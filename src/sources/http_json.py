"""Shared HTTP JSON transport for source adapters."""
from __future__ import annotations
import json
import time
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any


def fetch_json(url: str, retries: int = 3) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "near-value-accrual-resilience/1.0", "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError(f"HTTP {response.status}")
                return json.load(response, parse_float=Decimal)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            if attempt + 1 == retries:
                raise RuntimeError(f"{type(exc).__name__}: {exc}") from exc
            time.sleep(min(2 ** attempt, 4))
