"""Registered source families. RPC is a selectable integration point, pending adapter implementation."""
from __future__ import annotations

def available_sources() -> dict[str, list[str]]:
    return {
        "defillama": ["near_intents", "near_network_dex_volume", "near_network_fees", "near_network_tvl", "near_stablecoin_supply"],
        "bigquery": ["daily_total_supply", "daily_user_activity_cohorts"],
        "binance": ["token_price"],
        "rpc": [],
    }


def select_sources(names: list[str] | None) -> list[str]:
    supported = available_sources()
    selected = names or [name for name, datasets in supported.items() if datasets]
    unknown = sorted(set(selected) - set(supported))
    if unknown:
        raise ValueError("Unknown source(s): " + ", ".join(unknown))
    return selected
