"""
fetch_all_team_stats.py

Fetches team hitting and pitching stats for every season 1995-2025
(excluding 2020, the shortened COVID season) directly from the MLB Stats API.
Produces a single clean CSV: data/TeamWins_clean.csv

This replaces the old scrape_mlb.py + clean_baseball_data.py pipeline
and eliminates the doubled-column-name artifact from HTML scraping.
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
OUT_CSV = os.path.join(DATA_DIR, "TeamWins_clean.csv")

# MLB Stats API division IDs -> single-letter abbreviation
DIVISION_MAP = {
    200: "W",  # AL West
    201: "E",  # AL East
    202: "C",  # AL Central
    203: "W",  # NL West
    204: "E",  # NL East
    205: "C",  # NL Central
}


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

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
    # League id 103 = AL, 104 = NL
    LEAGUE_MAP = {103: "AL", 104: "NL"}
    result = {}
    for record in data.get("records", []):
        div_id = record["division"]["id"]
        league_id = record["league"]["id"]
        league_abbr = LEAGUE_MAP.get(league_id, "?")
        division_abbr = DIVISION_MAP.get(div_id, "?")
        for tr in record.get("teamRecords", []):
            tid = tr["team"]["id"]
            result[tid] = {
                "team_name": tr["team"]["name"],
                "WINS":      tr["wins"],       # top-level wins field
                "LEAGUE":    league_abbr,
                "DIVISION":  division_abbr,
            }
    return result


def fetch_team_stats(group: str, season: int) -> list[dict]:
    data = get("/teams/stats", {
        "stats": "season",
        "group": group,
        "season": season,
        "sportId": 1,
    })
    return data["stats"][0]["splits"]


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def build_hitting_row(s: dict, standings: dict, season: int) -> dict:
    stat = s["stat"]
    team = s["team"]
    tid = team["id"]
    info = standings.get(tid, {})
    return {
        "TEAM":     team["name"],
        "LEAGUE":   info.get("LEAGUE", ""),
        "DIVISION": info.get("DIVISION", ""),
        "WINS":     info.get("WINS", None),
        "Year":     season,
        "G":        stat.get("gamesPlayed"),
        "AB":       stat.get("atBats"),
        "R":        stat.get("runs"),
        "H":        stat.get("hits"),
        "2B":       stat.get("doubles"),
        "3B":       stat.get("triples"),
        "HR":       stat.get("homeRuns"),
        "RBI":      stat.get("rbi"),
        "BB":       stat.get("baseOnBalls"),
        "SO":       stat.get("strikeOuts"),
        "SB":       stat.get("stolenBases"),
        "CS":       stat.get("caughtStealing"),
        "AVG":      stat.get("avg"),
        "OBP":      stat.get("obp"),
        "SLG":      stat.get("slg"),
        "OPS":      stat.get("ops"),
        "team_id":  tid,
    }


def build_pitching_row(s: dict, season: int) -> dict:
    stat = s["stat"]
    team = s["team"]
    return {
        "team_id":   team["id"],
        "Year":      season,
        "W_pitch":   stat.get("wins"),
        "L_pitch":   stat.get("losses"),
        "ERA_pitch": stat.get("era"),
        "G_pitch":   stat.get("gamesPlayed"),
        "GS_pitch":  stat.get("gamesStarted"),
        "CG_pitch":  stat.get("completeGames"),
        "SHO_pitch": stat.get("shutouts"),
        "SV_pitch":  stat.get("saves"),
        "SVO_pitch": stat.get("saveOpportunities"),
        "IP_pitch":  stat.get("inningsPitched"),
        "H_pitch":   stat.get("hits"),
        "R_pitch":   stat.get("runs"),
        "ER_pitch":  stat.get("earnedRuns"),
        "HR_pitch":  stat.get("homeRuns"),
        "HB_pitch":  stat.get("hitBatsmen"),
        "BB_pitch":  stat.get("baseOnBalls"),
        "SO_pitch":  stat.get("strikeOuts"),
        "WHIP_pitch": stat.get("whip"),
        "AVG_pitch": stat.get("avg"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    all_hitting = []
    all_pitching = []

    for season in YEARS:
        print(f"Fetching {season}...", end="  ")
        try:
            standings = fetch_standings(season)
            hitting_splits = fetch_team_stats("hitting", season)
            time.sleep(0.3)
            pitching_splits = fetch_team_stats("pitching", season)
            time.sleep(0.3)

            for s in hitting_splits:
                all_hitting.append(build_hitting_row(s, standings, season))
            for s in pitching_splits:
                all_pitching.append(build_pitching_row(s, season))

            print(f"{len(hitting_splits)} teams")
        except Exception as e:
            print(f"ERROR: {e}")

    hitting_df = pd.DataFrame(all_hitting)
    pitching_df = pd.DataFrame(all_pitching)

    merged = pd.merge(hitting_df, pitching_df, on=["team_id", "Year"], how="inner")
    merged = merged.drop(columns=["team_id"])

    merged.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {len(merged)} rows -> {OUT_CSV}")
    print(f"Columns: {list(merged.columns)}")


if __name__ == "__main__":
    main()
