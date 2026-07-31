# MyTwinMind
My TwinMind Files

## TwinMind memory export

Create a local virtual environment and install everything the scraper needs:

```powershell
python setup_venv.py
```

You can rerun that command later to repair or update dependencies. It reuses the
existing `.venv`; use `python setup_venv.py --recreate` only after deactivating
the environment if you intentionally want to rebuild it from scratch.

Activate it in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Save a TwinMind browser session once. This opens a normal Chrome window with a
dedicated local profile under `.auth/` because Google often blocks OAuth inside
automated browser login flows.

```powershell
python scrape_twinmind_memories.py --login
```

Complete the Google/TwinMind login in that Chrome window, close Chrome fully, and
then return to the terminal and press Enter. The scraper will reuse that profile
for future exports.

Test one memory export with extra logging:

```powershell
python scrape_twinmind_memories.py --limit 1 --debug
```

Export memories to Markdown:

```powershell
python scrape_twinmind_memories.py --output memories
```

The default `memories/` export directory is ignored by git because exported
Markdown can contain private TwinMind memory content. Treat exported memories as
local personal data, not source files.

Each export also maintains `twinmind_memories.db`, a SQLite ledger containing
the link and title of every attempted memory plus whether its Markdown download
succeeded. The default ledger is also ignored by git. Successful links are
skipped on later runs, while failed or interrupted downloads remain eligible for
retry. Use `--database PATH` to put the ledger elsewhere:

```powershell
python scrape_twinmind_memories.py --output memories --database ..\twinmind-private\memories.db
```

If you use a custom `--output` directory, `--database` path, or `--log-database`
path, keep it outside tracked source paths or add it to `.gitignore` before
exporting private data.

View a SQLite ledger in a local read-only browser UI:

```powershell
python view_twinmind_db.py
```

Open the printed local URL, then select the `.db` file you want to inspect. The
viewer reads the `memories` table only and does not create, update, or repair
ledger files.

View the operational log database in a local read-only browser UI:

```powershell
python view_twinmind_logs.py
```

Open the printed local URL, then select `twinmind_logs.db` or the custom
database path passed to `--log-database`. The viewer reads the `logs` table only
and does not create, update, or repair log files.

You can also run without activating the virtual environment by calling its Python
directly.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe scrape_twinmind_memories.py --login
.\.venv\Scripts\python.exe scrape_twinmind_memories.py --limit 1 --debug
.\.venv\Scripts\python.exe scrape_twinmind_memories.py --output memories
```

macOS or Linux:

```bash
.venv/bin/python scrape_twinmind_memories.py --login
.venv/bin/python scrape_twinmind_memories.py --limit 1 --debug
.venv/bin/python scrape_twinmind_memories.py --output memories
```

For a privacy-safe export workflow, save the dedicated TwinMind login profile
once with `--login`, run a one-memory smoke test with `--limit 1 --debug`, then
export to the ignored `memories/` directory. Avoid committing auth state,
exports, or local ledgers.

The dedicated Chrome profile lives under `.auth/`, which is ignored by git
because it can contain sensitive session cookies. Do not keep that profile open
in Chrome while scraping; Chrome locks active profiles.

## Command reference

### `setup_venv.py`

Use this script to create or repair the local virtual environment and install
Playwright's Chromium browser.

Arguments:

| Argument | Type | Default | How to use it |
| --- | --- | --- | --- |
| `--venv PATH` | path | `.venv` | Choose the virtual environment directory. |
| `--recreate` | flag | off | Rebuild the virtual environment. Deactivate it first if it is active. |

Examples:

```powershell
python setup_venv.py
python setup_venv.py --venv .venv
python setup_venv.py --recreate
python setup_venv.py --venv ..\twinmind-private\.venv
```

### `scrape_twinmind_memories.py`

Use this script to save a dedicated TwinMind Chrome login profile and export
TwinMind memories to Markdown.

Arguments:

| Argument | Type | Default | How to use it |
| --- | --- | --- | --- |
| `--login` | flag | off | Open normal Chrome with the dedicated TwinMind profile so you can sign in once. |
| `--auth-state PATH` | path | `.auth\twinmind_state.json` | Deprecated compatibility option. Use `--profile-dir` instead. |
| `--profile-dir PATH` | path | `.auth\twinmind_chrome_profile` | Choose the dedicated Chrome profile used for login and scraping. |
| `--browser-channel NAME` | text | `chrome` | Choose the Playwright browser channel used for scraping. |
| `--output PATH` | path | `memories` | Choose where Markdown exports are written. |
| `--database PATH` | path | `twinmind_memories.db` | Choose the SQLite download ledger path. |
| `--log-database PATH` | path | `twinmind_logs.db` | Choose the SQLite operational log database path. |
| `--limit N` | integer | no limit | Export at most `N` memories. Must be positive. |
| `--headless` | flag | off | Run the export browser headlessly after login is already saved. |
| `--overwrite` | flag | off | Reuse an existing Markdown filename for the same sanitized title. |
| `--debug` | flag | off | Print selector, clipboard, scroll, and fallback details. |

Examples:

```powershell
python scrape_twinmind_memories.py --login
python scrape_twinmind_memories.py --login --profile-dir .auth\twinmind_chrome_profile --debug
python scrape_twinmind_memories.py --limit 1 --debug
python scrape_twinmind_memories.py --output memories
python scrape_twinmind_memories.py --output ..\twinmind-private\exports --database ..\twinmind-private\memories.db
python scrape_twinmind_memories.py --output ..\twinmind-private\exports --log-database ..\twinmind-private\logs.db
python scrape_twinmind_memories.py --limit 10 --headless
python scrape_twinmind_memories.py --output memories --overwrite
python scrape_twinmind_memories.py --browser-channel chrome --profile-dir .auth\twinmind_chrome_profile
```

### `view_twinmind_db.py`

Use this script to select and view a TwinMind SQLite download ledger in a local
read-only browser UI.

Arguments:

| Argument | Type | Default | How to use it |
| --- | --- | --- | --- |
| `--host HOST` | text | `127.0.0.1` | Choose the local interface to bind. |
| `--port PORT` | integer | `8765` | Choose the local port. |

Examples:

```powershell
python view_twinmind_db.py
python view_twinmind_db.py --port 8766
```

### `view_twinmind_logs.py`

Use this script to select and view a TwinMind SQLite operational log database in
a local read-only browser UI.

Arguments:

| Argument | Type | Default | How to use it |
| --- | --- | --- | --- |
| `--host HOST` | text | `127.0.0.1` | Choose the local interface to bind. |
| `--port PORT` | integer | `8767` | Choose the local port. |

Examples:

```powershell
python view_twinmind_logs.py
python view_twinmind_logs.py --port 8768
```

## Python function reference

The scripts are primarily command-line tools. The functions below are documented
for maintenance, tests, and small local helper scripts. Functions that accept a
Playwright `page`, `locator`, `item`, `button`, or `target` expect live
Playwright objects from the authenticated TwinMind browser session.

### Data structures

`SectionSpec(name, tab_selector, copy_selector)` describes one copyable TwinMind
memory section.

```python
from scrape_twinmind_memories import SectionSpec

section = SectionSpec("Summary", "#tab-summary", "button.copy")
```

`MemoryRecord(title, source_index, scraped_at, sections)` contains the data that
gets rendered to one Markdown file.

```python
from scrape_twinmind_memories import MemoryRecord

record = MemoryRecord(
    title="Roadmap Review",
    source_index=1,
    scraped_at="2026-07-29T12:00:00+00:00",
    sections={"Summary": "Short summary", "Transcript": "", "Notes": "Next steps"},
)
```

### `setup_venv.py` functions

| Function | Arguments | How to use it | Example |
| --- | --- | --- | --- |
| `is_windows_platform` | `platform: Optional[str] = None` | Return whether a platform string is Windows. Uses `sys.platform` when omitted. | `is_windows_platform("win32")` |
| `venv_python_path` | `venv_dir: Path`, `platform: Optional[str] = None` | Build the expected Python executable path inside a virtual environment. | `venv_python_path(Path(".venv"), "win32")` |
| `activation_command` | `venv_dir: Path`, `platform: Optional[str] = None` | Build the shell activation command shown to the user. | `activation_command(Path(".venv"), "linux")` |
| `display_python_command` | `venv_dir: Path`, `platform: Optional[str] = None` | Build the direct Python command shown to the user. | `display_python_command(Path(".venv"), "win32")` |
| `same_path` | `left: Path`, `right: Path` | Compare two paths after resolving them when possible. | `same_path(Path("."), Path.cwd())` |
| `running_inside_venv` | `venv_dir: Path` | Check whether the current Python process is running inside that virtual environment. | `running_inside_venv(Path(".venv"))` |
| `should_create_virtualenv` | `_venv_dir: Path`, `python_path: Path`, `recreate: bool` | Decide whether setup should create the virtual environment. | `should_create_virtualenv(Path(".venv"), Path(".venv/Scripts/python.exe"), False)` |
| `run_command` | `command: Sequence[str]`, `cwd: Path` | Run a subprocess command in a directory and raise on failure. | `run_command([str(Path(".venv/Scripts/python.exe")), "-m", "pip", "--version"], Path.cwd())` |
| `create_virtualenv` | `venv_dir: Path` | Create a virtual environment with pip. | `create_virtualenv(Path(".venv"))` |
| `setup_environment` | `project_dir: Path`, `venv_dir: Path`, `recreate: bool = False` | Create or reuse the environment, install requirements, and install Chromium. | `setup_environment(Path.cwd(), Path(".venv"), recreate=False)` |
| `print_next_steps` | `venv_dir: Path` | Print activation and scraper commands after setup. | `print_next_steps(Path(".venv"))` |
| `parse_args` | `argv: Optional[Sequence[str]] = None` | Parse setup CLI arguments. | `parse_args(["--venv", ".venv"])` |
| `main` | `argv: Optional[Sequence[str]] = None` | Run the setup command and return an exit code. | `raise SystemExit(main(["--venv", ".venv"]))` |

### `scrape_twinmind_memories.py` pure and local helper functions

| Function | Arguments | How to use it | Example |
| --- | --- | --- | --- |
| `utc_timestamp` | none | Create an ISO UTC timestamp for exported Markdown metadata. | `scraped_at = utc_timestamp()` |
| `sanitize_filename` | `value: str`, `fallback: str = "memory"` | Convert a title into a Windows-safe Markdown filename stem. | `sanitize_filename('Team Sync: "Launch" / Notes?*')` |
| `markdown_escape_title` | `value: str` | Normalize a Markdown H1 title and replace line breaks. | `markdown_escape_title("Roadmap\nReview")` |
| `render_markdown` | `record: MemoryRecord` | Render one memory record to Markdown text. | `markdown = render_markdown(record)` |
| `unique_markdown_path` | `output_dir: Path`, `title: str`, `source_index: int`, `overwrite: bool = False` | Pick an export filename, adding `-2`, `-3`, and so on when needed. | `unique_markdown_path(Path("memories"), "Daily Standup", 1)` |
| `write_memory_markdown` | `record: MemoryRecord`, `output_dir: Path`, `overwrite: bool = False` | Create the output directory and write one Markdown export. | `write_memory_markdown(record, Path("memories"))` |
| `open_memory_database` | `database_path: Path` | Open the SQLite ledger as a context manager and create its schema. | `with open_memory_database(Path("twinmind_memories.db")) as db: ...` |
| `was_successfully_downloaded` | `connection: sqlite3.Connection`, `link: str` | Check whether a memory link already has a successful ledger entry. | `was_successfully_downloaded(db, "https://app.twinmind.com/memory/123")` |
| `record_download` | `connection: sqlite3.Connection`, `link: str`, `title: str`, `successful: bool` | Record a failed or successful attempt without downgrading prior successes. | `record_download(db, link, title, successful=True)` |
| `open_log_database` | `database_path: Path` | Open the SQLite operational log database as a context manager and create its schema. | `with open_log_database(Path("twinmind_logs.db")) as db: ...` |
| `record_log` | `connection: sqlite3.Connection`, `level: str`, `event: str`, `message: str`, optional memory fields | Record one operational log event. | `record_log(db, "info", "memory_written", "Wrote memory.md")` |
| `ScraperLogger` | `connection: sqlite3.Connection`, `debug: bool = False` | Write operational logs to SQLite and print terminal logs. | `logger = ScraperLogger(db, debug=True)` |
| `debug_log` | `enabled: bool`, `message: str`, `logger: Optional[ScraperLogger] = None`, `event: str = "debug"` | Print a flushed debug message only when debugging is enabled, optionally persisting it to the operational log database. | `debug_log(True, "Copied Summary", logger=logger, event="clipboard")` |
| `import_playwright` | none | Import Playwright lazily and show setup guidance if it is missing. | `Error, TimeoutError, sync_playwright = import_playwright()` |
| `windows_chrome_candidates` | none | Build common Windows Chrome executable paths. | `candidates = windows_chrome_candidates()` |
| `find_chrome_executable` | `platform: Optional[str] = None` | Find Google Chrome for manual login on Windows, macOS, or Linux. | `chrome = find_chrome_executable()` |
| `build_manual_login_command` | `chrome_executable: str`, `profile_dir: Path` | Build the Chrome command used for the manual TwinMind login. | `build_manual_login_command("chrome.exe", Path(".auth/twinmind_chrome_profile"))` |
| `quote_command` | `command: Sequence[str]` | Quote command parts with spaces for readable debug output. | `quote_command(["C:\\Program Files\\Chrome\\chrome.exe", "--flag=value"])` |
| `save_login_state` | `profile_dir: Path`, `debug: bool = False` | Launch Chrome for manual login, then wait for Enter after Chrome is closed. | `save_login_state(Path(".auth/twinmind_chrome_profile"), debug=True)` |
| `compact_text` | `value: str` | Collapse repeated whitespace in scraped text. | `compact_text("  Team\\n Sync  ")` |
| `candidate_key` | `text: str`, `source_index: int` | Build a dedupe key from visible memory text or a source index fallback. | `candidate_key("Meeting title", 4)` |

### `scrape_twinmind_memories.py` Playwright helper functions

| Function | Arguments | How to use it | Example |
| --- | --- | --- | --- |
| `click_first_visible` | `locator`, `timeout_ms: int = 5000` | Click the first visible element in a Playwright locator. | `click_first_visible(page.locator("button"), timeout_ms=3000)` |
| `ensure_app_session` | `page`, `timeout_cls` | Open TwinMind and fail clearly if the saved session is missing or expired. | `ensure_app_session(page, TimeoutError)` |
| `click_if_present` | `page`, `selector: str`, `debug: bool`, `label: str` | Try to click an optional selector and log the result when debugging. | `click_if_present(page, ".optional-button", True, "optional button")` |
| `open_memories` | `page`, `timeout_cls`, `debug: bool = False` | Navigate from the TwinMind app shell into the Memories list. | `open_memories(page, TimeoutError, debug=True)` |
| `read_item_title` | `item`, `source_index: int` | Read a visible memory list item's title with selector fallbacks. | `title = read_item_title(item, 1)` |
| `read_item_key` | `item`, `source_index: int` | Read a stable dedupe key from a visible memory item. | `key = read_item_key(item, 1)` |
| `click_memory_item` | `item` | Click a visible memory item using nested target fallbacks. | `click_memory_item(item)` |
| `click_memory_target` | `target` | Click a target, falling back to a DOM click when Playwright actionability fails. | `click_memory_target(item.locator("div").first)` |
| `click_memory_date` | `button` | Click a date group button in the memory sidebar. | `click_memory_date(button)` |
| `read_memory_date_key` | `button`, `source_index: int` | Read a dedupe key for a date group button. | `date_key = read_memory_date_key(button, 2)` |
| `memory_date_is_selected` | `button` | Check whether a date group button appears selected. | `memory_date_is_selected(button)` |
| `memory_list_content` | `page` | Read the current memory list text before switching date groups. | `before = memory_list_content(page)` |
| `wait_for_memory_list_change` | `page`, `previous_content: str` | Wait for the memory list text to change after selecting a date. | `wait_for_memory_list_change(page, before)` |
| `read_clipboard` | `page` | Read browser clipboard text through Playwright. | `text = read_clipboard(page)` |
| `clear_clipboard` | `page` | Clear browser clipboard text before copying a section. | `clear_clipboard(page)` |
| `fallback_section_text` | `page`, `tab_selector: str`, `copy_selector: str` | Extract visible section text from the DOM when clipboard copy fails. | `fallback_section_text(page, "#tab-summary", "button.copy")` |
| `copy_section_text` | `page`, `section: SectionSpec`, `debug: bool = False` | Select a section tab, copy it, and fall back to DOM text if needed. | `copy_section_text(page, section, debug=True)` |
| `scrape_visible_items` | `page`, `database`, `seen`, `output_dir`, `overwrite`, `limit`, `debug`, `written` | Scrape currently visible memories, write Markdown, and update the ledger. | `scrape_visible_items(page, db, set(), Path("memories"), False, 1, True, [])` |
| `scroll_memory_list` | `page`, `debug: bool = False` | Scroll the TwinMind memory list and report whether it moved. | `moved = scroll_memory_list(page, debug=True)` |
| `reset_memory_list_scroll` | `page`, `debug: bool = False` | Reset the memory list scroll position to the top. | `reset_memory_list_scroll(page, debug=True)` |
| `scrape_current_memory_list` | `page`, `database`, `seen`, `output_dir`, `overwrite`, `limit`, `debug`, `written` | Keep scraping and scrolling one date group's current memory list. | `scrape_current_memory_list(page, db, set(), Path("memories"), False, 5, True, [])` |
| `scrape_date_groups` | `page`, `database`, `seen`, `output_dir`, `overwrite`, `limit`, `debug`, `written` | Traverse visible date groups and scrape each memory list, with current-list fallback. | `scrape_date_groups(page, db, set(), Path("memories"), False, None, True, [])` |
| `scrape_memories` | `profile_dir: Path`, `output_dir: Path`, `limit: Optional[int]`, `headless: bool`, `overwrite: bool`, `debug: bool`, `browser_channel: str`, `database_path: Path = DEFAULT_DATABASE_PATH`, `log_database_path: Path = DEFAULT_LOG_DATABASE_PATH` | Run the full authenticated export flow and return written Markdown paths. | `scrape_memories(Path(".auth/twinmind_chrome_profile"), Path("memories"), 1, False, False, True, "chrome")` |
| `parse_args` | `argv: Optional[Sequence[str]] = None` | Parse scraper CLI arguments. | `parse_args(["--limit", "1", "--debug"])` |
| `main` | `argv: Optional[Sequence[str]] = None` | Run login or export from Python and return an exit code. | `raise SystemExit(main(["--limit", "1", "--debug"]))` |
