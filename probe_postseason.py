import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()
api_key = os.getenv("CFBD_API_KEY")
headers = {"Authorization": f"Bearer {api_key}"}

def get_games(year, week, season_type):
    url = "https://api.collegefootballdata.com/games"
    params = {"year": year, "week": week, "seasonType": season_type}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.status_code, "msg": response.text}

print("Checking 2024 Postseason Week 1...")
games_2024 = get_games(2024, 1, "postseason")
print(f"Found {len(games_2024) if isinstance(games_2024, list) else games_2024} games.")

if isinstance(games_2024, list) and len(games_2024) > 0:
    print("Example game:", games_2024[0]['title'] if 'title' in games_2024[0] else "No title", games_2024[0]['away_team'], "vs", games_2024[0]['home_team'])


print("\nChecking information about weeks available in postseason...")
# There isn't a direct endpoint for available weeks, but we can guess.

print("\nChecking 2024 Regular Season Week 15 (Conference Championships usually)...")
games_cc = get_games(2024, 15, "regular")
print(f"Found {len(games_cc)} games.")
