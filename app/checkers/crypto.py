"""
app/checkers/crypto.py
----------------------
Checker for cryptocurrency price alerts.

Uses the CoinGecko public API to fetch real-time crypto prices.
CoinGecko was chosen because:
  - Completely free, no API key required
  - Reliable and well-maintained
  - Supports hundreds of coins and fiat currencies
  - Simple REST API with clear documentation

API docs: https://www.coingecko.com/en/api/documentation
"""

import httpx


def check_crypto_price(coin: str, currency: str, threshold: float, direction: str) -> tuple[bool, float]:
    """
    Fetches the current price of a cryptocurrency and checks if it meets the condition.

    Args:
        coin: CoinGecko coin id e.g. "bitcoin", "ethereum", "solana"
              Full list at: https://api.coingecko.com/api/v3/coins/list
        currency: fiat currency code e.g. "eur", "usd", "gbp"
        threshold: the price to compare against e.g. 80000
        direction: "above" (price >= threshold) or "below" (price <= threshold)

    Returns:
        A tuple of (condition_met, current_price)
        condition_met is True if the alert should be fired

    Example:
        met, price = check_crypto_price("bitcoin", "eur", 80000, "below")
        # Returns (True, 63000.0) if BTC is currently below 80,000€
    """
    url = "https://api.coingecko.com/api/v3/simple/price"

    # 'ids' is the coin, 'vs_currencies' is the fiat currency to get the price in
    params = {"ids": coin, "vs_currencies": currency}

    response = httpx.get(url, params=params, timeout=10)
    response.raise_for_status()  # raises an exception if the request failed (4xx, 5xx)

    # Response format: {"bitcoin": {"eur": 63000}}
    data = response.json()
    current_price = data[coin][currency]

    if direction == "above":
        condition_met = current_price >= threshold
    else:
        condition_met = current_price <= threshold

    return condition_met, current_price