# AGENTS.md

Guidance for coding agents working in `MyTwinMind`.

## Mission

Make the smallest safe change that preserves the repository's TwinMind memory export flow:

1. create or repair a local virtual environment
2. save a dedicated Chrome/TwinMind login profile under `.auth/`
3. scrape TwinMind memories with Playwright
4. write Markdown exports into `memories/` or the requested output directory
5. track attempted and successful downloads in a SQLite ledger

This is a small repo, but changes to selectors, output formatting, or ledger behavior can affect repeat exports.

## Hard Rules

- Keep diffs small and focused.
- Do not refactor unrelated code.
- Do not rename CLI flags, default paths, database columns, or output conventions unless explicitly requested.
- Do not introduce new dependencies unless clearly necessary.
- Do not convert the sync Playwright flow to async unless explicitly requested.
- Do not remove fallback scraping behavior unless replacing it with something demonstrably safer.
- Do not commit `.auth/`, `.venv/`, `__pycache__/`, generated Markdown exports, or local SQLite ledgers unless explicitly requested.
- Do not add hardcoded credentials, secrets, tokens, cookies, OAuth data, or API keys.
- Do not print secrets, cookies, clipboard contents, or authentication state in logs, tracebacks, tests, or summaries.

## Repository Map

- `scrape_twinmind_memories.py` - CLI entrypoint, Playwright scraping, Markdown rendering, and SQLite ledger behavior
- `setup_venv.py` - local virtual environment creation, dependency installation, and Playwright browser installation
- `requirements.txt` - runtime dependency list
- `README.md` - user setup and export instructions
- `tests/test_scrape_twinmind_memories.py` - unit tests for scraper helpers, Markdown output, click fallback, and ledger behavior
- `tests/test_setup_venv.py` - unit tests for virtual environment helper behavior
- `.gitignore` - local state and generated artifact exclusions
- `.auth/` - ignored dedicated Chrome profile and auth state; treat as sensitive local state
- `memories/` - generated Markdown exports; treat as output
- `twinmind_memories.db` and `data/*.db` - SQLite ledgers; treat as local state unless the task explicitly concerns them

## Default Engineering Stance

Prefer:

- targeted fixes
- stable CLI behavior
- robust selectors with clear fallbacks
- deterministic filename and Markdown rendering
- explicit SQLite writes
- narrow helper functions
- tests around pure helpers and ledger behavior

Avoid:

- speculative abstractions
- style-only rewrites
- broad exception swallowing
- multi-file reorganizations
- changing generated output structure without checking tests and README

## Required Impact Check

If you change memory fields, Markdown structure, filename generation, ledger schema, or CLI defaults, inspect impact across all of these:

- `scrape_twinmind_memories.py`
- `README.md`
- tests under `tests/`
- `.gitignore` when new local outputs or state are introduced

Do not stop after changing only the extraction layer when downstream output or retry behavior is affected.

## Scraper Rules

TwinMind markup and Google-authenticated browser behavior can change. Scraper edits must be conservative.

- Prefer robust selectors and visible-element checks over brittle assumptions.
- Keep fallback text extraction when possible.
- Fail clearly when authentication is missing or expired.
- Preserve the dedicated Chrome profile workflow unless the task explicitly changes authentication behavior.
- Preserve clipboard permission handling when changing copy behavior.
- Keep scraping code easy to debug with `--debug`.
- Do not add aggressive concurrency, anti-bot evasion, or access-control bypass behavior.

When editing `scrape_twinmind_memories.py`:

- keep login/session setup separate from memory navigation
- keep list traversal separate from per-memory extraction
- keep Markdown rendering independent of Playwright operations
- preserve downstream-compatible `MemoryRecord` fields unless explicitly changing output structure
- keep SQLite retry semantics intact: failed or interrupted downloads must remain eligible to retry

## Credentials And Auth

If a task touches authentication, Chrome profile handling, or login flow:

- preserve existing behavior unless a change is requested
- prefer local ignored state over committed state
- never expand secret exposure
- treat `.auth/` as sensitive because it can contain session cookies
- mention any security-sensitive observation in the final summary if relevant

## Database Rules

The SQLite ledger is the retry and idempotency boundary.

When editing ledger behavior:

- preserve `link` as the primary identity unless explicitly asked to migrate
- preserve the rule that successful downloads are never downgraded to failed
- record failed attempts before extraction so interrupted runs can retry
- do not silently drop title or success state
- keep SQL parameterized

If changing schema or ledger semantics, verify:

- `open_memory_database(...)`
- `was_successfully_downloaded(...)`
- `record_download(...)`
- `scrape_visible_items(...)`
- related tests

## Markdown Export Rules

Generated Markdown is user-facing output.

When editing Markdown output:

- preserve section names unless requested
- preserve safe filename behavior for Windows paths
- preserve duplicate filename handling unless requested
- preserve overwrite behavior
- make empty section output explicit and predictable

If changing output fields or formatting, verify:

- `SECTIONS`
- `MemoryRecord`
- `render_markdown(...)`
- `sanitize_filename(...)`
- `unique_markdown_path(...)`
- `write_memory_markdown(...)`
- README examples if commands or defaults change

## Setup Helper Rules

When editing `setup_venv.py`:

- preserve cross-platform path behavior
- do not recreate an active virtual environment
- keep setup messages practical and command-oriented
- preserve `requirements.txt` installation and `playwright install chromium` unless intentionally changing setup
- avoid shell-specific command construction inside subprocess calls

If changing setup behavior, verify:

- `venv_python_path(...)`
- `activation_command(...)`
- `display_python_command(...)`
- `running_inside_venv(...)`
- `setup_environment(...)`
- `tests/test_setup_venv.py`

## Python Standards

- Follow existing repository style.
- Prefer clear and explicit code over clever code.
- Add type hints for new or changed functions when practical.
- Use narrow exception handling where practical.
- Keep comments short and useful.
- Do not add broad exception handling unless justified by browser/page instability or existing local style.

## Setup And Validation

Typical local setup:

```powershell
python setup_venv.py
.\.venv\Scripts\Activate.ps1
```

Typical export smoke test after login:

```powershell
python scrape_twinmind_memories.py --limit 1 --debug
```

### Required Minimum For Code Changes

Run:

```powershell
python -m unittest discover
```

### Also Run When Feasible

If Playwright or live TwinMind behavior changed and a valid login profile is available:

```powershell
python scrape_twinmind_memories.py --limit 1 --debug
```

### If Live App Behavior Is Involved

If full validation depends on external credentials, a valid TwinMind account, browser profile state, clipboard permissions, or live TwinMind markup:

- run the unit tests anyway
- state clearly what could not be validated
- do not claim live scraping was verified unless it actually was

## Change Checklist

Before finishing, confirm:

- the code change is minimal
- CLI defaults and README commands still match
- Markdown output and ledger behavior still match tests
- no secrets or auth state were introduced
- generated artifacts were not unintentionally modified
- relevant tests were run
- the final summary includes assumptions and validation

## File-Specific Guidance

### `scrape_twinmind_memories.py`

- Treat this as the main product surface.
- Preserve CLI ergonomics.
- Be extremely cautious with selector changes.
- Prefer localized parser and navigation fixes.
- Keep browser profile, clipboard, rendering, and ledger concerns separated.
- Maintain retry-safe ledger behavior.

### `setup_venv.py`

- Treat setup output as user-facing.
- Keep commands accurate on Windows and POSIX platforms.
- Do not make destructive changes to an active environment.
- Keep subprocess calls explicit lists of arguments.

### `README.md`

- Keep setup and scrape instructions aligned with actual CLI defaults.
- Mention authentication or local-state implications when workflow changes.
- Keep examples concise and copy-pasteable.

### `tests/`

- Prefer unit tests for pure helpers, ledger behavior, CLI validation, and fallback decisions.
- Avoid tests that require live TwinMind, Google login, or real browser state unless explicitly marked or isolated.

### `.auth/`

- Treat as sensitive generated state.
- Do not inspect, print, copy, commit, or modify it unless the user explicitly asks for auth-profile troubleshooting.

### `memories/`

- Treat as generated output.
- Do not rely on checked-in exports for correctness unless the task explicitly concerns them.

## Final Response Requirements

Your final summary must include:

- what changed
- why it changed
- files touched
- validation performed
- any assumptions
- any remaining risk from external TwinMind markup, credentials, clipboard permissions, or live browser behavior

If validation was limited, say so explicitly.

## Definition Of Done

A task is done only when:

- the requested change is implemented
- downstream impacts were checked
- relevant validation was run or a clear reason is given for skipping it
- results were summarized clearly
- no unrelated code was changed
