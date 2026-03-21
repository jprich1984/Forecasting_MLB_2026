import os
import re
import json
import requests
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def fetch_fangraphs_opening_day(season=2026):
    url = f"https://www.fangraphs.com/roster-resource/opening-day-tracker?season={season}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
        r.text, re.DOTALL
    )
    if not match:
        raise ValueError("Could not find __NEXT_DATA__ in page — page structure may have changed.")
    data = json.loads(match.group(1))
    return data["props"]["pageProps"]["dehydratedState"]["queries"][0]["state"]["data"]

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    season = 2026
    print(f"Fetching {season} Opening Day Tracker from FanGraphs...")

    players = fetch_fangraphs_opening_day(season)
    print(f"Found {len(players)} player entries.")

    df = pd.DataFrame(players)[[
        "team", "playerName", "position", "status",
        "projectedOpeningDayRole", "age", "servicetime",
        "is40Man", "options", "proj_PA", "proj_IP", "proj_PT",
    ]]
    df.columns = [
        "Team", "Name", "Pos", "Status",
        "ProjectedOpeningDayRole", "Age", "ServiceTime",
        "Is40Man", "Options", "Proj_PA", "Proj_IP", "Proj_PT",
    ]

    output = os.path.join(data_dir, "PlayerTeamsAll_2026.csv")
    df.to_csv(output, index=False)
    print(f"SUCCESS: {len(df)} players saved to {output}")
    print("\nRole breakdown:")
    print(df["ProjectedOpeningDayRole"].value_counts().to_string())

if __name__ == "__main__":
    main()
