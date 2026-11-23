import requests
import json
import os
import time
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from src.utils.helper_io import read_json, save_as_json, latest_json
from src.config import STATSAPI_LEAGUES

load_dotenv()
API_KEY = os.getenv("STATS_API_KEY")
if not API_KEY:
    raise ValueError("STATS_API_KEY is missing or empty")

BASE_URL = "https://api.thestatsapi.com/api/football"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

RETRY_STATUSES = {429, 500, 502, 503, 504}
BRONZE = Path(__file__).resolve().parents[2] / "data" / "bronze"
STATS_API_BRONZE = BRONZE / "statsapi"
REQUEST_PAUSE = 1.1

class QuotaExceeded(Exception):
    """The trial/monthly request quota is used up; retrying won't help."""


QUOTA = {"remaining": None}   # updated after every successful call

def pull_json(endpoint: str, max_retries=3, params=None):
    url = f"{BASE_URL}/{endpoint}"

    for attempt in range(1, max_retries + 1):
        wait = 2 ** attempt

        try:    
            response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"[{attempt}/{max_retries}] network error {endpoint}: {e}; retrying in {wait} seconds")
            time.sleep(wait)
            continue

        if response.status_code == 429 and "USAGE_LIMIT_EXCEEDED" in response.text:
            raise QuotaExceeded("Monthly/trial quota used up")    

        if response.status_code in RETRY_STATUSES:
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 65)) + 1
            print(f"[{attempt}/{max_retries}] HTTP {response.status_code} on {endpoint}; retrying in {wait}s")
            time.sleep(wait)
            continue

        response.raise_for_status()
        QUOTA["remaining"] = response.headers.get("X-Monthly-Quota-Remaining")
        time.sleep(REQUEST_PAUSE)  
        return response.json()

    raise RuntimeError(f"Stopped on {endpoint} after {max_retries} attempts")

def extract_all_competitions(endpoint: str) -> None:
    folder = STATS_API_BRONZE
    if latest_json(folder, prefix=f"competitions_*"):
        print(f"competitions already saved.")
        return
    
    all_competitions = []
    
    page = 1
    per_page = 100

    while True:
        params = {"page": page, "per_page": per_page}
        data = pull_json(endpoint, 3, params)

        if data["meta"]["page"] != page:
            raise ValueError(f"Requested page {page}, got {data['meta']['page']}")
        
        all_competitions.extend(data["data"])

        if page >= data["meta"]["total_pages"]:
            break

        page += 1
        time.sleep(3)

    save_as_json(folder, "competitions", all_competitions)
    return all_competitions

def extract_seasons() -> None:
    for league, competition_id in STATSAPI_LEAGUES.items():
        league_folder = STATS_API_BRONZE / league
        if latest_json(league_folder, prefix=f"{league}_seasons"):
            print(f"{league}: seasons already saved.")
            continue
        data = pull_json(f"competitions/{competition_id}/seasons")
        save_as_json(league_folder, f"{league}_seasons", data)

TARGET_START_YEARS = {2022, 2023}

def select_statsapi_seasons(league: str) -> list[dict]:
    """Seasons from the saved bronze file whose start_year is in TARGET_START_YEARS. No API calls."""
    file = latest_json(STATS_API_BRONZE / league, prefix=f"{league}_seasons")
    if file is None:
        raise FileNotFoundError(f"No seasons file for {league}; run extract_seasons() first")
    return [s for s in read_json(file)["data"] if s["start_year"] in TARGET_START_YEARS]

def extract_matches(dry_run: bool = False) -> None:
    """Save every match (all stages) for the target seasons: one bronze file per league-season."""
    for league, competition_id in STATSAPI_LEAGUES.items():
        league_folder = STATS_API_BRONZE / league

        for season in select_statsapi_seasons(league):
            season_id = season["id"]
            label = str(season["start_year"])               # "2022", "2023"
            prefix = f"{league}_matches_{label}"

            if dry_run:
                print(f"[dry run] {league} {season['name']} ({season_id}) -> {prefix}")
                continue
            if latest_json(league_folder, prefix=prefix):
                print(f"{league} {label}: matches already saved.")
                continue

            all_matches = []
            page, per_page = 1, 100
            while True:
                params = {"competition_id": competition_id, "season_id": season_id,
                          "stage": "all", "page": page, "per_page": per_page}
                data = pull_json("matches", params=params)
                all_matches.extend(data["data"])

                total_pages = data["meta"]["total_pages"]
                print(f"{league} {label}: page {page}/{total_pages}, {len(all_matches)} matches so far")
                if page >= total_pages:
                    break
                page += 1

            save_as_json(league_folder, prefix, {"season": season, "matches": all_matches})

def extract_match_stats(leagues: list[str] | None = None, seasons: list[str] | None=None, max_calls: int | None = None) -> None:
    """One bronze file per match: statsapi/<league>/match_stats/<start_year>/<match_id>.json.
    Resumable: matches already saved are skipped. Stops cleanly when the quota runs out."""
    calls = 0
    for league in leagues or STATSAPI_LEAGUES:
        league_folder = STATS_API_BRONZE / league

        for file in sorted(league_folder.glob(f"{league}_matches_*.json")):
            data = read_json(file)
            label = str(data["season"]["start_year"])
            if seasons and label not in seasons:
                continue
            out_folder = league_folder / "match_stats" / label
            out_folder.mkdir(parents=True, exist_ok=True)

            for match in data["matches"]:
                if match["status"] != "finished":
                    continue
                out = out_folder / f"{match['id']}.json"
                if out.exists():
                    continue
                if max_calls is not None and calls >= max_calls:
                    print(f"Reached max_calls={max_calls}; stopping. Quota remaining: {QUOTA['remaining']}")
                    return

                try:
                    stats = pull_json(f"matches/{match['id']}/stats")
                except QuotaExceeded:
                    print(f"Quota used up after {calls} calls this run. Re-run once the quota resets or after upgrading.")
                    return
                except requests.exceptions.HTTPError as e:
                    if e.response is not None and e.response.status_code == 404:
                        # stats never collected: save a marker so we don't spend a call on it again
                        stats = {"data": None, "meta": {"detailed_stats": "not_found"}}
                    else:
                        raise
                calls += 1
                out.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"{league} {label} {match['id']}: saved ({calls} calls, quota left {QUOTA['remaining']})")

    print(f"Done: {calls} calls this run. Quota remaining: {QUOTA['remaining']}")

if __name__ == "__main__":
    
    # extract_all_competitions("competitions")
    # extract_matches()
    extract_match_stats(leagues=["belgian_pro"], seasons=["2022"])
