"""
Transfer Portal Data Fetcher

Fetches transfer portal data from the College Football Data API (CFBD).
Data includes player transfers with origin/destination schools, ratings, and eligibility.
"""

import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def fetch_transfer_portal_data(year=None):
    """
    Fetch transfer portal data from CFBD API.
    
    Args:
        year: Year of the offseason (e.g., 2024 returns transfers from end of 2023 season)
              If None, defaults to current year
    
    Returns:
        Dictionary with transfer portal data
    """
    if year is None:
        # Default to current year
        year = datetime.now().year
    
    CFBD_KEY = os.getenv("CFBD_API_KEY", "").strip()
    if not CFBD_KEY:
        raise ValueError("CFBD_API_KEY not set in .env file")
    
    url = "https://api.collegefootballdata.com/player/portal"
    headers = {"Authorization": f"Bearer {CFBD_KEY}"}
    params = {"year": year}
    
    print(f"Fetching transfer portal data for year {year}...")
    print(f"URL: {url}")
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    transfers = response.json()
    
    print(f"✅ Successfully fetched {len(transfers)} transfers")
    
    # Process and clean the data
    processed_transfers = []
    for transfer in transfers:
        processed_transfer = {
            "season": transfer.get("season"),
            "first_name": transfer.get("firstName"),
            "last_name": transfer.get("lastName"),
            "position": transfer.get("position"),
            "origin": transfer.get("origin"),
            "destination": transfer.get("destination"),
            "transfer_date": transfer.get("transferDate"),
            "rating": transfer.get("rating"),
            "stars": transfer.get("stars"),
            "eligibility": transfer.get("eligibility")
        }
        processed_transfers.append(processed_transfer)
    
    return {
        "fetched_at": datetime.utcnow().isoformat(),
        "year": year,
        "total_transfers": len(processed_transfers),
        "transfers": processed_transfers
    }


def save_to_cache(data, filepath=None):
    """Save fetched data to a JSON file."""
    if filepath is None:
        year = data.get('year', datetime.now().year)
        filepath = f"data/transfer_portal_{year}.json"
        
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"💾 Saved {data['total_transfers']} transfers to {filepath}")


def is_cache_stale(filepath="data/transfer_portal.json", max_age_hours=24):
    """
    Check if the cached data is stale (older than max_age_hours).
    
    Args:
        filepath: Path to the cache file
        max_age_hours: Maximum age in hours before data is considered stale
    
    Returns:
        True if cache doesn't exist or is stale, False otherwise
    """
    from pathlib import Path
    
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


def update_cache_if_needed(filepath="data/transfer_portal.json", max_age_hours=24, force=False, year=None):
    """
    Update the cache if it's stale or if force=True.
    
    Args:
        filepath: Path to the cache file
        max_age_hours: Maximum age in hours before data is considered stale
        force: If True, update cache regardless of age
        year: Year to fetch (defaults to current year)
    
    Returns:
        dict with keys:
            - 'updated': bool indicating if cache was updated
            - 'success': bool indicating if update was successful (if attempted)
            - 'error': error message if update failed
            - 'age_hours': age of data in hours (if cache exists)
    """
    from pathlib import Path
    
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
    if force or is_cache_stale(filepath, max_age_hours):
        print(f"🔄 Cache is stale or force update requested. Updating...")
        try:
            data = fetch_transfer_portal_data(year)
            save_to_cache(data, filepath)
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
    
    data = fetch_transfer_portal_data(year)
    save_to_cache(data)
    
    # Print summary
    print("\n" + "="*60)
    print("TRANSFER PORTAL SUMMARY:")
    print("="*60)
    print(f"Year: {data['year']}")
    print(f"Total Transfers: {data['total_transfers']}")
    
    # Show sample transfer
    if data['transfers']:
        print("\nSAMPLE TRANSFER:")
        print(json.dumps(data['transfers'][0], indent=2))
    
    # Show position breakdown
    positions = {}
    for transfer in data['transfers']:
        pos = transfer.get('position') or 'Unknown'
        positions[pos] = positions.get(pos, 0) + 1
    
    print("\nPOSITION BREAKDOWN:")
    for pos, count in sorted(positions.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {pos}: {count}")
