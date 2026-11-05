"""Shared all-time and current-snapshot JSON document."""
from src.normalize.common import iso_now
from src.storage.json_store import DATA_DIR, load_json, write_json

ALL_TIME_PATH = DATA_DIR / "all_time_metrics.json"


def save_metric(section, key, value, unit, endpoint, methodology, source="DeFiLlama"):
    if value is None:
        return
    document = load_json(ALL_TIME_PATH, {
        "dataset": "near_all_time_metrics",
        "unit": "mixed",
        "methodology": "Cumulative flow metrics and current stock snapshots are grouped by source domain.",
        "near_intents": {},
        "network": {},
    })
    document.setdefault(section, {})[key] = {
        "value": value,
        "unit": unit,
        "source": source,
        "source_endpoint": endpoint,
        "methodology": methodology,
        "updated_at": iso_now(),
    }
    document["updated_at"] = iso_now()
    write_json(ALL_TIME_PATH, document)
