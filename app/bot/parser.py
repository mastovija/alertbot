from datetime import datetime, timezone
from anthropic import Anthropic
from app.core.config import settings

client = Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are a reminder parsing assistant. 
The user will send a message in any language describing a reminder they want to set.
Your job is to extract two things:
1. The exact datetime when the reminder should be sent
2. The reminder message to send the user

Today's date and time is: {now}

You must respond with ONLY a JSON object, no explanation, no markdown, exactly like this:
{{
    "scheduled_at": "2026-01-15T09:00:00",
    "message": "Call the doctor"
}}

Rules:
- scheduled_at must be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
- If no time is specified, default to 09:00
- If no date is specified, assume tomorrow
- message should be in the same language the user wrote in
- If you cannot parse a reminder from the message, return: {{"error": "Could not parse reminder"}}
"""


def parse_reminder(user_text: str) -> dict:
    """
    Calls Claude API to extract structured reminder data from natural language.
    Returns a dict with 'scheduled_at' and 'message', or 'error' if parsing fails.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=SYSTEM_PROMPT.format(now=now),
        messages=[
            {"role": "user", "content": user_text}
        ],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code blocks if the model returns them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        import json
        result = json.loads(raw)
        return result
    except json.JSONDecodeError:
        return {"error": f"Could not parse response: {raw}"}