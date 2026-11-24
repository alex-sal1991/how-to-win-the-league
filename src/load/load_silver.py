from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.utils.db import get_engine

ROOT = Path(__file__).resolve().parents[2]
SILVER = ROOT / "data" / "silver"

# table name in the silver schema -> parquet file in data/silver
SILVER_TABLES = {
    "matches": "matches.parquet",
    # "matches_statsapi": "matches_statsapi.parquet",   # add once the StatsAPI silver step exists
}


def load_table(table: str, filename: str) -> None:
    df = pd.read_parquet(SILVER / filename)
    engine = get_engine()

    df.to_sql(table, engine, schema="silver", if_exists="replace",
              index=False, chunksize=1000, method="multi")

    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE silver.{table} ADD PRIMARY KEY (match_id)"))
        n = conn.execute(text(f"SELECT COUNT(*) FROM silver.{table}")).scalar()

    print(f"silver.{table}: {n} rows loaded (parquet had {len(df)})")


def load_silver() -> None:
    for table, filename in SILVER_TABLES.items():
        load_table(table, filename)


if __name__ == "__main__":
    load_silver()