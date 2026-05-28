"""
app/db/models.py
----------------
Database table definitions for the application.

Each class here maps directly to a table in PostgreSQL.
SQLModel combines SQLAlchemy (database ORM) with Pydantic (data validation),
so these classes serve two purposes at once:
  1. Define the database schema (columns, types, constraints)
  2. Validate data when creating or reading objects in Python

Tables:
  - User: people who interact with the bot
  - Alert: reminders and condition-based alerts created by users
"""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import BigInteger
import json


class User(SQLModel, table=True):
    """
    Represents a Telegram user who has interacted with the bot.

    Created automatically the first time someone writes to the bot.
    We store telegram_id (not username) as the unique identifier because
    usernames can change, but Telegram IDs never do.
    """

    # table=True tells SQLModel to create a real PostgreSQL table for this class
    id: Optional[int] = Field(default=None, primary_key=True)

    # BigInteger is required because modern Telegram IDs exceed the max value
    # of a regular Integer (2,147,483,647). Learned this the hard way in development.
    telegram_id: int = Field(
        sa_column=Column(BigInteger, unique=True, index=True)
        # unique=True: no two users can have the same telegram_id
        # index=True: speeds up lookups by telegram_id (we do this on every message)
    )

    username: Optional[str] = None  # Telegram username, can be null if user hasn't set one

    # always store UTC, never local time — avoids timezone confusion across servers
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Alert(SQLModel, table=True):
    """
    Represents an alert or reminder created by a user.

    Supports two fundamentally different types of alerts:
      - Scheduled: fire at a specific date/time ("el martes a las 10")
      - Condition-based: fire when something in the world changes
        ("cuando Bitcoin baje de 80.000€")

    The alert_type field determines which logic the scheduler uses
    when evaluating whether to send the notification.
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign key linking this alert to its owner in the user table
    # Same concept as a FK in SQL — each alert belongs to exactly one user
    user_id: int = Field(foreign_key="user.id")

    message: str  # Human-readable description shown in the notification

    # Determines how the scheduler evaluates this alert:
    # "scheduled" | "crypto" | "currency" | "release"
    alert_type: str = Field(default="scheduled")

    # Only used for scheduled alerts — None for condition-based alerts
    scheduled_at: Optional[datetime] = None

    # Stores the condition parameters as a JSON string.
    # We use a string instead of a proper JSON column for simplicity —
    # get_condition() and set_condition() handle serialization.
    #
    # Examples of what gets stored here:
    #   crypto:   '{"coin": "bitcoin", "currency": "eur", "threshold": 80000, "direction": "below"}'
    #   currency: '{"from": "USD", "to": "EUR", "threshold": 0.95, "direction": "above"}'
    #   release:  '{"query": "Severance temporada 3", "media_type": "tv"}'
    condition_config: Optional[str] = Field(default=None)

    # False until the notification is sent — the scheduler filters on this field
    # to find pending alerts. Once True, the alert is never evaluated again.
    sent: bool = Field(default=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def get_condition(self) -> Optional[dict]:
        """
        Returns the condition parameters as a Python dict.
        Returns None if this is a scheduled alert (no condition config).
        """
        if self.condition_config:
            return json.loads(self.condition_config)
        return None

    def set_condition(self, config: dict):
        """
        Stores the condition parameters dict as a JSON string.
        Called when creating a new condition-based alert.
        """
        self.condition_config = json.dumps(config)