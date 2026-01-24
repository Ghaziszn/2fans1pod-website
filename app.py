import os
import json
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.update(
        JSON_SORT_KEYS=False,
        SEND_FILE_MAX_AGE_DEFAULT=0,
    )

    cache = Cache(app, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300})
    limiter = Limiter(get_remote_address, app=app, default_limits=["60 per minute"])

    CFBD_KEY = os.getenv("CFBD_API_KEY", "").strip()
    if not CFBD_KEY:
        print("WARNING: CFBD_API_KEY not set. Add it in your .env")
    
    # Initialize background scheduler for automatic data updates
    scheduler = None
    enable_scheduler = os.getenv("ENABLE_BACKGROUND_SCHEDULER", "true").lower() == "true"
    
    if enable_scheduler:
        try:
            scheduler = BackgroundScheduler(daemon=True)
            
            # Schedule VSIN scraper to run daily at 6 AM ET
            # Cron format: minute hour day month day_of_week
            schedule = os.getenv("VSIN_SCRAPER_SCHEDULE", "0 6 * * *")  # Default: 6 AM daily
            
            def scheduled_vsin_update():
                """Background task to update VSIN betting splits."""
                try:
                    print("🕐 Running scheduled VSIN data update...")
                    from scrapers.vsin_betting_splits_scraper import update_cache_if_needed
                    
                    result = update_cache_if_needed(force=True)
                    
                    if result['success']:
                        print("✅ Scheduled VSIN update completed successfully")
                    else:
                        print(f"❌ Scheduled VSIN update failed: {result['error']}")
                except Exception as e:
                    print(f"❌ Error in scheduled VSIN update: {e}")
            
            # Parse cron schedule
            parts = schedule.split()
            if len(parts) == 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4]
                )
                scheduler.add_job(
                    func=scheduled_vsin_update,
                    trigger=trigger,
                    id='vsin_scraper',
                    name='VSIN Betting Splits Update',
                    replace_existing=True
                )
                scheduler.start()
                print(f"✅ Background scheduler started. VSIN updates scheduled: {schedule}")
                
                # Shut down scheduler when app exits
                atexit.register(lambda: scheduler.shutdown())
            else:
                print(f"⚠️  Invalid cron schedule format: {schedule}. Scheduler disabled.")
        except Exception as e:
            print(f"⚠️  Failed to initialize background scheduler: {e}")
    else:
        print("ℹ️  Background scheduler disabled (set ENABLE_BACKGROUND_SCHEDULER=true to enable)")


    @app.get("/")
    def index():
        return render_template("home.html")
    
    @app.get("/calculator")
    def calculator():
        return render_template("calculator.html")

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    def cfbd_get(path, params=None):
        url = f"https://api.collegefootballdata.com{path}"
        headers = {"Authorization": f"Bearer {CFBD_KEY}"} if CFBD_KEY else {}
        cache_key = f"{path}?{json.dumps(params, sort_keys=True)}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached, 200
        r = requests.get(url, headers=headers, params=params or {}, timeout=20)
        print(f"[API DEBUG] Fetching: {r.url}")
        if r.status_code == 200:
            cache.set(cache_key, r.json(), timeout=300)
            return r.json(), 200
        return {"error": r.text, "status": r.status_code}, r.status_code

    @app.get("/api/teams")
    @limiter.limit("120/minute")
    def api_teams():
        year = request.args.get("year", type=int, default=2025)
        data, code = cfbd_get("/teams/fbs", {"year": year})
        return (jsonify(data), code)

    @app.get("/api/stats")
    @limiter.limit("120/minute")
    def api_stats():
        team = request.args.get("team", type=str)
        year = request.args.get("year", type=int, default=2025)
        
        # If no team specified, fetch ALL teams (for rankings)
        # Cache this heavily (1 hour) since it's a large payload and doesn't change often
        if not team:
            cache_key = f"all_stats_{year}"
            cached = cache.get(cache_key)
            if cached:
                return jsonify(cached), 200
            
            data, code = cfbd_get("/stats/season", {"year": year})
            if code == 200:
                cache.set(cache_key, data, timeout=3600)
            return (jsonify(data), code)

        data, code = cfbd_get("/stats/season", {"year": year, "team": team})
        return (jsonify(data), code)

    @app.get("/api/redzone")
    @limiter.limit("60/minute")
    def api_redzone():
        """
        Serve cached redzone stats from scraped data.
        Cache is updated manually by running: python -m scrapers.redzone_scraper
        """
        import json
        from pathlib import Path
        
        cache_file = Path("data/redzone_stats.json")
        
        if not cache_file.exists():
            return jsonify({"error": "RedZone data not available. Run scraper first."}), 404
        
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        return jsonify(data), 200

    @app.get("/api/opponent_redzone")
    @limiter.limit("60/minute")
    def api_opponent_redzone():
        """
        Serve cached opponent redzone (defensive) stats from scraped data.
        Cache is updated manually by running: python -m scrapers.opponent_redzone_scraper
        """
        import json
        from pathlib import Path
        
        cache_file = Path("data/opponent_redzone_stats.json")
        
        if not cache_file.exists():
            return jsonify({"error": "Opponent RedZone data not available. Run scraper first."}), 404
        
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        return jsonify(data), 200

    @app.get("/betting")
    def betting():
        """Serve the betting lines page."""
        return render_template("betting.html")

    @app.get("/coaching-power-index")
    def coaching_power_index():
        """Serve the Coaching Power Index page."""
        return render_template("coaching_power_index.html")

    @app.get("/api/coaching-power-index")
    @limiter.limit("60/minute")
    def api_coaching_power_index():
        """
        Serve Coaching Power Index data.
        Returns comprehensive coaching statistics and rankings.
        """
        import json
        from pathlib import Path
        
        cache_file = Path("data/coaching_power_index.json")
        
        if not cache_file.exists():
            return jsonify({"error": "Coaching Power Index data not available."}), 404
        
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        return jsonify(data), 200

    @app.get("/transfer-portal")
    def transfer_portal():
        """Serve the Transfer Portal page."""
        return render_template("transfer_portal.html")

    @app.get("/api/transfer-portal")
    @limiter.limit("60/minute")
    def api_transfer_portal():
        """
        Serve Transfer Portal data with automatic refresh.
        
        Query parameters:
        - year: Year of the offseason (e.g., 2024 for transfers after 2023 season)
        
        Auto-refresh behavior:
        - Checks if cached data is older than 24 hours (configurable via TRANSFER_PORTAL_CACHE_HOURS env var)
        - Automatically re-fetches if data is stale
        - Returns cached data even if fetcher fails (with staleness warning)
        - Includes data_age_hours in response for transparency
        """
        import json
        import os
        from pathlib import Path
        from datetime import datetime
        
        year = request.args.get("year", type=int, default=datetime.now().year)
        cache_file = Path("data/transfer_portal.json")
        max_age_hours = int(os.getenv("TRANSFER_PORTAL_CACHE_HOURS", "24"))
        
        # Try to auto-update if cache is stale
        try:
            from scrapers.transfer_portal_fetcher import update_cache_if_needed
            
            update_result = update_cache_if_needed(
                filepath=str(cache_file),
                max_age_hours=max_age_hours,
                year=year
            )
            
            # Log the update attempt
            if update_result['updated']:
                if update_result['success']:
                    print(f"✅ Transfer portal cache auto-updated successfully")
                else:
                    print(f"⚠️  Transfer portal cache update failed: {update_result['error']}")
        except Exception as e:
            print(f"⚠️  Error during auto-update check: {e}")
            update_result = {'age_hours': None, 'error': str(e)}
        
        # Load and return cached data
        if not cache_file.exists():
            return jsonify({
                "error": "Transfer portal data not available. Run fetcher first: python -m scrapers.transfer_portal_fetcher"
            }), 404
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Calculate data age for response
            data_age_hours = None
            is_stale = False
            
            if 'fetched_at' in data:
                try:
                    fetched_at = datetime.fromisoformat(data['fetched_at'].replace('Z', '+00:00'))
                    age = datetime.utcnow() - fetched_at.replace(tzinfo=None)
                    data_age_hours = age.total_seconds() / 3600
                    is_stale = data_age_hours > max_age_hours
                except Exception:
                    pass
            
            # Add metadata to response
            response_data = {
                **data,
                "metadata": {
                    "data_age_hours": round(data_age_hours, 2) if data_age_hours is not None else None,
                    "is_stale": is_stale,
                    "max_age_hours": max_age_hours,
                    "auto_refresh_enabled": True
                }
            }
            
            # Add warning if data is stale and update failed
            if is_stale and update_result.get('error'):
                response_data["metadata"]["warning"] = f"Data is stale but auto-update failed: {update_result['error']}"
            
            return jsonify(response_data), 200
            
        except Exception as e:
            return jsonify({"error": f"Error reading cache: {str(e)}"}), 500

    @app.get("/recruiting")
    def recruiting():
        """Serve the Recruiting page."""
        return render_template("recruiting.html")

    @app.get("/api/recruiting")
    @limiter.limit("60/minute")
    def api_recruiting():
        """
        Serve Recruiting data with automatic refresh.
        
        Query parameters:
        - year: Recruiting class year (e.g., 2024)
        
        Auto-refresh behavior:
        - Checks if cached data is older than 24 hours (configurable via RECRUITING_CACHE_HOURS env var)
        - Automatically re-fetches if data is stale
        - Returns cached data even if fetcher fails (with staleness warning)
        - Includes data_age_hours in response for transparency
        """
        import json
        import os
        from pathlib import Path
        from datetime import datetime
        
        year = request.args.get("year", type=int, default=datetime.now().year)
        cache_file = Path(f"data/recruiting_{year}.json")
        max_age_hours = int(os.getenv("RECRUITING_CACHE_HOURS", "24"))
        
        # Try to auto-update if cache is stale
        try:
            from scrapers.recruiting_fetcher import update_cache_if_needed
            
            update_result = update_cache_if_needed(
                year=year,
                max_age_hours=max_age_hours
            )
            
            # Log the update attempt
            if update_result['updated']:
                if update_result['success']:
                    print(f"✅ Recruiting cache auto-updated successfully for {year}")
                else:
                    print(f"⚠️  Recruiting cache update failed for {year}: {update_result['error']}")
        except Exception as e:
            print(f"⚠️  Error during auto-update check: {e}")
            update_result = {'age_hours': None, 'error': str(e)}
        
        # Load and return cached data
        if not cache_file.exists():
            return jsonify({
                "error": f"Recruiting data for {year} not available. Run: python -m scrapers.recruiting_fetcher {year}"
            }), 404
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Calculate data age for response
            data_age_hours = None
            is_stale = False
            
            if 'fetched_at' in data:
                try:
                    fetched_at = datetime.fromisoformat(data['fetched_at'].replace('Z', '+00:00'))
                    age = datetime.utcnow() - fetched_at.replace(tzinfo=None)
                    data_age_hours = age.total_seconds() / 3600
                    is_stale = data_age_hours > max_age_hours
                except Exception:
                    pass
            
            # Add metadata to response
            response_data = {
                **data,
                "metadata": {
                    "data_age_hours": round(data_age_hours, 2) if data_age_hours is not None else None,
                    "is_stale": is_stale,
                    "max_age_hours": max_age_hours,
                    "auto_refresh_enabled": True
                }
            }
            
            # Add warning if data is stale and update failed
            if is_stale and update_result.get('error'):
                response_data["metadata"]["warning"] = f"Data is stale but auto-update failed: {update_result['error']}"
            
            return jsonify(response_data), 200
            
        except Exception as e:
            return jsonify({"error": f"Error reading cache: {str(e)}"}), 500

    @app.get("/api/ats")
    @limiter.limit("60/minute")
    def api_ats():
        """
        Fetch against-the-spread records for all teams.
        Example: /api/ats?year=2025
        """
        year = request.args.get("year", type=int, default=2025)
        data, code = cfbd_get("/teams/ats", {"year": year})
        return (jsonify(data), code)

    @app.get("/api/lines")
    @limiter.limit("60/minute")
    def api_lines():
        """
        Fetch betting lines for a specific week.
        Example: /api/lines?year=2025&week=13
        Optional: 
        - &provider=Bovada to filter by provider
        - &seasonType=regular (default) or postseason
        """
        year = request.args.get("year", type=int, default=2025)
        week = request.args.get("week", type=int)
        provider = request.args.get("provider", type=str)  # No default - get all providers
        season_type = request.args.get("seasonType", type=str, default="regular")
        
        if not week:
            return jsonify({"error": "week parameter is required"}), 400
        
        params = {"year": year, "week": week, "seasonType": season_type}
        if provider:  # Only add provider filter if explicitly specified
            params["provider"] = provider
            
        data, code = cfbd_get("/lines", params)
        return (jsonify(data), code)

    @app.get("/api/vsin_splits")
    @limiter.limit("60/minute")
    def api_vsin_splits():
        """
        Serve VSIN betting splits data with automatic refresh.
        
        Auto-refresh behavior:
        - Checks if cached data is older than 24 hours (configurable via VSIN_CACHE_HOURS env var)
        - Automatically re-scrapes if data is stale
        - Returns cached data even if scraper fails (with staleness warning)
        - Includes data_age_hours in response for transparency
        """
        import json
        import os
        from pathlib import Path
        from datetime import datetime
        
        cache_file = Path("data/vsin_betting_splits.json")
        max_age_hours = int(os.getenv("VSIN_CACHE_HOURS", "24"))
        
        # Try to auto-update if cache is stale
        try:
            from scrapers.vsin_betting_splits_scraper import update_cache_if_needed
            
            update_result = update_cache_if_needed(
                filepath=str(cache_file),
                max_age_hours=max_age_hours
            )
            
            # Log the update attempt
            if update_result['updated']:
                if update_result['success']:
                    print(f"✅ VSIN cache auto-updated successfully")
                else:
                    print(f"⚠️  VSIN cache update failed: {update_result['error']}")
        except Exception as e:
            print(f"⚠️  Error during auto-update check: {e}")
            update_result = {'age_hours': None, 'error': str(e)}
        
        # Load and return cached data
        if not cache_file.exists():
            return jsonify({
                "error": "VSIN splits data not available. Run scraper first: python -m scrapers.vsin_betting_splits_scraper"
            }), 404
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Calculate data age for response
            data_age_hours = None
            is_stale = False
            
            if 'scraped_at' in data:
                try:
                    scraped_at = datetime.fromisoformat(data['scraped_at'].replace('Z', '+00:00'))
                    age = datetime.utcnow() - scraped_at.replace(tzinfo=None)
                    data_age_hours = age.total_seconds() / 3600
                    is_stale = data_age_hours > max_age_hours
                except Exception:
                    pass
            
            # Add metadata to response
            response_data = {
                **data,
                "metadata": {
                    "data_age_hours": round(data_age_hours, 2) if data_age_hours is not None else None,
                    "is_stale": is_stale,
                    "max_age_hours": max_age_hours,
                    "auto_refresh_enabled": True
                }
            }
            
            # Add warning if data is stale and update failed
            if is_stale and update_result.get('error'):
                response_data["metadata"]["warning"] = f"Data is stale but auto-update failed: {update_result['error']}"
            
            return jsonify(response_data), 200
            
        except Exception as e:
            return jsonify({"error": f"Error reading cache: {str(e)}"}), 500


    @app.get("/data/<path:filename>")
    def serve_data(filename):
        return send_from_directory("data", filename)

    return app

app = create_app()

if __name__ == "__main__":
    # Get port from environment variable (Render sets this)
    port = int(os.getenv("PORT", 5001))
    # Bind to 0.0.0.0 for Render (allows external connections)
    app.run(host="0.0.0.0", port=port, debug=False)
