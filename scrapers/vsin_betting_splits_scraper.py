"""
VSIN Betting Splits Scraper

This scraper fetches betting splits data (handle % and bets %) from VSIN
for all college football games. Data includes spread, total, and moneyline splits.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime


def scrape_vsin_betting_splits():
    """
    Scrape betting splits from VSIN for all CFB games.
    Returns a dictionary with game data including handle and bets percentages.
    """
    url = "https://data.vsin.com/college-football/betting-splits/"
    
    print(f"Fetching VSIN betting splits: {url}")
    
    # Headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    games = []
    
    # Find all game rows in the table
    # Each game is represented by a <tr> element with team data
    rows = soup.find_all('tr', class_='')
    
    print(f"Found {len(rows)} potential game rows")
    
    for row in rows:
        try:
            game_data = parse_game_row(row)
            if game_data:
                games.append(game_data)
                print(f"  ✓ Parsed: {game_data['away_team']} @ {game_data['home_team']}")
        except Exception as e:
            print(f"  ⚠️  Error parsing row: {e}")
            continue
    
    print(f"\n✅ Successfully scraped {len(games)} games")
    
    return {
        "scraped_at": datetime.utcnow().isoformat(),
        "games": games
    }


def parse_game_row(row):
    """
    Parse a single game row to extract team names and betting splits.
    
    Expected structure:
    - Column 0: Team names (away/home separated by <hr>)
    - Column 1: Spread values
    - Column 2: Spread Handle %
    - Column 3: Spread Bets %
    - Column 4: Total values
    - Column 5: Total Handle %
    - Column 6: Total Bets %
    - Column 7: Moneyline values
    - Column 8: Moneyline Handle %
    - Column 9: Moneyline Bets %
    """
    cells = row.find_all('td')
    
    if len(cells) < 10:
        return None
    
    # Extract team names from first column
    team_cell = cells[0]
    team_links = team_cell.find_all('a', class_='txt-color-vsinred')
    
    if len(team_links) < 2:
        return None
    
    away_team = team_links[0].get_text(strip=True)
    home_team = team_links[1].get_text(strip=True)
    
    # Extract spread data (columns 1, 2, 3)
    spread_values = extract_split_values(cells[1])
    spread_handle = extract_percentages(cells[2])
    spread_bets = extract_percentages(cells[3])
    
    # Extract total data (columns 4, 5, 6)
    total_values = extract_split_values(cells[4])
    total_handle = extract_percentages(cells[5])
    total_bets = extract_percentages(cells[6])
    
    # Extract moneyline data (columns 7, 8, 9)
    moneyline_values = extract_split_values(cells[7])
    moneyline_handle = extract_percentages(cells[8])
    moneyline_bets = extract_percentages(cells[9])
    
    game_data = {
        "away_team": away_team,
        "home_team": home_team,
        "spread": {
            "away_line": spread_values[0] if len(spread_values) > 0 else None,
            "home_line": spread_values[1] if len(spread_values) > 1 else None,
            "away_handle_pct": spread_handle[0] if len(spread_handle) > 0 else None,
            "home_handle_pct": spread_handle[1] if len(spread_handle) > 1 else None,
            "away_bets_pct": spread_bets[0] if len(spread_bets) > 0 else None,
            "home_bets_pct": spread_bets[1] if len(spread_bets) > 1 else None,
        },
        "total": {
            "line": total_values[0] if len(total_values) > 0 else None,
            "over_handle_pct": total_handle[0] if len(total_handle) > 0 else None,
            "under_handle_pct": total_handle[1] if len(total_handle) > 1 else None,
            "over_bets_pct": total_bets[0] if len(total_bets) > 0 else None,
            "under_bets_pct": total_bets[1] if len(total_bets) > 1 else None,
        },
        "moneyline": {
            "away_line": moneyline_values[0] if len(moneyline_values) > 0 else None,
            "home_line": moneyline_values[1] if len(moneyline_values) > 1 else None,
            "away_handle_pct": moneyline_handle[0] if len(moneyline_handle) > 0 else None,
            "home_handle_pct": moneyline_handle[1] if len(moneyline_handle) > 1 else None,
            "away_bets_pct": moneyline_bets[0] if len(moneyline_bets) > 0 else None,
            "home_bets_pct": moneyline_bets[1] if len(moneyline_bets) > 1 else None,
        }
    }
    
    return game_data


def extract_split_values(cell):
    """
    Extract betting line values (spread, total, moneyline) from a cell.
    Values are separated by <hr> tags.
    Returns a list of values (e.g., ['+5.5', '-5.5'] or ['59.5', '59.5'])
    """
    values = []
    
    # Find all divs with class 'scorebox_highlight'
    divs = cell.find_all('div', class_='scorebox_highlight')
    
    for div in divs:
        link = div.find('a')
        if link:
            value = link.get_text(strip=True)
            values.append(value)
    
    return values


def extract_percentages(cell):
    """
    Extract percentage values from a cell.
    Percentages are separated by <hr> tags.
    Returns a list of integers (e.g., [39, 61])
    """
    percentages = []
    
    # Find all divs with class 'box_highlight_even1' or 'box_highlight_for1'
    divs = cell.find_all('div', class_=re.compile(r'box_highlight'))
    
    for div in divs:
        text = div.get_text(strip=True)
        # Extract percentage value (remove % sign and any icons)
        match = re.search(r'(\d+)%', text)
        if match:
            percentages.append(int(match.group(1)))
    
    return percentages


def save_to_cache(data, filepath="data/vsin_betting_splits.json"):
    """Save scraped data to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"💾 Saved to {filepath}")


if __name__ == "__main__":
    # When run directly, scrape and save to cache
    data = scrape_vsin_betting_splits()
    save_to_cache(data)
    
    # Print a sample game for verification
    if data['games']:
        print("\n" + "="*60)
        print("SAMPLE GAME DATA:")
        print("="*60)
        print(json.dumps(data['games'][0], indent=2))
