"""
Recruiting Data Fetcher

Fetches college football recruiting data from the College Football Data API (CFBD).
Data includes high school and JUCO recruits with ratings, positions, and commitments.
"""

import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def fetch_recruiting_data(year=None, team=None, classification="HighSchool", position=None, state=None):
    """
    Fetch recruiting data from CFBD API.
    
    Args:
        year: Recruiting class year (e.g., 2024)
        team: Filter by committed team (optional)
        classification: HighSchool, PrepSchool, or JUCO (default: HighSchool)
        position: Filter by position (optional)
        state: Filter by home state (optional)
    
    Returns:
        Dictionary with recruiting data
    """
    if year is None:
        # Default to current year
        year = datetime.now().year
    
    CFBD_KEY = os.getenv("CFBD_API_KEY", "").strip()
    if not CFBD_KEY:
        raise ValueError("CFBD_API_KEY not set in .env file")
    
    url = "https://api.collegefootballdata.com/recruiting/players"
    headers = {"Authorization": f"Bearer {CFBD_KEY}"}
    params = {
        "year": year,
        "classification": classification
    }
    
    # Add optional filters
    if team:
        params["team"] = team
    if position:
        params["position"] = position
    if state:
        params["state"] = state
    
    print(f"Fetching recruiting data for {year} class...")
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    recruits = response.json()
    
    print(f"✅ Successfully fetched {len(recruits)} recruits")
    
    # Process and clean the data
    processed_recruits = []
    for recruit in recruits:
        processed_recruit = {
            "id": recruit.get("id"),
            "athlete_id": recruit.get("athleteId"),
            "recruit_type": recruit.get("recruitType"),
            "year": recruit.get("year"),
            "ranking": recruit.get("ranking"),
            "name": recruit.get("name"),
            "school": recruit.get("school"),
            "committed_to": recruit.get("committedTo"),
            "position": recruit.get("position"),
            "height": recruit.get("height"),
            "weight": recruit.get("weight"),
            "stars": recruit.get("stars"),
            "rating": recruit.get("rating"),
            "city": recruit.get("city"),
            "state_province": recruit.get("stateProvince"),
            "country": recruit.get("country")
        }
        processed_recruits.append(processed_recruit)
    
    return {
        "fetched_at": datetime.utcnow().isoformat(),
        "year": year,
        "classification": classification,
        "total_recruits": len(processed_recruits),
        "recruits": processed_recruits
    }


def add_current_team_info(recruits_data):
    """
    Add current team information by cross-referencing with transfer portal data.
    
    Args:
        recruits_data: Dictionary with recruiting data
    
    Returns:
        Updated recruits_data with current_team field added
    """
    from pathlib import Path
    import glob
    
    # Load ALL transfer portal data files (multiple years)
    transfer_lookup = {}
    
    # Find all transfer portal JSON files
    transfer_files = glob.glob("data/transfer_portal*.json")
    
    if not transfer_files:
        # Try the default file
        transfer_files = ["data/transfer_portal.json"]
    
    for transfer_file_path in transfer_files:
        transfer_file = Path(transfer_file_path)
        if transfer_file.exists():
            try:
                with open(transfer_file, 'r') as f:
                    transfer_data = json.load(f)
                
                print(f"📋 Loading transfers from {transfer_file.name}")
                
                # Create lookup by player name
                for transfer in transfer_data.get('transfers', []):
                    first_name = transfer.get('first_name', '').strip()
                    last_name = transfer.get('last_name', '').strip()
                    
                    if first_name and last_name:
                        # Use full name as key (normalized)
                        full_name = f"{first_name} {last_name}".lower()
                        transfer_date = transfer.get('transfer_date', '')
                        
                        # Store the most recent destination (latest transfer date)
                        if full_name not in transfer_lookup or transfer_date > transfer_lookup[full_name].get('transfer_date', ''):
                            transfer_lookup[full_name] = {
                                'destination': transfer.get('destination'),
                                'origin': transfer.get('origin'),
                                'transfer_date': transfer_date,
                                'season': transfer.get('season')
                            }
            except Exception as e:
                print(f"⚠️  Could not load transfer portal data from {transfer_file.name}: {e}")
    
    print(f"✅ Loaded {len(transfer_lookup)} unique transfer records")
    
    # Update recruits with current team info
    matched_count = 0
    for recruit in recruits_data['recruits']:
        recruit_name = recruit.get('name', '').strip().lower()
        committed_to = recruit.get('committed_to')
        
        # Check if player has transferred
        if recruit_name in transfer_lookup:
            transfer_info = transfer_lookup[recruit_name]
            current_team = transfer_info['destination']
            
            # Add current team and transfer flag
            recruit['current_team'] = current_team if current_team else committed_to
            recruit['transferred'] = bool(current_team and current_team != committed_to)
            
            if recruit['transferred']:
                matched_count += 1
        else:
            # No transfer found, assume still at committed school
            recruit['current_team'] = committed_to
            recruit['transferred'] = False
    
    print(f"✅ Matched {matched_count} transfers out of {len(recruits_data['recruits'])} recruits")
    
    return recruits_data


def save_to_cache(data, year=None, filepath=None):
    """Save fetched data to a year-specific JSON file."""
    if filepath is None:
        if year is None:
            year = data.get('year', datetime.now().year)
        filepath = f"data/recruiting_{year}.json"
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Add current team information before saving
    data = add_current_team_info(data)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"💾 Saved {data['total_recruits']} recruits to {filepath}")


def is_cache_stale(year=None, filepath=None, max_age_hours=24):
    """
    Check if the cached data is stale (older than max_age_hours).
    
    Args:
        year: Recruiting class year
        filepath: Path to the cache file (optional, will use year-specific if not provided)
        max_age_hours: Maximum age in hours before data is considered stale
    
    Returns:
        True if cache doesn't exist or is stale, False otherwise
    """
    from pathlib import Path
    
    if filepath is None:
        if year is None:
            year = datetime.now().year
        filepath = f"data/recruiting_{year}.json"
    
    cache_file = Path(filepath)
    
    # If cache doesn't exist, it's stale
    if not cache_file.exists():
        return True
    
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        # Check if fetched_at timestamp exists
        if 'fetched_at' not in data:
            return True
        
        # Parse the timestamp and check age
        fetched_at = datetime.fromisoformat(data['fetched_at'].replace('Z', '+00:00'))
        age = datetime.utcnow() - fetched_at.replace(tzinfo=None)
        age_hours = age.total_seconds() / 3600
        
        return age_hours > max_age_hours
        
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"⚠️  Error reading cache: {e}")
        return True


def update_cache_if_needed(year=None, filepath=None, max_age_hours=24, force=False):
    """
    Update the cache if it's stale or if force=True.
    
    Args:
        year: Year to fetch (defaults to current year)
        filepath: Path to the cache file (optional, will use year-specific if not provided)
        max_age_hours: Maximum age in hours before data is considered stale
        force: If True, update cache regardless of age
    
    Returns:
        dict with keys:
            - 'updated': bool indicating if cache was updated
            - 'success': bool indicating if update was successful (if attempted)
            - 'error': error message if update failed
            - 'age_hours': age of data in hours (if cache exists)
    """
    from pathlib import Path
    
    if year is None:
        year = datetime.now().year
    
    if filepath is None:
        filepath = f"data/recruiting_{year}.json"
    
    result = {
        'updated': False,
        'success': True,
        'error': None,
        'age_hours': None
    }
    
    # Calculate current cache age
    cache_file = Path(filepath)
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            if 'fetched_at' in data:
                fetched_at = datetime.fromisoformat(data['fetched_at'].replace('Z', '+00:00'))
                age = datetime.utcnow() - fetched_at.replace(tzinfo=None)
                result['age_hours'] = age.total_seconds() / 3600
        except Exception:
            pass
    
    # Check if update is needed
    if force or is_cache_stale(year, filepath, max_age_hours):
        print(f"🔄 Cache is stale or force update requested. Updating...")
        try:
            data = fetch_recruiting_data(year)
            save_to_cache(data, year, filepath)
            result['updated'] = True
            result['success'] = True
            result['age_hours'] = 0
            print(f"✅ Cache updated successfully")
        except Exception as e:
            print(f"❌ Error updating cache: {e}")
            result['updated'] = True
            result['success'] = False
            result['error'] = str(e)
    else:
        print(f"✓ Cache is fresh (age: {result['age_hours']:.1f} hours)")
    
    return result


if __name__ == "__main__":
    # When run directly, fetch and save to cache
    import sys
    
    # Allow year to be passed as command line argument
    year = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    data = fetch_recruiting_data(year)
    save_to_cache(data)
    
    # Print summary
    print("\n" + "="*60)
    print("RECRUITING SUMMARY:")
    print("="*60)
    print(f"Year: {data['year']}")
    print(f"Classification: {data['classification']}")
    print(f"Total Recruits: {data['total_recruits']}")
    
    # Show sample recruit
    if data['recruits']:
        print("\nSAMPLE RECRUIT:")
        print(json.dumps(data['recruits'][0], indent=2))
    
    # Show position breakdown
    positions = {}
    for recruit in data['recruits']:
        pos = recruit.get('position') or 'Unknown'
        positions[pos] = positions.get(pos, 0) + 1
    
    print("\nPOSITION BREAKDOWN:")
    for pos, count in sorted(positions.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {pos}: {count}")
    
    # Show star breakdown
    stars_breakdown = {}
    for recruit in data['recruits']:
        star_count = recruit.get('stars') or 0
        stars_breakdown[star_count] = stars_breakdown.get(star_count, 0) + 1
    
    print("\nSTAR BREAKDOWN:")
    for stars in sorted(stars_breakdown.keys(), reverse=True):
        if stars > 0:
            print(f"  {stars}★: {stars_breakdown[stars]}")
    
    # Show top committed teams
    teams = {}
    for recruit in data['recruits']:
        team = recruit.get('committed_to') or 'Uncommitted'
        teams[team] = teams.get(team, 0) + 1
    
    print("\nTOP COMMITTED TEAMS:")
    for team, count in sorted(teams.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {team}: {count}")
