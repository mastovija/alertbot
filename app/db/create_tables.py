from sqlmodel import SQLModel
from app.db.session import engine
from app.db import models  # noqa: F401 — importing models registers them with SQLModel
                            # without this, create_all() wouldn't know they exist


def create_tables():
    # Creates all tables that don't exist yet — safe to run multiple times
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    create_tables()
    print("Tables created successfully")