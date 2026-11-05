"""Raw BigQuery fetch adapter for daily total supply."""
from src.sources.bigquery.client import execute_query
from src.sources.bigquery.query_loader import load_query

TABLE = "bigquery-public-data.crypto_near_mainnet_us.blocks"
QUERY_NAME = "daily_total_supply"


def fetch_daily_supply(start_date: str, end_date: str):
    """Return raw daily supply rows for the half-open UTC date range [start, end)."""
    query = load_query(QUERY_NAME, table=TABLE, start_date=start_date, end_date=end_date)
    return execute_query(query)
