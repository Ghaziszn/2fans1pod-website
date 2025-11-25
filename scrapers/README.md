# RedZone Scrapers

## Overview
This directory contains scrapers for fetching red zone statistics from cfbstats.com for all FBS teams:
- **redzone_scraper.py**: Offensive red zone stats (scoring efficiency)
- **opponent_redzone_scraper.py**: Defensive red zone stats (opponent conversion rates)


## File Structure
```
cfb_matchup_flask_starter/
├── scrapers/
│   ├── __init__.py
│   ├── redzone_scraper.py            # Offensive red zone scraper
│   └── opponent_redzone_scraper.py   # Defensive red zone scraper
├── data/
│   ├── redzone_stats.json            # Offensive stats (generated)
│   └── opponent_redzone_stats.json   # Defensive stats (generated)
└── app.py                             # Flask app with API endpoints
```

## How to Use

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Scrapers

**Offensive Red Zone Stats:**
```bash
python -m scrapers.redzone_scraper
```

**Defensive Red Zone Stats (Opponent Conversion):**
```bash
python -m scrapers.opponent_redzone_scraper
```

Each scraper will:
- Scrape all FBS teams (~136 teams)
- Save results to `data/` directory
- Take ~2-3 minutes to complete

### 3. Access the Data
The Flask app serves the cached data at:
```
GET /api/redzone              # Offensive stats
GET /api/opponent_redzone     # Defensive stats (if implemented)
```

Returns:
```json
{
  "scraped_at": "2025-11-21T03:45:05.189135",
  "teams": {
    "Alabama": {
      "Split": "All Games",
      "G": "10",
      "Attempts": "45",
      "Scores": "38",
      "Score %": "84.44",
      "TD": "34",
      "TD %": "75.56",
      "FG": "4",
      "FG %": "8.89"
    },
    ...
  }
}
```

## Updating the Data

Run the scrapers manually whenever you need fresh data:
```bash
python -m scrapers.redzone_scraper
python -m scrapers.opponent_redzone_scraper
```

**Recommended**: Set up a cron job to run daily:
```bash
# Run at 3 AM daily
0 3 * * * cd /path/to/project && /path/to/.venv/bin/python -m scrapers.redzone_scraper
0 3 * * * cd /path/to/project && /path/to/.venv/bin/python -m scrapers.opponent_redzone_scraper
```

## Important Notes

⚠️ **Legal Disclaimer**: This scraper accesses cfbstats.com. Be respectful:
- Don't run it too frequently (once per day is sufficient)
- The site has a broken SSL certificate (hence `verify=False`)
- Check the site's terms of service

## Troubleshooting

**"RedZone data not available" error**:
- Run the scraper first: `python -m scrapers.redzone_scraper`

**SSL warnings**:
- These are expected due to cfbstats.com's certificate issue
- Warnings are suppressed in the code

**Scraper fails**:
- Check your internet connection
- The website might be down or changed its structure
- Check the HTML structure hasn't changed
