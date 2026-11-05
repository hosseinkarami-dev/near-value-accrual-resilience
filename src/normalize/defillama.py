"""Pure DeFiLlama payload normalization; this module performs no I/O."""
from datetime import date, datetime, timezone
from src.normalize.common import DEFINITIONS, START_DATE, dec, utc_now


def primary_chart(payload):
    found = {}
    for item in payload.get("totalDataChart", []) if isinstance(payload, dict) else []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            value = dec(item[1])
            if value is not None:
                found[int(item[0])] = value
    return sorted(found.items())


def tvl_series(payload):
    total, chains = [], {}
    for item in payload.get("tvl", []) if isinstance(payload, dict) else []:
        if isinstance(item, dict):
            value = dec(item.get("totalLiquidityUSD"))
            if value is not None:
                total.append((int(item["date"]), value))
    for chain, info in (payload.get("chainTvls", {}) if isinstance(payload, dict) else {}).items():
        chains[chain] = []
        for item in info.get("tvl", []) if isinstance(info, dict) else []:
            value = dec(item.get("totalLiquidityUSD"))
            if value is not None:
                chains[chain].append((int(item["date"]), value))
    return total, chains


def normalize_payload(metric, endpoint, payload, retrieved, previous=None, start_date=None, end_date=None):
    """Return persisted-shape payload and rows for validation, without writing files."""
    start = date.fromisoformat(start_date) if start_date else START_DATE
    end = date.fromisoformat(end_date) if end_date else utc_now().date()
    if metric == "near_intents_tvl":
        total, chains = tvl_series(payload)
        incoming = {"total": [], "chains": {}}
        for ts, value in total:
            dt = datetime.fromtimestamp(ts, timezone.utc)
            if start <= dt.date() < end:
                incoming["total"].append({"date": dt.date().isoformat(), "timestamp": ts, "metric": metric, "value": value, "unit": "USD", "source": "DeFiLlama", "source_endpoint": endpoint, "retrieved_at": retrieved, "is_final": True, "scope": "total"})
        for chain, points in chains.items():
            incoming["chains"][chain] = []
            for ts, value in points:
                dt = datetime.fromtimestamp(ts, timezone.utc)
                if start <= dt.date() < end:
                    incoming["chains"][chain].append({"date": dt.date().isoformat(), "timestamp": ts, "metric": metric, "value": value, "unit": "USD", "source": "DeFiLlama", "source_endpoint": endpoint, "retrieved_at": retrieved, "is_final": True, "scope": "chain", "chain": chain})
        old_series = previous.get("series", {}) if isinstance(previous, dict) else {}

        def merge_series(old_rows, new_rows):
            keyed = {row["date"]: row for row in old_rows if isinstance(row, dict) and row.get("date")}
            keyed.update({row["date"]: row for row in new_rows})
            return [keyed[key] for key in sorted(keyed)]

        series = {"total": merge_series(old_series.get("total", []), incoming["total"]), "chains": {}}
        old_chains = old_series.get("chains", {}) if isinstance(old_series, dict) else {}
        for chain in set(old_chains) | set(incoming["chains"]):
            series["chains"][chain] = merge_series(old_chains.get(chain, []), incoming["chains"].get(chain, []))
        rows = series["total"] + [row for chain_rows in series["chains"].values() for row in chain_rows]
        document = {"dataset": metric, "unit": "USD", "source_endpoint": endpoint, "methodology": DEFINITIONS[metric] + " Total and chain histories are stored in distinct series.", "updated_at": retrieved, "series": series}
        return document, rows

    rows = []
    for ts, value in primary_chart(payload):
        dt = datetime.fromtimestamp(ts, timezone.utc)
        if dt.date() < start or dt.date() >= end:
            continue
        row = {"date": dt.date().isoformat(), "timestamp": ts, "metric": metric, "value": value, "unit": "USD", "source": "DeFiLlama", "source_endpoint": endpoint, "retrieved_at": retrieved, "is_final": True}
        if metric == "near_intents_holders_revenue_buyback":
            row["classification"] = "near_treasury_revenue" if dt.date() < date(2026, 2, 23) else "near_buyback"
            row["classification_effective_date"] = "2026-02-23"
            row["methodology"] = "DeFiLlama holders revenue; classified as NEAR Treasury revenue before 2026-02-23 and NEAR Buyback from that date. This is not token burn."
        rows.append(row)
    return None, rows
