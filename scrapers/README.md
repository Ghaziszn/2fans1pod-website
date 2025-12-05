# Data Scrapers

## Overview
This directory contains scrapers for fetching college football data:
- **redzone_scraper.py**: Offensive red zone stats (scoring efficiency)
- **opponent_redzone_scraper.py**: Defensive red zone stats (opponent conversion rates)
- **vsin_betting_splits_scraper.py**: Betting splits data (handle % and bets %) from VSIN


## File Structure
```
cfb_matchup_flask_starter/
├── scrapers/
│   ├── __init__.py
│   ├── redzone_scraper.py                # Offensive red zone scraper
│   ├── opponent_redzone_scraper.py       # Defensive red zone scraper
│   └── vsin_betting_splits_scraper.py    # VSIN betting splits scraper
├── data/
│   ├── redzone_stats.json                # Offensive stats (generated)
│   ├── opponent_redzone_stats.json       # Defensive stats (generated)
│   └── vsin_betting_splits.json          # VSIN betting data (generated)
└── app.py                                 # Flask app with API endpoints
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

**VSIN Betting Splits:**
```bash
python -m scrapers.vsin_betting_splits_scraper
```

Each scraper will:
- Scrape data from the respective source
- Save results to `data/` directory
- Take ~2-3 minutes to complete

### 3. Access the Data
The Flask app serves the cached data at:
```
GET /api/redzone              # Offensive stats
GET /api/opponent_redzone     # Defensive stats
GET /api/vsin_splits          # VSIN betting splits (with auto-refresh)
```

## Auto-Update Feature (VSIN Betting Splits)

The VSIN betting splits data **automatically updates** when stale (older than 24 hours):

### How It Works
1. **Smart Cache**: When you request `/api/vsin_splits`, the API checks if data is older than 24 hours
2. **Auto-Refresh**: If stale, the scraper runs automatically in the background
3. **Graceful Degradation**: If scraper fails, old data is still served with a warning
4. **Background Scheduler**: Optionally runs daily at 6 AM to proactively update data

### Configuration Options

Set these environment variables in your `.env` file:

```bash
# Maximum age before data is considered stale (default: 24 hours)
VSIN_CACHE_HOURS=24

# Enable/disable background scheduler (default: true)
ENABLE_BACKGROUND_SCHEDULER=true

# Cron schedule for background updates (default: 6 AM daily)
# Format: minute hour day month day_of_week
VSIN_SCRAPER_SCHEDULE="0 6 * * *"
```

### API Response Metadata

The `/api/vsin_splits` endpoint includes metadata about data freshness:

```json
{
  "scraped_at": "2025-11-25T12:00:00",
  "games": [...],
  "metadata": {
    "data_age_hours": 2.5,
    "is_stale": false,
    "max_age_hours": 24,
    "auto_refresh_enabled": true
  }
}
```

## Manual Updates

You can still run scrapers manually whenever you need fresh data:
```bash
python -m scrapers.redzone_scraper
python -m scrapers.opponent_redzone_scraper
python -m scrapers.vsin_betting_splits_scraper
```

**For RedZone Data**: Set up a cron job to run daily:
```bash
# Run at 3 AM daily
0 3 * * * cd /path/to/project && /path/to/.venv/bin/python -m scrapers.redzone_scraper
0 3 * * * cd /path/to/project && /path/to/.venv/bin/python -m scrapers.opponent_redzone_scraper
```

**For VSIN Data**: No cron job needed! Auto-update handles it automatically.

## Important Notes

⚠️ **Legal Disclaimer**: These scrapers access external websites. Be respectful:
- Don't run them too frequently (once per day is sufficient)
- cfbstats.com has a broken SSL certificate (hence `verify=False`)
- Check each site's terms of service before use

## Troubleshooting

**"RedZone data not available" error**:
- Run the scraper first: `python -m scrapers.redzone_scraper`

**"VSIN splits data not available" error**:
- The auto-refresh should handle this automatically
- If it persists, run manually: `python -m scrapers.vsin_betting_splits_scraper`
- Check server logs for scraper errors

**SSL warnings**:
- These are expected due to cfbstats.com's certificate issue
- Warnings are suppressed in the code

**Scraper fails**:
- Check your internet connection
- The website might be down or changed its structure
- Check the HTML structure hasn't changed
- For VSIN: The site may have updated their layout

**Background scheduler not working**:
- Ensure `ENABLE_BACKGROUND_SCHEDULER=true` in `.env`
- Check server logs for scheduler initialization messages
- Some deployment platforms (e.g., serverless) don't support background tasks
- The auto-refresh on API requests will still work even if scheduler is disabled
