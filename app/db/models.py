from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    # table=True tells SQLModel this class maps to a real PostgreSQL table
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(unique=True, index=True)  # index speeds up lookups by telegram_id
    username: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)  # always store UTC, never local time
    )


class Alert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")  # links each alert to its owner
    message: str
    scheduled_at: datetime   # when the alert should be sent
    sent: bool = Field(default=False)  # False until the scheduler fires it
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )