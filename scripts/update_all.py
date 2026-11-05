"""Update selected source families without generating a report artifact."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src.sources.registry import available_sources, select_sources
from src.pipelines.binance import run as update_price
from src.pipelines.bigquery import run as update_supply
from src.pipelines.bigquery_user_activity import run as update_user_activity
from src.pipelines.defillama import run_series
from src.pipelines.defillama_network import run_network_metrics


RUNNERS = {
    "binance": [("token_price", update_price)],
    "defillama": [
        ("defillama_tvl", lambda: run_series("near_intents_tvl")),
        ("defillama_dex_volume", lambda: run_series("near_intents_dex_volume")),
        ("defillama_gross_fees", lambda: run_series("near_intents_gross_fees")),
        ("defillama_net_revenue", lambda: run_series("near_intents_net_revenue")),
        ("defillama_holders_revenue", lambda: run_series("near_intents_holders_revenue_buyback")),
        ("defillama_network_metrics", run_network_metrics),
    ],
    "bigquery": [
        ("daily_total_supply", update_supply),
        ("daily_user_activity_cohorts", update_user_activity),
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", action="append", choices=[*available_sources(), "all"],
        help="Source family to update; repeat to select multiple. Defaults to all implemented sources.",
    )
    args = parser.parse_args()
    requested = args.source
    if requested and "all" in requested and len(requested) > 1:
        parser.error("'all' cannot be combined with another --source")
    names = select_sources(None if not requested or "all" in requested else requested)
    outcomes = []
    for source in names:
        jobs = RUNNERS.get(source)
        if jobs is None:
            print(f"{source}: adapter not implemented")
            outcomes.append(False)
            continue
        for name, run in jobs:
            try:
                result = run()
                status = result.get("status", "completed")
                outcomes.append(status in ("retrieved", "retrieved_with_errors", "completed"))
            except Exception as exc:
                status = f"failed ({type(exc).__name__}: {exc})"
                outcomes.append(False)
            print(f"{name}: {status}")
    return 0 if all(outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
