import os

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine

load_dotenv()

PG_VARIABLES = ["PG_HOST", "PG_PORT", "PG_DB", "PG_USER", "PG_PASSWORD"]


def get_engine() -> Engine:
    """SQLAlchemy engine for the project database, built from .env."""
    missing = [var for var in PG_VARIABLES if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing in .env: {', '.join(missing)}")

    url = URL.create(
        "postgresql+psycopg",
        username=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        host=os.getenv("PG_HOST"),
        port=int(os.getenv("PG_PORT")),
        database=os.getenv("PG_DB"),
    )
    return create_engine(url)