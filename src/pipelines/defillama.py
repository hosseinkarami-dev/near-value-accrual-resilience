"""DeFiLlama NEAR Intents datasets, with incremental historical updates."""
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.contracts.datasets import DATASETS, validate_document
from src.normalize.common import START_DATE, iso_now, validate
from src.normalize.defillama import normalize_payload
from src.normalize.defillama_network import all_time_total
from src.sources.defillama.client import endpoint_for, fetch_payload
from src.storage.all_time import save_metric
from src.storage.json_store import DATA_DIR as NORMALIZED, load_json, save_rows, upsert, write_json


def _rows_from_document(metric, document):
    if metric != "near_intents_tvl":
        return existing_rows_for_document(document)
    series = document.get("series", {}) if isinstance(document, dict) else {}
    rows = list(series.get("total", []))
    for chain_rows in series.get("chains", {}).values():
        rows.extend(chain_rows)
    return rows


def existing_rows_for_document(document):
    rows = document.get("observations", []) if isinstance(document, dict) else []
    return [row for row in rows if isinstance(row, dict) and row.get("date")]


def _next_start(metric, previous, today):
    if metric == "near_intents_tvl":
        series = previous.get("series", {}) if isinstance(previous, dict) else {}
        latest_dates = []
        total_dates = [row["date"] for row in series.get("total", []) if row.get("date")]
        if total_dates:
            latest_dates.append(max(total_dates))
        for chain_rows in series.get("chains", {}).values():
            chain_dates = [row["date"] for row in chain_rows if row.get("date")]
            if chain_dates:
                latest_dates.append(max(chain_dates))
        if not latest_dates:
            return START_DATE
        latest = min(latest_dates)
    else:
        dates = [row["date"] for row in existing_rows_for_document(previous)]
        if not dates:
            return START_DATE
        latest = max(dates)
    return min(today, date.fromisoformat(latest) + timedelta(days=1))


def _range_endpoint(endpoint, start, end):
    """Send a half-open timestamp window; endpoints without range support ignore these parameters."""
    parts = urlsplit(endpoint)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({
        "start": str(int(datetime.combine(start, datetime.min.time(), timezone.utc).timestamp())),
        "end": str(int(datetime.combine(end, datetime.min.time(), timezone.utc).timestamp())),
    })
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _summary_endpoint(endpoint):
    parts = urlsplit(endpoint)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({"excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true"})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def run_series(metric):
    contract = DATASETS[metric]
    path = NORMALIZED / contract.filename
    endpoint = endpoint_for(metric)
    previous = load_json(path, {})
    old_rows = _rows_from_document(metric, previous)
    retrieved = iso_now()
    today = datetime.now(timezone.utc).date()
    start = _next_start(metric, previous, today)
    error = None
    source_payload = None
    try:
        if start < today:
            source_payload = fetch_payload(_range_endpoint(endpoint, start, today))
            document, incoming = normalize_payload(metric, endpoint, source_payload, retrieved, previous, start.isoformat(), today.isoformat())
            if metric == "near_intents_tvl":
                validate_document(contract, document)
                write_json(path, document)
            else:
                save_rows(path, metric, upsert([row for row in old_rows if not row.get("breakdown")], incoming), endpoint, contract.unit, "Primary totalDataChart series only; original timestamps retained and UTC date derived.", contract)
        if metric in {"near_intents_dex_volume", "near_intents_gross_fees", "near_intents_net_revenue", "near_intents_holders_revenue_buyback"}:
            summary = fetch_payload(_summary_endpoint(endpoint))
            lifetime = all_time_total(summary)
            if lifetime is None:
                lifetime = all_time_total(fetch_payload(endpoint))
            save_metric("near_intents", metric, lifetime, "USD", endpoint, "Provider lifetime total or the sum of the provider's complete daily chart.")
    except Exception as exc:
        error = str(exc)
    rows = _rows_from_document(metric, load_json(path, {}))
    limitations = ["Current UTC date is excluded until the day is complete; stored dates are incrementally extended from latest stored date + 1.", "Some DeFiLlama endpoints do not document start/end parameters and may return their full chart; the pipeline filters the requested window locally and avoids rewriting previously stored dates."]
    if metric == "near_intents_net_revenue":
        limitations.append("A distinct Front-end Affiliate Revenue / Other Revenue daily split was not present in the retrieved payload.")
    if metric == "near_intents_holders_revenue_buyback":
        limitations.append("USD series only; no NEAR-denominated quantity was present in the normalized daily chart.")
    if metric == "near_intents_tvl":
        limitations.append("Total and each chain are validated as separate series; not interchangeable or additive to total.")
    return validate(metric, path, rows, endpoint, contract.unit, error, limitations, series_by_id=True)
