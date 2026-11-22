import requests
import os
import time
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from src.utils.helper_io import read_json, save_as_json, latest_json
from src.config import LEAGUES

load_dotenv()
API_KEY = os.getenv("SPORTRADAR_API_KEY")
if not API_KEY:
    raise ValueError("SPORTRADAR_API_KEY is missing or empty")

BASE_URL = "https://api.sportradar.com/soccer-extended/trial/v4/en"
HEADERS = {"accept": "application/json", "x-api-key": API_KEY}
RETRY_STATUSES = {429, 500, 502, 503, 504}
BRONZE = Path(__file__).resolve().parents[2] / "data" / "bronze"
SPORTRADAR_BRONZE = BRONZE / "sportradar"
REQUEST_PAUSE = 1.1


def pull_json(endpoint, params=None, max_retries=3):
    url = f"{BASE_URL}/{endpoint}" 
    for attempt in range(1, max_retries + 1):
        wait = 2 ** attempt

        try:    
            response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"[{attempt}/{max_retries}] network error {endpoint}: {e}; retrying in {wait} seconds")
            
            time.sleep(wait)
            continue

        if response.status_code in RETRY_STATUSES:
            print(f"[{attempt}/{max_retries}] HTTP {response.status_code} on {endpoint}; retrying in {wait}s")
            time.sleep(wait)
            continue

        response.raise_for_status()
        time.sleep(REQUEST_PAUSE)  
        return response.json()

    raise RuntimeError(f"Stopped on {endpoint} after {max_retries} attempts")


def extract_competitions() -> None:
    if latest_json(SPORTRADAR_BRONZE, prefix="competitions"):
        print("Competitions - already saved.")
        return
    data = pull_json("competitions.json")
    save_as_json(SPORTRADAR_BRONZE, "competitions", data)


def extract_seasons() -> None:
    for league, competition_id in LEAGUES.items():
        league_folder = SPORTRADAR_BRONZE / league
        if latest_json(league_folder, prefix="seasons"):
            print(f"{league}: seasons already saved.")
            continue
        data = pull_json(f"competitions/{competition_id}/seasons.json")
        save_as_json(league_folder, "seasons", data)


def select_seasons(league) -> list[dict]:
    file = latest_json(SPORTRADAR_BRONZE / league, "seasons")
    if file is None:
        raise FileNotFoundError(f"No seasons file for {league}; run extract_seasons()")
        
    seasons = sorted(read_json(file)["seasons"], key=lambda season: season["start_date"])
    today = date.today().isoformat()
    
    for season in seasons:
        season["is_complete"] = season["end_date"] < today
    
    return seasons

def extract_season_summaries(league, season_id, season) -> None:
    league_folder = SPORTRADAR_BRONZE / league
    if latest_json(league_folder, prefix=f"season_summary_{season}"):
        print(f"{league}: season summary already saved.")
        return
    
    all_summaries = []
    start = 0
    limit = 100

    while True:
        params = {"start": start, "limit":limit}
        response = pull_json(f"seasons/{season_id}/summaries.json", params=params)

        summaries = response.get("summaries", [])
        all_summaries.extend(summaries)

        print(f"{league} — fetched {len(all_summaries)} records so far (page start={start})")

        if len(summaries) < limit:
            break

        start += limit
    
    response["summaries"] = all_summaries
    save_as_json(league_folder, f"season_summary_{season}", response)

def extract_all_summaries() -> None:
    for league in LEAGUES:
        for s in select_seasons(league):
            if s["is_complete"]:
                extract_season_summaries(league, s["id"], s["year"].replace("/", "_"))


if __name__ == "__main__":
    
    extract_competitions()
    extract_seasons()
    extract_all_summaries()
    
    