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
              