"""Refresh the daily NEAR activity and cohort JSON dataset from BigQuery."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.pipelines.bigquery_user_activity import run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", help="Override the incremental start date (use 2025-05-10 for a full historical refresh).")
    args = parser.parse_args()
    print(run(start_date=args.start_date))
