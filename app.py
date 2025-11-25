import os
import json
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.update(
        JSON_SORT_KEYS=False,
        SEND_FILE_MAX_AGE_DEFAULT=timedelta(hours=1),
    )

    cache = Cache(app, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300})
    limiter = Limiter(get_remote_address, app=app, default_limits=["60 per minute"])

    CFBD_KEY = os.getenv("CFBD_API_KEY", "").strip()
    if not CFBD_KEY:
        print("WARNING: CFBD_API_KEY not set. Add it in your .env")

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
        Optional: &provider=Bovada to filter by provider
        """
        year = request.args.get("year", type=int, default=2025)
        week = request.args.get("week", type=int)
        provider = request.args.get("provider", type=str)  # No default - get all providers
        
        if not week:
            return jsonify({"error": "week parameter is required"}), 400
        
        params = {"year": year, "week": week}
        if provider:  # Only add provider filter if explicitly specified
            params["provider"] = provider
            
        data, code = cfbd_get("/lines", params)
        return (jsonify(data), code)

    @app.get("/api/vsin_splits")
    @limiter.limit("60/minute")
    def api_vsin_splits():
        """
        Serve cached VSIN betting splits data.
        Cache is updated manually by running: python -m scrapers.vsin_betting_splits_scraper
        """
        import json
        from pathlib import Path
        
        cache_file = Path("data/vsin_betting_splits.json")
        
        if not cache_file.exists():
            return jsonify({"error": "VSIN splits data not available. Run scraper first."}), 404
        
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        return jsonify(data), 200


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
