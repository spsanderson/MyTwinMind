# Copilot Instructions

This repository is a Python scraper for SportNinja with four connected layers:

1. Playwright scraping
2. SQLite normalization and persistence
3. Excel export into `output/`
4. Flask browsing UI

When working in this repo, make the smallest safe change that solves the requested problem while preserving compatibility across those layers.

## Priorities

- Keep diffs small and focused.
- Prefer targeted fixes over refactors.
- Preserve existing CLI, database, export, and route behavior unless explicitly asked to change them.
- Do not introduce new dependencies unless clearly necessary.
- Do not add hardcoded credentials, secrets, tokens, cookies, or API keys.
- Do not commit generated files from `output/` unless explicitly requested.

## Repository map

- `main.py` — CLI entrypoint and scrape orchestration
- `scraper.py` — Playwright login, navigation, statistics extraction, timeline extraction
- `database.py` — SQLite schema, normalization, idempotent save behavior
- `exporter.py` — Excel/XLSX writing and column ordering
- `app.py` — Flask browser for saved data
- `templates/` — Flask templates
- `test_*.py` — pytest tests
- `pytest.ini` — includes the `integration` marker

## Scraper guidance

SportNinja HTML can change, so scraping edits must be conservative.

- Prefer robust selectors over brittle selectors.
- Keep fallback parsing behavior when possible.
- Fail gracefully when optional elements are missing.
- Preserve row shapes expected by downstream code unless a schema change is explicitly requested.
- Do not add anti-bot evasion, access-control bypasses, or aggressive concurrency.

## Cross-layer impact rule

If you change scraped fields, parsed row shape, or naming, check all affected layers:

- `scraper.py`
- `database.py`
- `exporter.py`
- `app.py`
- `templates/`
- tests

Do not update only one layer.

## Database guidance

`database.py` is the normalization boundary.

- Preserve idempotent save behavior.
- Preserve schema compatibility unless explicitly asked to migrate it.
- Do not silently drop data.
- Keep `raw_data` capture unless explicitly asked to remove it.
- Keep helper behavior deterministic.

## Export guidance

When editing `exporter.py`:

- Preserve uppercase column normalization.
- Preserve output naming and workbook structure unless explicitly asked to change them.
- Verify `STATS_COLUMN_ORDER` and `TIMELINE_COLUMN_ORDER` when output fields change.

## Flask guidance

When editing `app.py` or `templates/`:

- Preserve route paths unless explicitly asked to change them.
- Keep SQL parameterized.
- Keep route/template context aligned.
- Avoid unnecessary abstractions.

## Validation

Before finishing, run the most relevant validation available.

Minimum expected command:

```bash
pytest -m "not integration"
```

Also run full `pytest` when feasible.

If live-site validation depends on external credentials or live SportNinja HTML, say clearly what could not be validated.

## Final summaries

When finishing a task, summarize:

- what changed
- why it changed
- files touched
- validation performed
- assumptions
- remaining risk from live-site markup changes, if relevant
