"""Convert Binance raw kline arrays to the persisted daily candle contract."""
from datetime import datetime, timezone
from src.normalize.common import START_DATE, dec


def normalize_klines(candles, retrieved_at, today):
    observations = []
    today_start = datetime.combine(today, datetime.min.time(), timezone.utc)
    for candle in candles:
        opened = datetime.fromtimestamp(int(candle[0]) / 1000, timezone.utc)
        closed = datetime.fromtimestamp(int(candle[6]) / 1000, timezone.utc)
        day = opened.date()
        if day < START_DATE or day >= today:
            continue
        values = [dec(candle[i]) for i in (1, 2, 3, 4, 5, 7, 9, 10)]
        if any(value is None for value in values):
            continue
        op, high, low, close, base, quote, taker_base, taker_quote = values
        observations.append({"date": day.isoformat(), "timestamp": int(candle[0]), "close_timestamp": int(candle[6]), "metric": "near_usdt_daily_candle", "unit": "USDT", "open": op, "high": high, "low": low, "close": close, "base_asset_volume_near": base, "quote_asset_volume_usdt": quote, "number_of_trades": int(candle[8]), "taker_buy_base_asset_volume_near": taker_base, "taker_buy_quote_asset_volume_usdt": taker_quote, "retrieved_at": retrieved_at, "is_final": closed < today_start})
    return observations
