"""Normalization for network-level DeFiLlama histories and current snapshots."""
from datetime import datetime, timezone
from decimal import Decimal

from src.normalize.common import dec
from src.normalize.defillama import primary_chart


def _date(timestamp):
    return datetime.fromtimestamp(int(timestamp), timezone.utc).date().isoformat()


def _sum_values(value):
    if isinstance(value, dict):
        values = [dec(item) for item in value.values()]
    elif isinstance(value, (int, float, Decimal, str)):
        values = [dec(value)]
    else:
        return None
    values = [item for item in values if item is not None]
    return sum(values, Decimal(0)) if values else None


def _daily_row(metric, endpoint, retrieved, day, value, **fields):
    return {
        "date": day,
        "metric": metric,
        "value": value,
        "unit": "USD",
        "source": "DeFiLlama",
        "source_endpoint": endpoint,
        "retrieved_at": retrieved,
        "is_final": True,
        **fields,
    }


def normalize_network_history(metric, endpoint, payload, retrieved, start_date, end_date):
    """Normalize daily provider results to a half-open UTC date window."""
    rows = []
    if metric in {"near_network_dex_volume", "near_network_fees"}:
        for timestamp, value in primary_chart(payload):
            day = _date(timestamp)
            if start_date <= day < end_date:
                rows.append(_daily_row(metric, endpoint, retrieved, day, value, timestamp=timestamp))
    elif metric == "near_network_historical_tvl":
        for item in payload if isinstance(payload, list) else []:
            if not isinstance(item, dict) or item.get("date") is None:
                continue
            timestamp = int(item["date"])
            day = _date(timestamp)
            value = dec(item.get("tvl"))
            if value is not None and start_date <= day < end_date:
                rows.append(_daily_row(metric, endpoint, retrieved, day, value, timestamp=timestamp))
    elif metric == "near_network_stablecoin_supply":
        for item in payload if isinstance(payload, list) else []:
            if not isinstance(item, dict) or item.get("date") is None:
                continue
            timestamp = int(item["date"])
            day = _date(timestamp)
            usd = _sum_values(item.get("totalCirculatingUSD"))
            if usd is not None and start_date <= day < end_date:
                rows.append(_daily_row(
                    metric, endpoint, retrieved, day, usd, timestamp=timestamp,
                    circulating_by_peg=item.get("totalCirculating"),
                ))
    return sorted(rows, key=lambda row: row["date"])


def all_time_total(payload):
    """Use a provider lifetime total when present; otherwise sum its full daily chart."""
    value = dec(payload.get("totalAllTime")) if isinstance(payload, dict) else None
    if value is not None:
        return value
    protocols = payload.get("protocols", []) if isinstance(payload, dict) else []
    protocol_totals = [dec(item.get("totalAllTime")) for item in protocols if isinstance(item, dict)]
    if protocol_totals and all(item is not None for item in protocol_totals):
        return sum(protocol_totals, Decimal(0))
    chart = primary_chart(payload)
    if chart:
        return sum((value for _, value in chart), Decimal(0))
    return None


def current_stablecoin_supply(payload, chain_name="Near"):
    for item in payload if isinstance(payload, list) else []:
        if isinstance(item, dict) and str(item.get("name", "")).casefold() == chain_name.casefold():
            return _sum_values(item.get("totalCirculatingUSD", item.get("totalCirculating")))
    return None
