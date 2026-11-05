"""Normalize grouped BigQuery signer/day records before cohort aggregation."""
from datetime import date


def normalize_signer_activity_rows(source_rows):
    """Validate grouped source rows while keeping account ids for cohort state."""
    rows = []
    for source in source_rows:
        activity_day = date.fromisoformat(str(source["activity_date"]))
        user_id = str(source["user_id"])
        transaction_count = int(source["transaction_count"])
        if not user_id or transaction_count < 1:
            raise ValueError("Invalid signer activity row")
        rows.append({"date": activity_day.isoformat(), "user_id": user_id, "transaction_count": transaction_count})
    return rows
