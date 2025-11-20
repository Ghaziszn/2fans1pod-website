# CFB Matchup Calculator (Flask + JS + AG Grid)

This is a from-scratch starter. It proxies CollegeFootballData through Flask and renders matchup comparisons with AG Grid.

## 1) Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# then edit .env to set CFBD_API_KEY=...
```

## 2) Run
```bash
python app.py
# open http://127.0.0.1:5000
```

## 3) Tests
```bash
pytest -q
```

## Deploy
- Render/Heroku/Fly.io: set `CFBD_API_KEY` env var; start with `gunicorn app:app`
