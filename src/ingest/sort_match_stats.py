"""Copy StatsAPI match-stats files from a flat dump folder into bronze, by league and season.

Uses the saved match lists (data/bronze/statsapi/<league>/<league>_matches_*.json) to work out
which league and season each match_id belongs to. Files for other competitions (Eredivisie,
Süper Lig, ...) are left behind. Copies rather than moves, so the dump is untouched.

Run from the project folder:
    python -m src.ingest.sort_match_stats "C:\\path\\to\\match_stats"
"""
import shutil
import sys
from pathlib import Path

from src.utils.helper_io import read_json

ROOT = Path(__file__).resolve().parents[2]
STATS_API_BRONZE = ROOT / "data" / "bronze" / "statsapi"
LEAGUES_TO_SORT = ["liga_portugal", "belgian_pro"]


def sort_match_stats(source: Path) -> None:
    dump = {f.stem: f for f in source.glob("*.json")}
    print(f"{len(dump)} files in {source}\n")

    for league in LEAGUES_TO_SORT:
        league_folder = STATS_API_BRONZE / league
        for match_list in sorted(league_folder.glob(f"{league}_matches_*.json")):
            data = read_json(match_list)
            label = str(data["season"]["start_year"])
            ids = [m["id"] for m in data["matches"] if m["status"] == "finished"]

            out_folder = league_folder / "match_stats" / label
            out_folder.mkdir(parents=True, exist_ok=True)

            copied = already = 0
            missing = []
            for match_id in ids:
                target = out_folder / f"{match_id}.json"
                if target.exists():
                    already += 1
                elif match_id in dump:
                    shutil.copy2(dump[match_id], target)
                    copied += 1
                else:
                    missing.append(match_id)

            print(f"{league} {label} ({data['season']['name']}): {len(ids)} listed | "
                  f"{copied} copied | {already} already there | {len(missing)} missing")
            if missing:
                print(f"    missing: {', '.join(missing)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('Usage: python -m src.ingest.sort_match_stats "<path to match_stats folder>"')
    sort_match_stats(Path(sys.argv[1]))