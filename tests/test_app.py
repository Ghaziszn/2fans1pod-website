"""
Characterization tests for the 2fans1pod CFB web app.

PURPOSE
-------
Pin the current observable behavior of every route so a refactor can be proven
safe. If a change to app.py / scrapers / data access makes one of these fail,
that change altered behavior the app relies on — intended or not.

GROUND RULES (keep these true through any refactor)
---------------------------------------------------
- No test hits the network. The CFBD API (`requests.get`) and every scraper
  `update_cache_if_needed` are mocked in the `client` fixture.
- Rate limiting is disabled in the test app so repeated calls are deterministic
  (Flask-Limiter is per-process in-memory and would otherwise 429 flakily).
- File-backed routes read the real JSON in `data/`; assertions check the
  response CONTRACT (status + key shape), not exact values, so refreshed data
  files don't break the suite.
"""
import json

import pytest


# --------------------------------------------------------------------------- #
# Test doubles
# --------------------------------------------------------------------------- #
class FakeResponse:
    """Stand-in for a requests.Response from the CFBD API."""

    def __init__(self, payload, status_code=200,
                 url="https://api.collegefootballdata.com/mock"):
        self._payload = payload
        self.status_code = status_code
        self.url = url
        self.text = payload if isinstance(payload, str) else json.dumps(payload)

    def json(self):
        return self._payload


def _noop_update(*args, **kwargs):
    """Replacement for scraper update_cache_if_needed: never touch the network."""
    return {"updated": False, "success": True, "age_hours": 0.0, "error": None}


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def cfbd_payload():
    """Mutable holder so individual tests can set what the mocked CFBD returns."""
    return {"value": [{"mock": True}], "status": 200}


@pytest.fixture
def client(monkeypatch, cfbd_payload):
    import app as app_module

    # 1. Block all outbound HTTP from the CFBD helper.
    def fake_get(url, headers=None, params=None, timeout=None):
        return FakeResponse(cfbd_payload["value"], status_code=cfbd_payload["status"])

    monkeypatch.setattr(app_module.requests, "get", fake_get)

    # 2. Neutralize scraper auto-refresh (imported *inside* the route functions,
    #    so patch the attribute on each scraper module).
    for mod in (
        "scrapers.transfer_portal_fetcher",
        "scrapers.recruiting_fetcher",
        "scrapers.vsin_betting_splits_scraper",
    ):
        monkeypatch.setattr(f"{mod}.update_cache_if_needed", _noop_update,
                            raising=True)

    # 3. Fresh app with no scheduler, no rate limiter.
    application = app_module.create_app()
    application.config.update(TESTING=True, RATELIMIT_ENABLED=False)
    with application.test_client() as c:
        yield c


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
def test_health(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json().get("ok") is True


# --------------------------------------------------------------------------- #
# Static HTML page routes — each renders its template and returns HTML
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", [
    "/",
    "/calculator",
    "/betting",
    "/coaching-power-index",
    "/transfer-portal",
    "/recruiting",
])
def test_page_routes_render_html(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert "text/html" in r.content_type


# --------------------------------------------------------------------------- #
# CFBD-backed JSON routes (network mocked)
# --------------------------------------------------------------------------- #
def test_api_teams_returns_list(client, cfbd_payload):
    cfbd_payload["value"] = [{"school": "Michigan"}, {"school": "Ohio State"}]
    r = client.get("/api/teams?year=2025")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_api_stats_all_teams(client, cfbd_payload):
    cfbd_payload["value"] = [{"team": "Michigan", "statName": "totalYards"}]
    r = client.get("/api/stats?year=2025")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_api_stats_single_team(client, cfbd_payload):
    cfbd_payload["value"] = [{"team": "Michigan", "statName": "totalYards"}]
    r = client.get("/api/stats?team=Michigan&year=2025")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_api_ats_returns_list(client, cfbd_payload):
    cfbd_payload["value"] = [{"team": "Michigan", "ats": "5-3"}]
    r = client.get("/api/ats?year=2025")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_api_lines_requires_week(client):
    r = client.get("/api/lines?year=2025")
    assert r.status_code == 400
    assert "week" in r.get_json().get("error", "").lower()


def test_api_lines_with_week(client, cfbd_payload):
    cfbd_payload["value"] = [{"homeTeam": "Michigan", "lines": []}]
    r = client.get("/api/lines?year=2025&week=5")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


# --------------------------------------------------------------------------- #
# File-backed JSON routes (read real data/*.json)
# --------------------------------------------------------------------------- #
def test_api_redzone(client):
    r = client.get("/api/redzone")
    assert r.status_code == 200
    assert "teams" in r.get_json()


def test_api_opponent_redzone(client):
    r = client.get("/api/opponent_redzone")
    assert r.status_code == 200
    assert "teams" in r.get_json()


def test_api_coaching_power_index(client):
    r = client.get("/api/coaching-power-index")
    assert r.status_code == 200
    assert "coaches" in r.get_json()


def test_api_transfer_portal_wraps_metadata(client):
    r = client.get("/api/transfer-portal?year=2026")
    assert r.status_code == 200
    body = r.get_json()
    assert "metadata" in body
    assert body["metadata"]["auto_refresh_enabled"] is True


def test_api_recruiting_wraps_metadata(client):
    r = client.get("/api/recruiting?year=2026")
    assert r.status_code == 200
    body = r.get_json()
    assert "metadata" in body
    assert "recruits" in body


def test_api_recruiting_missing_year_404(client):
    # No data/recruiting_1900.json exists -> current behavior is 404.
    r = client.get("/api/recruiting?year=1900")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_api_vsin_splits_wraps_metadata(client):
    r = client.get("/api/vsin_splits")
    assert r.status_code == 200
    body = r.get_json()
    assert "metadata" in body
    assert body["metadata"]["auto_refresh_enabled"] is True


# --------------------------------------------------------------------------- #
# Raw data file serving
# --------------------------------------------------------------------------- #
def test_serve_data_file(client):
    r = client.get("/data/sos.json")
    assert r.status_code == 200
