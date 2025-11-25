"""
Opponent RedZone Scraper for CFBStats.com

This scraper fetches opponent red zone (defensive) statistics for all FBS teams.
Data is cached to avoid excessive requests to the source website.
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

# Disable SSL warnings due to cfbstats broken certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://cfbstats.com"


def get_teams_list():
    """Fetch the list of all teams and their URLs."""
    url = "https://cfbstats.com/2025/team/index.html"
    print(f"Fetching team index: {url}")

    response = requests.get(url, verify=False, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    teams = {}
    
    # Pattern to match team pages: /2025/team/{number}/
    pattern = re.compile(r'/2025/team/\d+/')

    # Find all links that match the team pattern
    for link in soup.find_all("a"):
        href = link.get("href", "")
        if pattern.search(href):
            name = link.text.strip()
            if name:
                teams[name] = BASE + href
    
    print(f"Found {len(teams)} teams")
    return teams


def get_opponent_redzone_stats(team_url):
    """Fetch opponent red zone (defensive) stats for a specific team (All Games split)."""
    # The red zone defense split page lives under the team page path
    redzone_url = team_url.replace("index.html", "redzone/defense/split.html")
    
    print(f"Fetching: {redzone_url}")
    response = requests.get(redzone_url, verify=False, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Find the stats table
    table = soup.find("table")
    if not table:
        return None

    rows = table.find_all("tr")
    if len(rows) < 2:
        return None

    # Extract headers
    headers = [h.get_text(strip=True) for h in rows[0].find_all(["th", "td"])]

    # Extract each row
    for row in rows[1:]:
        cols = row.find_all("td")
        if not cols:
            continue

        values = [c.get_text(strip=True) for c in cols]

        if len(values) == len(headers):
            row_data = dict(zip(headers, values))
            # Return only the "All Games" row
            if row_data.get("Split") == "All Games":
                return row_data

    return None


def scrape_all_teams():
    """
    Scrape opponent red zone (defensive) stats for ALL teams.
    Returns a dictionary: {team_name: {opponent_redzone_stats}}
    """
    print("Starting full scrape of all teams (opponent red zone defense)...")
    teams = get_teams_list()
    
    all_data = {}
    total = len(teams)
    
    for idx, (name, url) in enumerate(teams.items(), 1):
        print(f"[{idx}/{total}] Scraping {name}...")
        try:
            stats = get_opponent_redzone_stats(url)
            if stats:
                all_data[name] = stats
        except Exception as e:
            print(f"  ⚠️  Error scraping {name}: {e}")
            continue
    
    print(f"\n✅ Scraped {len(all_data)} teams successfully")
    return all_data


def save_to_cache(data, filepath="data/opponent_redzone_stats.json"):
    """Save scraped data to a JSON file with timestamp."""
    cache_data = {
        "scraped_at": datetime.utcnow().isoformat(),
        "teams": data
    }
    
    with open(filepath, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"💾 Saved to {filepath}")


if __name__ == "__main__":
    # When run directly, scrape all teams and save to cache
    data = scrape_all_teams()
    save_to_cache(data)
