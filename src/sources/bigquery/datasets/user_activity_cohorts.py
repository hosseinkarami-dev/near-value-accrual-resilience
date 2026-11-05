"""Raw BigQuery adapter for daily user activity and cohort metrics."""
from datetime import date

from src.sources.bigquery.client import execute_query
from src.sources.bigquery.query_loader import load_query

TABLE = "bigquery-public-data.crypto_near_mainnet_us.transactions"
QUERY_NAME = "daily_user_activity_by_signer"


def fetch_daily_signer_activity(start_date: str, end_date: str):
    """Fetch one row per signer/day for the half-open UTC range [start, end)."""
    start = date.fromisoformat(start_date).isoformat()
    end = date.fromisoformat(end_date).isoformat()
    if end <= start:
        raise ValueError("end_date must be later than start_date")
    query = load_query(QUERY_NAME, start_date=start, end_date=end)
    return execute_query(query)
