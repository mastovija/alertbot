from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import BigInteger


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # BigInteger supports values up to 9,223,372,036,854,775,807
    # Regular Integer max is only 2,147,483,647 — too small for modern Telegram IDs
    telegram_id: int = Field(
        sa_column=Column(BigInteger, unique=True, index=True)
    )
    username: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
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