"""
Shared pytest setup for the characterization suite.

These tests exist to LOCK CURRENT BEHAVIOR before any refactor. They are not
a statement of how the app *should* work — they capture how it works today so
that a refactor (service layer, models/, ETL runner, the X data layer) can be
verified to change structure without changing observable behavior.

This module runs at collection time, BEFORE `app.py` is imported anywhere.
That matters: `app.py` calls `create_app()` at module import, which would
otherwise start the APScheduler background thread during the test run. We
disable it here so the suite has no live timers or network jobs.
"""
import os

# Must be set before `app` is imported by any test module.
os.environ.setdefault("ENABLE_BACKGROUND_SCHEDULER", "false")
# Keep CFBD key empty so no test can accidentally authenticate a real call;
# all network is mocked regardless (see the `client` fixture).
os.environ.setdefault("CFBD_API_KEY", "")
