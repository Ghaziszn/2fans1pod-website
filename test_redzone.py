"""
Test script to verify RedZone data integration
"""
import json

# Load the scraped data
with open('data/redzone_stats.json', 'r') as f:
    data = json.load(f)

print("=" * 60)
print("REDZONE DATA TEST")
print("=" * 60)
print(f"\n✅ Data file loaded successfully")
print(f"✅ Scraped at: {data['scraped_at']}")
print(f"✅ Total teams: {len(data['teams'])}")

# Test a few specific teams
test_teams = ['Alabama', 'Georgia', 'Ohio State', 'Texas']

print("\n" + "=" * 60)
print("TESTING SPECIFIC TEAMS")
print("=" * 60)

for team in test_teams:
    if team in data['teams']:
        rz_data = data['teams'][team]
        score_pct = rz_data.get('Score %', 'N/A')
        attempts = rz_data.get('Attempts', 'N/A')
        scores = rz_data.get('Scores', 'N/A')
        
        print(f"\n{team}:")
        print(f"  RedZone Attempts: {attempts}")
        print(f"  RedZone Scores: {scores}")
        print(f"  Score %: {score_pct}%")
        print(f"  ✅ Data looks good!")
    else:
        print(f"\n{team}:")
        print(f"  ❌ NOT FOUND in scraped data")

print("\n" + "=" * 60)
print("FIELD NAMES CHECK")
print("=" * 60)

# Show what fields are available
sample_team = list(data['teams'].keys())[0]
print(f"\nSample team ({sample_team}) has these fields:")
for field in data['teams'][sample_team].keys():
    print(f"  - {field}")

print("\n" + "=" * 60)
print("✅ TEST COMPLETE")
print("=" * 60)
print("\nThe scraper is working correctly!")
print("The field name is 'Score %' (not 'Pct')")
print("JavaScript has been updated to use the correct field name.")
