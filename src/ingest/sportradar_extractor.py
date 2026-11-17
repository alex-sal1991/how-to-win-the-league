import requests
import os
import time
import pprint
from pathlib import Path
from dotenv import load_dotenv
from src.utils.helper_io import *

load_dotenv()
API_KEY = os.getenv("SPORTRADAR_API_KEY")
if API_KEY is None:
    raise ValueError("SPORTRADAR_API_KEY is missing or empty")

BASE_URL = "https://api.sportradar.com/soccer-extended/trial/v4/en"
headers = {"accept": "application/json", "x-api-key": API_KEY}
RETRY_STATUSES = {429, 500, 502, 503, 504}
BRONZE = Path(__file__).resolve().parents[2] / "data" / "bronze"

#### Extract competitions
def pull_competitions(endpoint, params=None, max_retries=3):
    url = f"{BASE_URL}/{endpoint}" 
    for attempt in range(1, max_retries + 1):
        wait = 2 ** attempt

        try:    
            response = requests.get(url, headers=headers, params=params, timeout=30)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"[{attempt}/{max_retries}] network error {endpoint}: {e}; retrying in {wait} seconds")
            
            time.sleep(wait)
            continue

        if response.status_code in RETRY_STATUSES:
            print(f"[{attempt}/{max_retries}] HTTP {response.status_code} on {endpoint}; retrying in {wait}s")
            time.sleep(wait)
            continue

        response.raise_for_status()
        return response.json()

    raise RuntimeError(f"Stopped on {endpoint} after {max_retries} attempts")

if __name__ == "__main__":
    folder = BRONZE / "sportradar"

    competitions = pull_competitions("/competitions.json")
    saved_json = save_as_json(folder, "competitions.json", competitions)

    data = read_json("data/bronze/sportradar/competitions.json_20261117_095830.json")
    for comp in data["competitions"]:
        if comp.get("gender") == "men" and comp.get("category", {}).get("country_code") in {"ENG", "PRT", "BEL", "NOR"}:
            print(comp["id"], comp["category"]["name"], comp["name"])
    