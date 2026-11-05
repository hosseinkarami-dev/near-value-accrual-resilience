"""Stable identifiers and file locations for normalized datasets."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetContract:
    key: str
    filename: str
    source: str
    unit: str
    collection: str = "observations"


DATASETS = {
    "near_daily_price": DatasetContract("near_daily_price", "network/daily_token_price.json", "Binance Spot", "USDT"),
    "near_daily_total_supply": DatasetContract("near_daily_total_supply", "network/daily_total_supply.json", "BigQuery", "NEAR"),
    "near_daily_user_activity_cohorts": DatasetContract("near_daily_user_activity_cohorts", "network/daily_user_activity_cohorts.json", "BigQuery", "mixed"),
    "near_intents_tvl": DatasetContract("near_intents_tvl", "near_intents/historical_tvl.json", "DeFiLlama", "USD", "series"),
    "near_intents_dex_volume": DatasetContract("near_intents_dex_volume", "near_intents/daily_dex_trading_volume.json", "DeFiLlama", "USD"),
    "near_intents_gross_fees": DatasetContract("near_intents_gross_fees", "near_intents/daily_gross_fees.json", "DeFiLlama", "USD"),
    "near_intents_net_revenue": DatasetContract("near_intents_net_revenue", "near_intents/daily_net_revenue.json", "DeFiLlama", "USD"),
    "near_intents_holders_revenue_buyback": DatasetContract("near_intents_holders_revenue_buyback", "near_intents/daily_holders_revenue_buyback.json", "DeFiLlama", "USD"),
    "near_network_dex_volume": DatasetContract("near_network_dex_volume", "network/daily_dex_trading_volume.json", "DeFiLlama", "USD"),
    "near_network_fees": DatasetContract("near_network_fees", "network/daily_revenue_fees.json", "DeFiLlama", "USD"),
    "near_network_historical_tvl": DatasetContract("near_network_historical_tvl", "network/historical_tvl.json", "DeFiLlama", "USD"),
    "near_network_stablecoin_supply": DatasetContract("near_network_stablecoin_supply", "network/daily_stablecoin_supply.json", "DeFiLlama", "USD"),
}


def validate_document(contract: DatasetContract, document: dict) -> None:
    """Check the stable dataset envelope without changing provider-specific fields."""
    required = {"dataset", "unit", "source_endpoint", "methodology", "updated_at", contract.collection}
    missing = sorted(required - document.keys())
    if missing:
        raise ValueError(f"{contract.key}: normalized document is missing {', '.join(missing)}")
    if document["dataset"] != contract.key:
        raise ValueError(f"{contract.key}: document dataset id does not match contract")
    if document["unit"] != contract.unit:
        raise ValueError(f"{contract.key}: document unit does not match contract")
