"""
scrape_mlb_api.py

Pulls all-time career stats from the MLB Stats API (statsapi.mlb.com).
No browser required — the API returns JSON directly.

Produces three CSV files in data/:
  - CareerHittingStatsAlltime.csv   (~22,000 players)
  - CareerPitchingStatsAlltime.csv  (~12,000 players)
  - CareerFieldingStatsAlltime.csv  (~50,000 player-position records)
"""

import os
import time
import requests
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://statsapi.mlb.com/api/v1/stats"
LIMIT = 500          # records per request (API max is ~1000, 500 is safe)
SLEEP_BETWEEN = 0.3  # seconds between requests — polite but fast

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

GROUPS = [
    {"group": "hitting",  "output": "CareerHittingStatsAlltime.csv"},
    {"group": "pitching", "output": "CareerPitchingStatsAlltime.csv"},
    {"group": "fielding", "output": "CareerFieldingStatsAlltime.csv"},
]


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------

def fetch_page(group: str, offset: int, limit: int) -> dict:
    params = {
        "stats":      "career",
        "group":      group,
        "sportId":    1,
        "playerPool": "ALL",
        "limit":      limit,
        "offset":     offset,
    }
    r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def parse_splits(splits: list) -> list[dict]:
    """Flatten each split record into a single dict."""
    rows = []
    for s in splits:
        row = {}
        # Player info
        p = s.get("player", {})
        row["player_id"]   = p.get("id")
        row["full_name"]   = p.get("fullName")
        row["first_name"]  = p.get("firstName")
        row["last_name"]   = p.get("lastName")

        # Position
        pos = s.get("position", {})
        row["position_code"] = pos.get("code")
        row["position_name"] = pos.get("name")
        row["position_abbr"] = pos.get("abbreviation")

        # Team / league
        row["team_id"]   = s.get("team",   {}).get("id")
        row["team_name"] = s.get("team",   {}).get("name")
        row["league_id"] = s.get("league", {}).get("id")
        row["league"]    = s.get("league", {}).get("name")

        row["num_teams"] = s.get("numTeams")

        # All stat fields (whatever the API returns for this group)
        row.update(s.get("stat", {}))

        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Main scrape loop
# ---------------------------------------------------------------------------

def scrape_group(group: str, output_file: str, data_dir: str):
    print(f"\n{'='*55}")
    print(f"  Scraping group: {group.upper()}")
    print(f"{'='*55}")

    all_rows = []
    offset = 0
    total = None

    while True:
        print(f"  offset={offset:>6}  /  total={total if total else '?'} ...", end="  ")
        try:
            data = fetch_page(group, offset, LIMIT)
        except requests.RequestException as e:
            print(f"\n  ERROR fetching offset {offset}: {e}")
            print("  Saving progress and moving on.")
            break

        stats_block = data.get("stats", [{}])[0]

        if total is None:
            total = stats_block.get("totalSplits", 0)
            print(f"(total={total})")

        splits = stats_block.get("splits", [])
        if not splits:
            print("no splits returned — done.")
            break

        rows = parse_splits(splits)
        all_rows.extend(rows)
        print(f"fetched {len(splits)}  |  running total: {len(all_rows)}")

        offset += len(splits)
        if offset >= total:
            break

        time.sleep(SLEEP_BETWEEN)

    if not all_rows:
        print(f"  No data for group '{group}'. Skipping.")
        return

    df = pd.DataFrame(all_rows)
    out_path = os.path.join(data_dir, output_file)
    df.to_csv(out_path, index=False)
    print(f"\n  Saved {len(df):,} records -> {out_path}")
    print(f"  Columns ({len(df.columns)}): {list(df.columns)}")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    for cfg in GROUPS:
        scrape_group(cfg["group"], cfg["output"], data_dir)

    print("\nAll done.")


if __name__ == "__main__":
    main()
