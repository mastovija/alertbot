"""
app/db/session.py
-----------------
Database connection and session management.

This module creates the SQLAlchemy engine (the connection to PostgreSQL)
and provides a session factory used throughout the app to read and write data.

Why sessions?
A session is like a "unit of work" with the database — you open it, make
changes, and either commit (save) or rollback (discard) at the end.
SQLModel handles this automatically when using 'with Session(engine)'.
"""

from sqlmodel import create_engine, Session
from app.core.config import settings

# The engine is the actual connection to PostgreSQL.
# It's created once at startup and reused — creating a new connection
# for every query would be slow and wasteful.
# echo=True logs every SQL query to the terminal, useful for development.
# Set to False in production to avoid cluttering logs.
engine = create_engine(
    settings.database_url,
    echo=True,
)


def get_session():
    """
    Provides a database session for use in FastAPI endpoints.

    Uses 'yield' instead of 'return' so the session stays open while
    the endpoint runs, then closes automatically when it finishes —
    even if an error occurs. This is called a context manager pattern.

    Usage in a FastAPI route:
        def my_route(session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session