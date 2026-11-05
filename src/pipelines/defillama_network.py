"""DeFiLlama network-level daily histories and current snapshots."""
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.contracts.datasets import DATASETS, validate_document
from src.normalize.common import START_DATE, iso_now
from src.normalize.defillama_network import all_time_total, current_stablecoin_supply, normalize_network_history
from src.sources.defillama.client import endpoint_for, fetch_payload
from src.storage.all_time import save_metric
from src.storage.json_store import DATA_DIR, existing_rows, load_json, save_rows, upsert


DAILY_METRICS = (
    "near_network_dex_volume",
    "near_network_fees",
    "near_network_historical_tvl",
    "near_network_stablecoin_supply",
)
FLOW_METRICS = {"near_network_dex_volume", "near_network_fees"}
TODAY_UTC = lambda: datetime.now(timezone.utc).date()


def _next_start(path, today):
    rows = existing_rows(path)
    if not rows:
        return START_DATE
    return min(today, date.fromisoformat(max(row["date"] for row in rows)) + timedelta(days=1))


def _range_url(endpoint, start, end, stablecoin=False):
    parts = urlsplit(endpoint)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    start_ts = int(datetime.combine(start, datetime.min.time(), timezone.utc).timestamp())
    end_ts = int(datetime.combine(end, datetime.min.time(), timezone.utc).timestamp())
    query.update({"start": str(start_ts), "end": str(end_ts)})
    if stablecoin:
        # The stablecoin chart endpoint supports startts; start/end are retained for API versions
        # that support conventional range parameter names.
        query["startts"] = str(start_ts)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _without_chart(endpoint):
    parts = urlsplit(endpoint)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({"excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true"})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _save_daily(metric, endpoint, payload, start, today, retrieved):
    contract = DATASETS[metric]
    path = DATA_DIR / contract.filename
    old_rows = existing_rows(path)
    incoming = normalize_network_history(metric, endpoint, payload, retrieved, start.isoformat(), today.isoformat())
    methodology = {
        "near_network_dex_volume": "Daily DEX trading volume aggregated across DeFiLlama-tracked DEX protocols on NEAR.",
        "near_network_fees": "Daily fees paid by users across DeFiLlama-tracked protocols on NEAR; this is not protocol revenue or NEAR token burn.",
        "near_network_historical_tvl": "Daily DeFi TVL on NEAR from DeFiLlama; excludes liquid staking and double-counted TVL.",
        "near_network_stablecoin_supply": "Daily stablecoin circulating supply on NEAR, expressed as aggregate USD value with peg-category supply breakdown where available.",
    }[metric]
    save_rows(path, metric, upsert(old_rows, incoming), endpoint, contract.unit, methodology, contract)
    validate_document(contract, load_json(path, {}))
    return {"dataset": metric, "path": str(path.relative_to(DATA_DIR)), "observation_count": len(incoming), "stored_observation_count": len(existing_rows(path)), "status": "retrieved" if incoming else "up_to_date"}


def run_network_metrics():
    today = TODAY_UTC()
    retrieved = iso_now()
    outcomes = []
    all_time = {}
    range_starts = []

    for metric in DAILY_METRICS:
        contract = DATASETS[metric]
        endpoint = endpoint_for(metric)
        path = DATA_DIR / contract.filename
        start = _next_start(path, today)
        range_starts.append(start)
        try:
            if start < today:
                payload = fetch_payload(_range_url(endpoint, start, today, metric == "near_network_stablecoin_supply"))
                outcome = _save_daily(metric, endpoint, payload, start, today, retrieved)
            else:
                outcome = {"dataset": metric, "path": str(path.relative_to(DATA_DIR)), "observation_count": 0, "stored_observation_count": len(existing_rows(path)), "status": "up_to_date"}
            if metric in FLOW_METRICS:
                # Lifetime totals refresh independently from the incremental daily history.
                summary = fetch_payload(_without_chart(endpoint))
                lifetime = all_time_total(summary)
                if lifetime is not None:
                    all_time[metric] = lifetime
                    save_metric("network", metric, lifetime, "USD", endpoint, "Provider lifetime total, refreshed independently from the daily history.")
                else:
                    lifetime = all_time_total(fetch_payload(endpoint))
                    if lifetime is not None:
                        all_time[metric] = lifetime
                        save_metric("network", metric, lifetime, "USD", endpoint, "Sum of the provider's complete daily chart; refreshed independently from the incremental daily history.")
            outcomes.append(outcome)
        except Exception as exc:
            outcomes.append({"dataset": metric, "status": "unavailable", "error": str(exc)})

    try:
        current_chains = fetch_payload(endpoint_for("near_network_current_chains"))
        near_chain = next((row for row in current_chains if isinstance(row, dict) and str(row.get("name", "")).casefold() == "near"), None)
        if near_chain and near_chain.get("tvl") is not None:
            save_metric("network", "current_chain_tvl", near_chain["tvl"], "USD", endpoint_for("near_network_current_chains"), "Current TVL snapshot for the NEAR chain; stock value, not a cumulative flow.")
        else:
            raise RuntimeError("NEAR was not present in the current chain TVL response")
        current_stables = fetch_payload(endpoint_for("near_network_current_stablecoins"))
        supply = current_stablecoin_supply(current_stables, "Near")
        if supply is not None:
            save_metric("network", "current_stablecoin_supply", supply, "USD", endpoint_for("near_network_current_stablecoins"), "Current aggregate USD value of circulating stablecoins on NEAR.")
        else:
            raise RuntimeError("NEAR stablecoin supply was not present in the current stablecoin response")
        snapshot_status = "retrieved"
    except Exception as exc:
        snapshot_status = f"unavailable: {exc}"

    failures = sum(item["status"] == "unavailable" for item in outcomes)
    return {
        "dataset": "near_network_defillama_metrics",
        "source": "DeFiLlama",
        "queried_start_date": min(range_starts, default=today).isoformat(),
        "queried_end_date_exclusive": today.isoformat(),
        "daily_metrics": outcomes,
        "current_snapshots": snapshot_status,
        "all_time_values_updated": sorted(all_time),
        "status": "retrieved_with_errors" if failures or snapshot_status != "retrieved" else "retrieved",
    }
