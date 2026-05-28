"""
app/bot/parser.py
-----------------
Natural language parser powered by Claude API.

This is the "brain" of the bot — it takes a free-text message from the user
and converts it into structured data that the rest of the system can work with.

Without this module, users would need to fill in forms or use rigid commands
like "/alert crypto bitcoin below 80000". With it, they can just write
"avísame cuando Bitcoin baje de 80.000€" in any language.

Flow:
  user text → Claude API → structured JSON → Alert object in the database
"""

from datetime import datetime, timezone
from anthropic import Anthropic
from app.core.config import settings

# Single Anthropic client instance, reused across all calls
client = Anthropic(api_key=settings.anthropic_api_key)

# The system prompt defines Claude's role and the exact output format we expect.
# Key design decisions:
#   - We inject today's date so Claude can interpret "mañana" or "el martes"
#   - We demand JSON-only output to make parsing reliable
#   - We define all 4 alert types with concrete examples so Claude classifies correctly
#   - Double curly braces {{ }} are Python's way of escaping { } inside f-strings
SYSTEM_PROMPT = """You are a reminder and alert parsing assistant.
The user will send a message in any language describing an alert they want to set.
Your job is to classify the alert and extract its parameters.

Today's date and time is: {now}

There are 4 types of alerts:

1. "scheduled" - a reminder at a specific date/time
   Example: "el martes a las 10 llamar al médico"
   
2. "crypto" - alert when a cryptocurrency reaches a price
   Example: "avísame cuando Bitcoin baje de 80000 euros"
   Coins: bitcoin, ethereum, solana, cardano, dogecoin, etc.
   
3. "currency" - alert when an exchange rate crosses a threshold
   Example: "avísame cuando el dólar esté por encima de 0.95 euros"
   
4. "release" - alert when a movie or TV show is released
   Example: "avísame cuando estrene la temporada 3 de Severance"
   media_type must be "movie" or "tv"

You must respond with ONLY a JSON object, no explanation, no markdown.

For "scheduled":
{{"alert_type": "scheduled", "scheduled_at": "2026-01-15T09:00:00", "message": "Llamar al médico"}}

For "crypto":
{{"alert_type": "crypto", "message": "Bitcoin bajo de 80000€", "condition": {{"coin": "bitcoin", "currency": "eur", "threshold": 80000, "direction": "below"}}}}

For "currency":
{{"alert_type": "currency", "message": "Dólar sobre 0.95€", "condition": {{"from": "USD", "to": "EUR", "threshold": 0.95, "direction": "above"}}}}

For "release":
{{"alert_type": "release", "message": "Severance temporada 3", "condition": {{"query": "Severance temporada 3", "media_type": "tv"}}}}

Rules:
- scheduled_at must be ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
- If no time is specified for scheduled alerts, default to 09:00
- message should be in the same language the user wrote in
- For crypto, use CoinGecko coin ids (bitcoin, ethereum, solana...)
- For currency, use 3-letter codes (USD, EUR, GBP...)
- If you cannot parse the alert, return: {{"error": "Could not parse alert"}}
"""


def parse_alert(user_text: str) -> dict:
    """
    Converts a free-text message into a structured alert definition.

    Calls the Claude API with a carefully crafted system prompt that instructs
    it to return JSON only. The response is then parsed and returned as a dict.

    Args:
        user_text: the raw message from the Telegram user

    Returns:
        A dict with 'alert_type' and type-specific fields, for example:
          {'alert_type': 'crypto', 'message': '...', 'condition': {...}}
        Or on failure:
          {'error': 'Could not parse alert'}
    """
    # Inject current UTC time so Claude can resolve relative dates
    # like "mañana", "el martes", "en 2 horas"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,  # JSON responses are short — capping tokens controls cost
        system=SYSTEM_PROMPT.format(now=now),
        messages=[
            {"role": "user", "content": user_text}
        ],
    )

    raw = response.content[0].text.strip()

    # LLMs sometimes wrap JSON in markdown code blocks (```json ... ```)
    # despite being told not to. This strips those wrappers defensively.
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        import json
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": f"Could not parse response: {raw}"}