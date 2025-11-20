# RedZone Scraper Integration

## Overview
The RedZone scraper fetches red zone offense statistics from cfbstats.com for all FBS teams.

## File Structure
```
cfb_matchup_flask_starter/
├── scrapers/
│   ├── __init__.py
│   └── redzone_scraper.py    # Main scraper
├── data/
│   └── redzone_stats.json    # Cached data (generated)
└── app.py                     # Flask app with /api/redzone endpoint
```

## How to Use

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Scraper
```bash
python -m scrapers.redzone_scraper
```

This will:
- Scrape all FBS teams (~130 teams)
- Save results to `data/redzone_stats.json`
- Take ~2-3 minutes to complete

### 3. Access the Data
The Flask app serves the cached data at:
```
GET /api/redzone
```

Returns:
```json
{
  "scraped_at": "2025-11-20T00:57:00.000000",
  "teams": {
    "Alabama": {
      "Split": "All Games",
      "G": "10",
      "Att": "45",
      "Scores": "38",
      "Pct": "84.4",
      ...
    },
    ...
  }
}
```

## Updating the Data

Run the scraper manually whenever you need fresh data:
```bash
python -m scrapers.redzone_scraper
```

**Recommended**: Set up a cron job to run daily:
```bash
# Run at 3 AM daily
0 3 * * * cd /path/to/project && /path/to/.venv/bin/python -m scrapers.redzone_scraper
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
