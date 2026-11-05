"""BigQuery daily supply pipeline: query, normalize, validate, and persist."""
from datetime import date, datetime, timedelta, timezone
from src.contracts.datasets import DATASETS, validate_document
from src.normalize.bigquery import normalize_supply_rows
from src.normalize.common import START_DATE
from src.sources.bigquery.datasets.daily_total_supply import TABLE, fetch_daily_supply
from src.storage.json_store import DATA_DIR as NORMALIZED, load_json, write_json

OVERLAP_DAYS = 2


def run(start_date=None):
    contract = DATASETS["near_daily_total_supply"]
    today = datetime.now(timezone.utc).date()
    retrieved = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    path = NORMALIZED / contract.filename
    stored = load_json(path, {"observations": []})
    old = stored.get("observations", []) if isinstance(stored, dict) else []
    if isinstance(start_date, str):
        start = date.fromisoformat(start_date)
    elif isinstance(start_date, date):
        start = start_date
    else:
        previous_dates = [date.fromisoformat(row["date"]) for row in old if row.get("date")]
        latest = max(previous_dates, default=None)
        start = max(START_DATE, latest - timedelta(days=OVERLAP_DAYS)) if latest else START_DATE
    try:
        source_rows = fetch_daily_supply(start.isoformat(), today.isoformat())
    except Exception as exc:
        return {"dataset": contract.key, "path": str(path.relative_to(path.parents[1])).replace("\\", "/"), "source": contract.source, "source_endpoint": TABLE, "status": "unavailable", "retrieval_error": str(exc), "observation_count": len(old), "missing_dates": [], "validation_errors": [str(exc)]}
    observations, missing, duplicate_dates, errors = normalize_supply_rows(source_rows, old, start, today, retrieved)
    document = {"dataset": contract.key, "unit": contract.unit, "source": contract.source, "source_endpoint": TABLE, "methodology": "Last block per UTC date selected with ROW_NUMBER ordered by block timestamp descending then block height descending. BigQuery FLOAT64 total_supply is in yoctoNEAR; converted to NEAR using Decimal division by 10^24 and marked approximate_float64.", "updated_at": retrieved, "observations": observations}
    validate_document(contract, document)
    write_json(path, document)
    dates = [row["date"] for row in observations]
    return {"dataset": contract.key, "path": str(path.relative_to(path.parents[1])).replace("\\", "/"), "source": contract.source, "source_endpoint": TABLE, "metric_definition": "Approximate daily total NEAR supply at the last available block of each UTC day.", "unit": contract.unit, "earliest_available_date": dates[0] if dates else None, "latest_available_finalized_date": dates[-1] if dates else None, "observation_count": len(observations), "missing_dates": missing, "duplicate_dates": duplicate_dates, "validation_errors": errors, "supply_precision": "approximate_float64; exact yocto values not generated", "status": "retrieved" if not errors and not missing else "retrieved_with_errors"}
