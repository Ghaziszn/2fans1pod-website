import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

CFBD_KEY = os.getenv("CFBD_API_KEY")

if not CFBD_KEY:
    print("Error: CFBD_API_KEY not found in environment variables.")
    exit(1)

headers = {"Authorization": f"Bearer {CFBD_KEY}"}

def fetch_data(url):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def compute_metrics(rows):
    bucket = {}
    
    # Find games count
    games_row = next((r for r in rows if r.get("statName") == "games"), None)
    games = int(games_row["statValue"]) if games_row else 0
    
    print(f"Games: {games}")
    
    # Debug: Print all available stat names
    all_stats = sorted(list(set(r.get("statName") for r in rows)))
    print(f"Available Stats: {all_stats}")

    def_stats = ["sacks", "tacklesForLoss", "interceptions", "fumblesRecovered", "interceptionTDs", "interceptionYards"]

    for r in rows:
        stat_name = r.get("statName", "").strip()
        if not stat_name or stat_name == "games":
            continue
        
        try:
            val = float(r["statValue"])
        except (ValueError, TypeError):
            continue

        is_opponent = stat_name.endswith("Opponent")
        base_name = stat_name.replace("Opponent", "")
        
        # Logic from app.js
        if base_name in def_stats:
            is_def_bucket = not is_opponent
        else:
            is_def_bucket = is_opponent
            
        per_game_val = val / games if games > 0 else val
        
        if base_name not in bucket:
            bucket[base_name] = {}
        
        if is_def_bucket:
            bucket[base_name]["def"] = per_game_val
        else:
            bucket[base_name]["off"] = per_game_val

    def get_val(key, type_):
        return bucket.get(key, {}).get(type_)

    def div(n, d):
        return n / d if (n is not None and d is not None and d > 0) else None

    # Fix topPct logic: possessionTime (off) vs possessionTime (def/opponent)
    # bucket["possessionTime"]["off"] is own possession
    # bucket["possessionTime"]["def"] is opponent possession
    top_off = get_val("possessionTime", "off")
    top_def = get_val("possessionTime", "def")
    
    off = {
        "ppg": get_val("points", "off"), # Check if 'points' exists in Available Stats
        "ypg": get_val("totalYards", "off"),
        "rushYdsG": get_val("rushingYards", "off"),
        "passYdsG": (get_val("netPassingYards", "off") or get_val("passingYards", "off")),
        "topPct": div(top_off, (top_off or 0) + (top_def or 0)),
        "thirdPct": div(get_val("thirdDownConversions", "off"), get_val("thirdDowns", "off")),
        "fourthPct": div(get_val("fourthDownConversions", "off"), get_val("fourthDowns", "off")),
        "rzPct": div((get_val("redZoneScores", "off") or get_val("redzoneScores", "off")), (get_val("redZoneAttempts", "off") or get_val("redzoneAttempts", "off"))),
        "ydsPerRush": div(get_val("rushingYards", "off"), get_val("rushingAttempts", "off")),
        "takeaways": get_val("turnovers", "def"),
        "giveaways": get_val("turnovers", "off"),
        "penalties": get_val("penalties", "off"),
    }

    def_ = {
        "ppg": get_val("points", "def"),
        "ypg": get_val("totalYards", "def"),
        "rushYdsG": get_val("rushingYards", "def"),
        "passYdsG": (get_val("netPassingYards", "def") or get_val("passingYards", "def")),
        "thirdPct": div(get_val("thirdDownConversions", "def"), get_val("thirdDowns", "def")),
        "fourthPct": div(get_val("fourthDownConversions", "def"), get_val("fourthDowns", "def")),
        "rzPct": div((get_val("redZoneScores", "def") or get_val("redzoneScores", "def")), (get_val("redZoneAttempts", "def") or get_val("redzoneAttempts", "def"))),
        "ydsPerRush": div(get_val("rushingYards", "def"), get_val("rushingAttempts", "def")),
        "tfl": get_val("tacklesForLoss", "def"),
        "sacks": get_val("sacks", "def"),
    }
    
    return off, def_

# Fetch Stats
print("Fetching ALL Stats (2025)...")
# Note: Removing 'team' param fetches all
all_stats = fetch_data("https://api.collegefootballdata.com/stats/season?year=2025")

print(f"Total rows fetched: {len(all_stats)}")

# Filter for Alabama locally
stats = [r for r in all_stats if r.get("team") == "Alabama"]
print(f"Alabama rows found: {len(stats)}")

if stats:
    offense, defense = compute_metrics(stats)
    
    print("\n--- Calculated Offense Metrics (from bulk fetch) ---")
    print(json.dumps(offense, indent=2))
    
    print("\n--- Calculated Defense Metrics (from bulk fetch) ---")
    print(json.dumps(defense, indent=2))
else:
    print("No stats found for Alabama in bulk fetch.")
