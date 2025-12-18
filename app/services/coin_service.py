"""Service for retrieving market data from external APIs with caching."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

import requests
from flask import current_app

_CACHE: Dict[str, Tuple[float, dict[str, Any]]] = {}


def _should_use_cache(key: str, timeout: int) -> bool:
    if key not in _CACHE:
        return False
    timestamp, _ = _CACHE[key]
    return time.time() - timestamp < timeout


def fetch_market_data(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Fetch price data for configured coins from CoinGecko with caching."""
    config = current_app.config
    cache_key = "market_data"
    timeout = config.get("CACHE_TIMEOUT", 300)
    if not force_refresh and _should_use_cache(cache_key, timeout):
        return _CACHE[cache_key][1]

    if force_refresh:
        _CACHE.pop(cache_key, None)

    coins = config.get("MARKET_COINS", "bitcoin,ethereum")
    currency = config.get("PREFERRED_CURRENCY", "usd")
    params = {
        "vs_currency": currency,
        "ids": coins,
        "order": "market_cap_desc",
        "per_page": len(coins.split(",")),
        "page": 1,
        "sparkline": "true",
        "price_change_percentage": "1h,24h,7d",
    }

    try:
        response = requests.get(
            f"{config['COINGECKO_API_URL']}/coins/markets",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        _CACHE[cache_key] = (time.time(), data)
        return data
    except requests.RequestException:
        if cache_key in _CACHE:
            return _CACHE[cache_key][1]
        return []

def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_market_payload(
    raw_data: list[dict[str, Any]], *, fetched_at: datetime | None = None
) -> dict[str, Any]:
    """Prepare market data payload for frontend consumption."""
    observed_at = fetched_at or datetime.now(timezone.utc)
    tickers = []
    chart_data = {}
    for coin in raw_data:
        price_change = coin.get("price_change_percentage_24h", 0)
        trend = "up" if price_change >= 0 else "down"
        tickers.append(
            {
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name"),
                "current_price": coin.get("current_price"),
                "price_change_percentage_24h": price_change,
                "trend": trend,
            }
        )

        raw_prices = coin.get("sparkline_in_7d", {}).get("price", [])
        prices = list(raw_prices[-288:]) if raw_prices else []
        current_price = coin.get("current_price")
        if prices:
            if current_price is not None:
                prices[-1] = current_price
        elif current_price is not None:
            prices = [current_price]

        last_observed = _parse_timestamp(coin.get("last_updated")) or observed_at
        if last_observed < observed_at:
            last_observed = observed_at

        symbol = coin.get("symbol", "").upper()
        chart_data[symbol] = {
            "prices": prices,
            "last_updated": last_observed.isoformat(),
            "interval_minutes": 5,
        }

    return {"tickers": tickers, "chart_data": chart_data}


def fetch_global_metrics() -> dict[str, Any]:
    """Return global market metrics with caching."""
    cache_key = "global_metrics"
    timeout = current_app.config.get("CACHE_TIMEOUT", 300)
    if _should_use_cache(cache_key, timeout):
        return _CACHE[cache_key][1]

    try:
        response = requests.get(
            f"{current_app.config['COINGECKO_API_URL']}/global",
            timeout=10,
        )
        response.raise_for_status()
        data = response.json().get('data', {})
        _CACHE[cache_key] = (time.time(), data)
        return data
    except requests.RequestException:
        return _CACHE.get(cache_key, (0, {}))[1]


def get_price_for_symbol(symbol: str, *, force_refresh: bool = False) -> float | None:
    """Return the current price for a specific symbol, optionally forcing a refresh."""
    symbol = symbol.upper()
    for coin in fetch_market_data(force_refresh=force_refresh):
        if coin.get("symbol", "").upper() == symbol:
            price = coin.get("current_price")
            return float(price) if price is not None else None
    return None


def build_price_lookup(force_refresh: bool = False) -> dict[str, float]:
    """Return a mapping of symbol to current price."""
    lookup: dict[str, float] = {}
    for entry in fetch_market_data(force_refresh=force_refresh):
        symbol = entry.get("symbol")
        price = entry.get("current_price")
        if symbol and price is not None:
            lookup[symbol.upper()] = float(price)
    return lookup
