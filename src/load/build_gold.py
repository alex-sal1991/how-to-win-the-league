from pathlib import Path

from sqlalchemy import text

from src.utils.db import get_engine

ROOT = Path(__file__).resolve().parents[2]
GOLD_SQL = ROOT / "sql" / "gold"


def build_gold() -> None:
    engine = get_engine()
    for sql_file in sorted(GOLD_SQL.glob("*.sql")):        # 01_..., 02_... run in order
        with engine.begin() as conn:
            conn.exec_driver_sql(sql_file.read_text(encoding="utf-8"))
        table = sql_file.stem.split("_", 1)[1]             # "01_team_match" -> "team_match"
        with engine.connect() as conn:
            n = conn.execute(text(f"SELECT COUNT(*) FROM gold.{table}")).scalar()
        print(f"{sql_file.name}: gold.{table} = {n} rows")


if __name__ == "__main__":
    build_gold()