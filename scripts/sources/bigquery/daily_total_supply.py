"""Update the daily supply dataset from BigQuery."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.pipelines.bigquery import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", help="Override incremental start date; 2025-05-10 refreshes the full stored range.")
    args = parser.parse_args()
    print(run(start_date=args.start_date))
