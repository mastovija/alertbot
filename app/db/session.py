from sqlmodel import create_engine, Session
from app.core.config import settings

# echo=True logs every SQL query to the terminal — useful for development,
# remove in production
engine = create_engine(
    settings.database_url,
    echo=True,
)


def get_session():
    # yield (instead of return) ensures the session is always closed
    # after use, even if an error occurs
    with Session(engine) as session:
        yield session