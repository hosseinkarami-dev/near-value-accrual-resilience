# NEAR historical data extraction

This repository retrieves source observations and writes normalized daily JSON datasets. It does not generate reports.

## Run

From the repository root:

- `python scripts/update_all.py` updates every implemented source family.
- `python scripts/update_all.py --source defillama` updates DeFiLlama NEAR Intents and network datasets.
- `python scripts/update_all.py --source bigquery` updates the daily supply series.
- `python scripts/update_all.py --source binance` updates the NEAR/USDT price series.
- Repeat `--source` to update more than one family.

To run one dataset on its own, use its provider folder directly, for example:

- `python scripts/sources/defillama/tvl.py`
- `python scripts/sources/defillama/net_revenue.py`
- `python scripts/sources/defillama/network_metrics.py`
- `python scripts/sources/binance/token_price.py`
- `python scripts/sources/bigquery/daily_total_supply.py`
- Add `--start-date YYYY-MM-DD` to that BigQuery command to set a backfill start. Without it, the command starts two days before the latest saved date and keeps earlier stored history.
- `python scripts/sources/bigquery/user_activity_cohorts.py` refreshes the transaction, user, and cohort dataset. `update_all.py --source bigquery` runs this alongside daily supply.
- The cohort updater bootstraps its selected date window once (default starts `2025-05-10`), saves first-activity state under `data/state/`, and then re-queries only the latest date with a two-day overlap. It filters on `block_date` and replaces overlapping JSON rows instead of duplicating them.

DeFiLlama historical files are grouped under `data/near_intents/` and `data/network/`; cumulative and current snapshot values share `data/all_time_metrics.json`. Historical updates begin at `latest stored date + 1` (or `2025-05-10` for a first run) and stop before the current UTC date. Some free DeFiLlama endpoints return the full chart even when date parameters are supplied; those responses are filtered locally and existing dates are preserved. Current snapshots and cumulative values are refreshed each run. A failed retrieval leaves the last successful dataset intact.

## Architecture

The data path is **source adapter → normalizer → dataset pipeline → storage**:

- `src/sources/` retrieves raw payloads. Providers are grouped by family: `defillama/`, `binance/`, `bigquery/`, and the reserved `rpc/` integration point. BigQuery's `client.py` handles generic query execution; dataset adapters live in `bigquery/datasets/`, with SQL templates in `bigquery/queries/` loaded at runtime.
- `src/normalize/` converts provider payloads to the dataset shape and applies UTC/date and numeric rules. Normalizers do not make network requests or write files.
- `src/contracts/datasets.py` is the central catalog of dataset identifiers, filenames, source names, units, and the expected top-level collection (`observations` or `series`). Pipelines validate this envelope before saving it; existing dataset-specific fields remain intact.
- `src/pipelines/` coordinates retrieval, normalization, validation, and upserts.
- `src/storage/` handles atomic JSON writes and historical row merging.
- `scripts/sources/` groups dataset-specific commands by provider; each command can run by itself. `scripts/update_all.py` is the family-level runner.
- `data/near_intents/` contains protocol-level NEAR Intents histories.
- `data/network/` contains chain-level NEAR histories and other network datasets.
- `data/all_time_metrics.json` contains cumulative flow values and current network snapshots.

Binance, DeFiLlama, and BigQuery have working adapters. The RPC folder is an extension point only; an RPC source and its dataset still need to be specified and implemented.

## Data rules

Dates use UTC, missing observations remain missing, and TVL, DEX volume, gross fees, net revenue, holders revenue, and network fees remain separate measures. NEAR network fees are fees paid by users, not protocol revenue or token burn. The public BigQuery `blocks.total_supply` column is `FLOAT64`, so its normalized values are explicitly marked approximate.
