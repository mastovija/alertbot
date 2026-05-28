"""
app/checkers/currency.py
------------------------
Checker for currency exchange rate alerts.

Uses the ExchangeRate API (open.er-api.com) to fetch real-time exchange rates.
Chosen because:
  - Free tier with no API key required
  - Updated every 24 hours — sufficient for exchange rate alerts
  - Simple and reliable REST API

API docs: https://www.exchangerate-api.com/docs/free
"""

import httpx


def check_currency_rate(from_currency: str, to_currency: str, threshold: float, direction: str) -> tuple[bool, float]:
    """
    Fetches the current exchange rate between two currencies and checks the condition.

    Args:
        from_currency: base currency code e.g. "USD", "GBP"
        to_currency: target currency code e.g. "EUR", "JPY"
        threshold: the rate to compare against e.g. 0.95
        direction: "above" (rate >= threshold) or "below" (rate <= threshold)

    Returns:
        A tuple of (condition_met, current_rate)
        condition_met is True if the alert should be fired

    Example:
        met, rate = check_currency_rate("USD", "EUR", 0.95, "above")
        # Returns (True, 0.98) if 1 USD currently buys more than 0.95 EUR
    """
    # The API returns all rates relative to the base currency in one call.
    # Cheaper than calling once per currency pair.
    url = f"https://open.er-api.com/v6/latest/{from_currency}"

    response = httpx.get(url, timeout=10)
    response.raise_for_status()

    # Response format: {"rates": {"EUR": 0.86, "GBP": 0.73, ...}}
    data = response.json()
    current_rate = data["rates"][to_currency]

    if direction == "above":
        condition_met = current_rate >= threshold
    else:
        condition_met = current_rate <= threshold

    return condition_met, current_rate