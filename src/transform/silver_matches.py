from pathlib import Path
from src.utils.helper_io import read_json
from src.config import LEAGUES, STAT_KEYS

import pandas as pd

BRONZE = Path(__file__).resolve().parents[2] / "data" / "bronze"
SPORTRADAR_BRONZE = BRONZE / "sportradar"
SILVER = Path(__file__).resolve().parents[2] / "data" / "silver"

def load_summaries(league):
    matches = []
    for file in sorted((SPORTRADAR_BRONZE / league).glob("season_summary_*.json")):
        matches.extend(read_json(file)["summaries"])
    return matches

def phase_from_group(group_name):
    if "," not in group_name:
        return "regular season"
    else:
        phase = group_name.split(",")[-1].strip()      # strip the leading space
        if "Relegation/Promotion" in phase:
            return "promotion_playoff"
        if "Championship" in phase:
            return "championship_playoff"
        if "Qualifying" in phase:
            return "europe_playoff"
        if "Europa" in phase:
            return "europa_playoff"
        if phase == "Relegation Round":
            return "relegation_playoff"
        raise ValueError(f"Unknown group: {group_name!r}")
        
def team_stats(match, qualifier):
    for comp in match.get("statistics", {}).get("totals", {}).get("competitors", []):
        if comp.get("qualifier") == qualifier:
            return comp.get("statistics", {})
    return {}

def flatten_match(match, league):
    
    event = match["sport_event"]
    status = match["sport_event_status"]
    context = event["sport_event_context"]

    group_name = (context.get("groups") or [{}])[0].get("name", "")
    teams = {competitor["qualifier"]: competitor for competitor in event["competitors"]}
    home_goals, away_goals = status["home_score"], status["away_score"]
    
    row =  {
        "league": league,
        "match_id": event["id"],
        "season": context["season"]["year"],
        "season_id": context["season"]["id"],
        "start_time": event["start_time"],
        "round": context.get("round", {}).get("number"),
        "group_name": group_name,
        "phase": phase_from_group(group_name),
        "home_team_id": teams["home"]["id"],
        "home_team": teams["home"]["name"],
        "away_team_id": teams["away"]["id"],
        "away_team": teams["away"]["name"],
        "home_goals": home_goals,
        "away_goals": away_goals,
        "result": "H" if home_goals > away_goals else "A" if away_goals > home_goals else "D"
    }

    for side in ("home", "away"):
        stats = team_stats(match, side)
        for key in STAT_KEYS:
            row[f"{side}_{key}"] = stats.get(key)
    
    return row

def build_silver(matches):
    df = pd.DataFrame(matches)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    stat_cols = [f"{side}_{k}" for side in ("home", "away") for k in STAT_KEYS]
    df[stat_cols] = df[stat_cols].astype("Int64")
    
    output = SILVER / "matches.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output, index=False)

    return df

if __name__ == "__main__":
    rows = []
    for league in LEAGUES:
        for match in load_summaries(league):
            if match["sport_event_status"]["status"] != "closed":
                continue
            rows.append(flatten_match(match, league))
    
    df = build_silver(rows)

    print(df.head())
    print(df.shape)
    

