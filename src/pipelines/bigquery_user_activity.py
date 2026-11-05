"""Incremental NEAR activity/cohort pipeline backed by signer first-seen state."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from src.contracts.datasets import DATASETS, validate_document
from src.normalize.common import START_DATE
from src.normalize.user_activity import normalize_signer_activity_rows
from src.sources.bigquery.datasets.user_activity_cohorts import TABLE, fetch_daily_signer_activity
from src.storage.json_store import DATA_DIR, load_json, write_json

OVERLAP_DAYS = 2
STATE_PATH = DATA_DIR / "state" / "near_user_first_activity.json"


def _cohort_observations(activity_rows, first_activity_by_user):
    daily = defaultdict(lambda: {"transactions": 0, "active_users": 0, "new_users": 0, "old_users": 0})
    cohort_activity = Counter()
    for row in activity_rows:
        day, user_id = row["date"], row["user_id"]
        cohort_date = first_activity_by_user[user_id]
        totals = daily[day]
        totals["transactions"] += row["transaction_count"]
        totals["active_users"] += 1
        if cohort_date == day:
            totals["new_users"] += 1
        elif cohort_date < day:
            totals["old_users"] += 1
        cohort_activity[(day, cohort_date)] += 1

    cohort_sizes = Counter(first_activity_by_user.values())
    output = []
    for (day, cohort_date), retained_users in sorted(cohort_activity.items()):
        totals = daily[day]
        cohort_size = cohort_sizes[cohort_date]
        output.append({
            "date": day,
            "activity_date": day,
            **totals,
            "cohort_date": cohort_date,
            "cohort_age_days": (date.fromisoformat(day) - date.fromisoformat(cohort_date)).days,
            "cohort_size": cohort_size,
            "retained_users": retained_users,
            "retention_rate": Decimal(retained_users) / Decimal(cohort_size),
            "cohort_basis": "first_activity_since_analysis_start",
        })
    return output, cohort_sizes


def _merge_observations(old_rows, incoming, start, end, cohort_sizes):
    merged = {}
    for row in old_rows:
        day = row.get("date", "")
        if day and (day < start.isoformat() or day >= end.isoformat()):
            merged[(day, row.get("cohort_date", ""))] = row
    for row in incoming:
        merged[(row["date"], row["cohort_date"])] = row

    observations = []
    for key, row in merged.items():
        item = dict(row)
        size = cohort_sizes.get(item.get("cohort_date"), item.get("cohort_size", 0))
        if size:
            item["cohort_size"] = size
            item["retention_rate"] = Decimal(item["retained_users"]) / Decimal(size)
        observations.append(item)
    return sorted(observations, key=lambda row: (row["date"], row.get("cohort_date", "")))


def run(start_date=None):
    contract = DATASETS["near_daily_user_activity_cohorts"]
    today = datetime.now(timezone.utc).date()
    retrieved = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    path = DATA_DIR / contract.filename
    old_document = load_json(path, {"observations": []})
    old_rows = old_document.get("observations", []) if isinstance(old_document, dict) else []
    state = load_json(STATE_PATH, {})
    state = state if isinstance(state, dict) else {}
    first_activity_by_user = state.get("first_activity_by_user", {})
    analysis_start = date.fromisoformat(state["analysis_start_date"]) if state.get("analysis_start_date") else START_DATE

    if isinstance(start_date, str):
        start = date.fromisoformat(start_date)
        analysis_start = min(analysis_start, start) if first_activity_by_user else start
    elif isinstance(start_date, date):
        start = start_date
        analysis_start = min(analysis_start, start) if first_activity_by_user else start
    elif not first_activity_by_user:
        # A missing checkpoint requires a one-time historical bootstrap.
        start = analysis_start
    else:
        previous_dates = [date.fromisoformat(row["date"]) for row in old_rows if row.get("date")]
        latest = max(previous_dates, default=None)
        start = max(analysis_start, latest - timedelta(days=OVERLAP_DAYS)) if latest else analysis_start

    try:
        print(f"Cohort update: querying signer/day activity for [{start.isoformat()}, {today.isoformat()}) on block_date...", flush=True)
        raw_rows = fetch_daily_signer_activity(start.isoformat(), today.isoformat())
        print(f"Cohort update: BigQuery returned {len(raw_rows)} signer/day rows; preparing JSON...", flush=True)
        activity_rows = normalize_signer_activity_rows(raw_rows)
    except Exception as exc:
        return {
            "dataset": contract.key,
            "path": str(path.relative_to(path.parents[1])).replace("\\", "/"),
            "source": contract.source,
            "source_endpoint": TABLE,
            "status": "unavailable",
            "retrieval_error": str(exc),
        }

    for row in activity_rows:
        user_id, day = row["user_id"], row["date"]
        prior = first_activity_by_user.get(user_id)
        if prior is None or day < prior:
            first_activity_by_user[user_id] = day

    incoming, cohort_sizes = _cohort_observations(activity_rows, first_activity_by_user)
    observations = _merge_observations(old_rows, incoming, start, today, cohort_sizes)
    updated_state = {
        "dataset": "near_user_first_activity_state",
        "analysis_start_date": analysis_start.isoformat(),
        "updated_at": retrieved,
        "first_activity_by_user": first_activity_by_user,
    }
    document = {
        "dataset": contract.key,
        "unit": contract.unit,
        "source": contract.source,
        "source_endpoint": TABLE,
        "methodology": "One row per activity date and observed cohort. Transactions count transaction rows; active users are distinct signers. New users are first observed since the configured analysis start; old users have an earlier observed activity. Retention is retained cohort users divided by cohort size. Missing cohort/date combinations represent zero retained users.",
        "row_grain": "activity_date_and_cohort_date",
        "daily_metrics_repeat_for_each_cohort_on_the_same_date": True,
        "cohort_basis": "first_activity_since_analysis_start",
        "analysis_start_date": analysis_start.isoformat(),
        "updated_at": retrieved,
        "observations": observations,
    }
    validate_document(contract, document)
    print(f"Cohort update: writing {len(observations)} cohort rows and {len(first_activity_by_user)} account checkpoints...", flush=True)
    write_json(STATE_PATH, updated_state)
    write_json(path, document)
    return {
        "dataset": contract.key,
        "path": str(path.relative_to(path.parents[1])).replace("\\", "/"),
        "source": contract.source,
        "source_endpoint": TABLE,
        "observation_count": len(observations),
        "active_accounts_tracked": len(first_activity_by_user),
        "queried_start_date": start.isoformat(),
        "queried_end_date_exclusive": today.isoformat(),
        "status": "retrieved" if observations else "no_observations",
    }
