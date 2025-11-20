<!-- Copilot instructions for the CFB Matchup Calculator repo -->
# Copilot instructions — CFB Matchup Calculator

Goal: Help contributors make small, correct changes (features, bug fixes, tests) by calling out the project's architecture, data flows, conventions, and useful file examples.

- Top-level overview
  - This is a small Flask + vanilla JS single-repo app that proxies CollegeFootballData (CFBD) APIs and renders matchup comparisons using AG Grid. The browser talks to Flask endpoints under /api/*, and Flask proxies requests to https://api.collegefootballdata.com.
  - Key files: `app.py` (Flask factory + API proxy), `static/js/app.js` (frontend logic & metrics computation), `templates/index.html` (UI shell), `data/sos.json` (local SOS data), `tests/test_app.py` (simple pytest sanity test), `requirements.txt`.

- Architecture & data flow (quick)
  - Browser → GET /api/teams and /api/stats → Flask in `app.py` → cfbd_get(...) → external CFBD API.
  - Responses from CFBD are cached in-process with `flask_caching.SimpleCache` keyed by `cache_key = f"{path}?{json.dumps(params, sort_keys=True)}"` and TTL ~300s. Keep new cache keys consistent with this pattern.
  - Static SOS is served from `/data/sos.json` via the `serve_data` route and injected into the page as `window.SOS_URL` in the template.

- Important implementation details to preserve
  - `create_app()` factory in `app.py` — tests import and call this. Use the factory pattern for new routes to keep tests and dev server consistent.
  - Rate limiting: `Flask-Limiter` is configured with default limits (e.g., 60/minute; some endpoints override to 120/minute). Respect and reuse the `@limiter.limit` decorator when adding heavy endpoints.
  - Caching: `Cache(app, config={"CACHE_TYPE": "SimpleCache"})` with 300s default; cfbd_get uses `timeout=20` on requests—keep that timeout for external calls.
  - JSON handling: `app.config.update(JSON_SORT_KEYS=False)` is set so response ordering is preserved for UI. Avoid changing this unless intentional.

- Frontend patterns and expectations
  - `static/js/app.js` is imperative DOM code — it expects specific element IDs (e.g., `team1`, `team2`, `loadTeams`, `runCompare`, `status`, `team1Card`, `grid1`, `grid2`). When changing markup, keep these IDs or update JS accordingly.
  - `computeMetricsFromStats(rows)` expects CFBD `/stats/season` rows with `statName` (or `statName.1`) and numeric `value/game` or `statValue`. Familiarize with its mapping and bucket keys (e.g., `points`, `totalYards`, `possessionTime`, `thirdDownConversions`).
  - AG Grid is loaded via CDN in the template. Grids are created with `agGrid.createGrid(...)` and updated by calling `gridApi.setGridOption('rowData', rows)`.

- Developer workflows & commands
  - Create venv, install deps: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` (see `README.md`).
  - Run locally: `python app.py` → open `http://127.0.0.1:5000`.
  - Tests: `pytest -q`. Tests use the factory `create_app()` and a small `healthz` check in `tests/test_app.py`.
  - Deploy: stateless; recommended `gunicorn app:app` and set `CFBD_API_KEY` in the environment.

- Environment and config
  - Required env: `CFBD_API_KEY` (CFBD API token). Optional: `FLASK_RUN_PORT` (default 5000). See `.env.example` usage in `README.md`.

- Quick examples (how Copilot should suggest edits)
  - Adding a new API proxy route: follow `cfbd_get(path, params)` pattern, reuse `cache_key` convention and `limiter.limit` where appropriate.
  - Changing the UI: if you rename an element in `templates/index.html`, update the corresponding ID usage in `static/js/app.js` (search for the ID string to update both places).
  - Extending metrics: `computeMetricsFromStats` builds a `bucket` from `statName` keys. When adding a new metric, add parsing logic there and surface it in `buildComparisonRows`.

- Tests and quick checks before committing
  - Run `pytest -q` (unit tests are minimal). After adding routes, add a small test that uses `create_app()` and `app.test_client()` to exercise the route.

If any of these points are unclear or you want more examples (e.g., a sample test for a new API route or a pointer on how to extend `computeMetricsFromStats`), tell me which area and I'll expand this file.
