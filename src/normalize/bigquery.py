"""Normalize BigQuery supply rows to the existing daily supply JSON contract."""
from datetime import date, timedelta
from decimal import Decimal
YOCTO = Decimal(10) ** 24


def normalize_supply_rows(source_rows, old_rows, start, today, retrieved):
    by_date = {}
    for item in source_rows:
        day = str(item["utc_date"])
        raw_supply = Decimal(str(item["total_supply"]))
        if raw_supply <= 0:
            continue
        stamp = item["block_timestamp_utc"]
        stamp = stamp if stamp.endswith("Z") else stamp.replace(" ", "T") + "Z"
        by_date[day] = {"date": day, "block_height": int(item["block_height"]), "block_hash": item["block_hash"], "block_timestamp_utc": stamp, "total_supply_near": raw_supply / YOCTO, "supply_precision": "approximate_float64", "unit": "NEAR", "source": "BigQuery", "retrieved_at": retrieved, "is_final": True}
    # Keep all earlier history when the pipeline fetches only a recent overlap window.
    for row in old_rows:
        day = row.get("date", "")
        if day and day not in by_date and day < today.isoformat():
            by_date[day] = row
    observations = [by_date[key] for key in sorted(by_date)]
    dates = [row["date"] for row in observations]
    unique = set(dates)
    missing = []
    if dates:
        cursor = start
        end = min(today - timedelta(days=1), date.fromisoformat(dates[-1]))
        while cursor <= end:
            if cursor.isoformat() not in unique:
                missing.append(cursor.isoformat())
            cursor += timedelta(days=1)
    errors = []
    duplicate_dates = len(dates) - len(unique)
    if duplicate_dates:
        errors.append(f"{duplicate_dates} duplicate daily dates detected")
    if any(Decimal(str(row["total_supply_near"])) <= 0 for row in observations):
        errors.append("non-positive supply value detected")
    return observations, missing, duplicate_dates, errors
