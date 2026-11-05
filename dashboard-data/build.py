"""Prepare static-dashboard JSON from normalized source data; no network requests."""
from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATA = ROOT / "data"
OUTPUT = ROOT / "dashboard" / "public" / "data" / "dashboard.json"

METRICS = {
    "network_dex_volume": ("Network DEX volume", "network/daily_dex_trading_volume.json", "flow"),
    "network_fees": ("Network fees", "network/daily_revenue_fees.json", "flow"),
    "network_tvl": ("NEAR network TVL", "network/historical_tvl.json", "stock"),
    "stablecoin_supply": ("Stablecoin supply", "network/daily_stablecoin_supply.json", "stock"),
    "intents_tvl": ("NEAR Intents TVL", "near_intents/historical_tvl.json", "stock"),
    "intents_dex_volume": ("NEAR Intents DEX volume", "near_intents/daily_dex_trading_volume.json", "flow"),
    "intents_gross_fees": ("NEAR Intents gross fees", "near_intents/daily_gross_fees.json", "flow"),
    "intents_net_revenue": ("NEAR Intents net revenue", "near_intents/daily_net_revenue.json", "flow"),
    "intents_holders_revenue": ("NEAR Intents holders revenue", "near_intents/daily_holders_revenue_buyback.json", "flow"),
}


def read_json(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def number(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    try:
        parsed = Decimal(str(value))
        return float(parsed) if parsed.is_finite() else None
    except Exception:
        return None


def month_start(day: date) -> date:
    return day.replace(day=1)


def period_key(day: date, interval: str) -> date:
    if interval == "weekly":
        return day - timedelta(days=day.weekday())
    return month_start(day)


def aggregate(rows: list[dict], kind: str, interval: str) -> list[dict]:
    buckets: dict[date, list[dict]] = {}
    for row in rows:
        day = date.fromisoformat(row["date"])
        buckets.setdefault(period_key(day, interval), []).append(row)

    output = []
    for start, values in sorted(buckets.items()):
        values.sort(key=lambda item: item["date"])
        if kind == "flow":
            value = sum((number(item["value"]) or 0 for item in values), 0)
            source_date = values[-1]["date"]
        else:
            # Stock metrics (TVL and supply) are represented by the last observation in a period.
            value = number(values[-1]["value"])
            source_date = values[-1]["date"]
        end = start + timedelta(days=6) if interval == "weekly" else start.replace(day=monthrange(start.year, start.month)[1])
        output.append({
            "date": start.isoformat(),
            "period_end": min(end, date.fromisoformat(source_date)).isoformat(),
            "source_date": source_date,
            "value": value,
            "observations": len(values),
        })
    return output


def metric_rows(metric_id: str, source_path: str) -> list[dict]:
    document = read_json(SOURCE_DATA / source_path)
    if metric_id == "intents_tvl":
        rows = document.get("series", {}).get("total", [])
    else:
        rows = document.get("observations", [])
    output = []
    for row in rows:
        value = number(row.get("value"))
        if row.get("date") and value is not None:
            output.append({"date": row["date"], "value": value})
    return sorted(output, key=lambda item: item["date"])


def all_time_metrics() -> dict:
    document = read_json(SOURCE_DATA / "all_time_metrics.json")
    result = {}
    # The dashboard is intentionally DeFiLlama-only for now.
    for section in ("near_intents", "network"):
        for key, item in document.get(section, {}).items():
            if item.get("source") != "DeFiLlama":
                continue
            value = number(item.get("value"))
            if value is not None:
                result[key] = {
                    "value": value,
                    "unit": item.get("unit", "USD"),
                    "source": item.get("source"),
                    "updated_at": item.get("updated_at"),
                    "methodology": item.get("methodology"),
                }
    return result


def build() -> dict:
    series = {}
    for metric_id, (label, relative_path, kind) in METRICS.items():
        rows = metric_rows(metric_id, relative_path)
        series[metric_id] = {
            "label": label,
            "kind": kind,
            "unit": "USD",
            "aggregation": "sum" if kind == "flow" else "last_observation_in_period",
            "observation_count": len(rows),
            "first_date": rows[0]["date"] if rows else None,
            "last_date": rows[-1]["date"] if rows else None,
            "daily": rows,
            "weekly": aggregate(rows, kind, "weekly"),
            "monthly": aggregate(rows, kind, "monthly"),
        }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_scope": "DeFiLlama only",
        "all_time": all_time_metrics(),
        "series": series,
    }


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Dashboard data prepared: {OUTPUT.relative_to(ROOT)}")
