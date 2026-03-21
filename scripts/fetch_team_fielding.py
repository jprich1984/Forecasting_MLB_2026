"""
fetch_team_fielding.py

Fetches team fielding stats for every season 1995-2025
(excluding 2020, the shortened COVID season) from the MLB Stats API.
Produces: data/teamFielding1995-2025.csv
"""

import os
import time
import requests
import pandas as pd

BASE_URL = "https://statsapi.mlb.com/api/v1"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

YEARS = [y for y in range(1995, 2026) if y != 2020]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
OUT_CSV = os.path.join(DATA_DIR, "teamFielding1995-2025.csv")

DIVISION_MAP = {
    200: "W",  # AL West
    201: "E",  # AL East
    202: "C",  # AL Central
    203: "W",  # NL West
    204: "E",  # NL East
    205: "C",  # NL Central
}


def get(endpoint: str, params: dict) -> dict:
    r = requests.get(f"{BASE_URL}{endpoint}", params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_standings(season: int) -> dict:
    """Returns {team_id: {wins, division, league, team_name}} for a season."""
    data = get("/standings", {
        "leagueId": "103,104",
        "season": season,
        "standingsTypes": "regularSeason",
    })
    LEAGUE_MAP = {103: "AL", 104: "NL"}
    result = {}
    for record in data.get("records", []):
        div_id = record["division"]["id"]
        league_id = record["league"]["id"]
        for tr in record.get("teamRecords", []):
            tid = tr["team"]["id"]
            result[tid] = {
                "team_name": tr["team"]["name"],
                "WINS":      tr["wins"],
                "LEAGUE":    LEAGUE_MAP.get(league_id, "?"),
                "DIVISION":  DIVISION_MAP.get(div_id, "?"),
            }
    return result


def build_fielding_row(s: dict, standings: dict, season: int) -> dict:
    stat = s["stat"]
    team = s["team"]
    tid = team["id"]
    info = standings.get(tid, {})
    return {
        "TEAM":                  team["name"],
        "LEAGUE":                info.get("LEAGUE", ""),
        "DIVISION":              info.get("DIVISION", ""),
        "WINS":                  info.get("WINS", None),
        "Year":                  season,
        "G":                     stat.get("gamesPlayed"),
        "errors":                stat.get("errors"),
        "fielding_pct":          stat.get("fielding"),
        "putOuts":               stat.get("putOuts"),
        "assists":               stat.get("assists"),
        "chances":               stat.get("chances"),
        "doublePlays":           stat.get("doublePlays"),
        "triplePlays":           stat.get("triplePlays"),
        "rangeFactorPerGame":    stat.get("rangeFactorPerGame"),
        "rangeFactorPer9Inn":    stat.get("rangeFactorPer9Inn"),
        "innings":               stat.get("innings"),
        "passedBall":            stat.get("passedBall"),
        "wildPitches":           stat.get("wildPitches"),
        "throwingErrors":        stat.get("throwingErrors"),
        "caughtStealing":        stat.get("caughtStealing"),
        "stolenBasesAllowed":    stat.get("stolenBases"),
        "stolenBasePercentage":  stat.get("stolenBasePercentage"),
        "catchersInterference":  stat.get("catchersInterference"),
        "pickoffs":              stat.get("pickoffs"),
    }


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    all_rows = []

    for season in YEARS:
        print(f"Fetching {season}...", end="  ")
        try:
            standings = fetch_standings(season)
            time.sleep(0.3)

            data = get("/teams/stats", {
                "stats": "season",
                "group": "fielding",
                "season": season,
                "sportId": 1,
            })
            splits = data["stats"][0]["splits"]

            for s in splits:
                all_rows.append(build_fielding_row(s, standings, season))

            print(f"{len(splits)} teams")
        except Exception as e:
            print(f"ERROR: {e}")

        time.sleep(0.3)

    df = pd.DataFrame(all_rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {len(df)} rows -> {OUT_CSV}")
    print(f"Columns: {list(df.columns)}")


if __name__ == "__main__":
    main()
