# BigQuery query templates

- `daily_total_supply.sql` returns the daily supply snapshot.
- `daily_user_activity_cohorts.sql` directly aggregates transaction counts, distinct active users, new/old/returning users, and cohort retention for inspection in BigQuery.
- `daily_user_activity_by_signer.sql` is the bounded source query used by the incremental updater; it returns one `signer_account_id` per day.

All templates take `start_date` and exclusive `end_date` values and filter on `block_date`.
The direct cohort query reads transaction hashes only for the requested date range. It separately
scans signer/date history from NEAR MainNet genesis (2020-04-22) to classify new/old/returning
users and calculate complete cohort sizes. This history scan is still broad. The current updater
persists first-seen state at `data/state/near_user_first_activity.json`, but scopes it to its
configured analysis start date; it is not yet a lifetime MainNet checkpoint.
Output rows have grain `activity_date + cohort_date`, so daily totals repeat for each cohort
active on a date.
