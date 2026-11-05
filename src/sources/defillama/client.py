"""DeFiLlama HTTP source adapter."""
from typing import Any
from src.sources.http_json import fetch_json

BASE = "https://api.llama.fi"
ENDPOINTS = {
    "near_intents_tvl": f"{BASE}/protocol/near-intents",
    "near_intents_dex_volume": f"{BASE}/summary/dexs/near-intents",
    "near_intents_gross_fees": f"{BASE}/summary/fees/near-intents?dataType=dailyFees",
    "near_intents_net_revenue": f"{BASE}/summary/fees/near-intents?dataType=dailyRevenue",
    "near_intents_holders_revenue_buyback": f"{BASE}/summary/fees/near-intents?dataType=dailyHoldersRevenue",
}

NETWORK_ENDPOINTS = {
    "near_network_dex_volume": f"{BASE}/overview/dexs/Near",
    "near_network_fees": f"{BASE}/overview/fees/Near?dataType=dailyFees",
    "near_network_historical_tvl": f"{BASE}/v2/historicalChainTvl/Near",
    "near_network_stablecoin_supply": "https://stablecoins.llama.fi/stablecoincharts/Near",
    "near_network_current_chains": f"{BASE}/v2/chains",
    "near_network_current_stablecoins": "https://stablecoins.llama.fi/stablecoinchains",
}


def endpoint_for(metric: str) -> str:
    return ENDPOINTS[metric] if metric in ENDPOINTS else NETWORK_ENDPOINTS[metric]


def fetch_payload(endpoint: str) -> Any:
    """Retrieve an unmodified JSON payload; normalization belongs in src.normalize."""
    return fetch_json(endpoint)
