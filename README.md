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

If you use a custom `--output` directory or `--database` path, keep it outside
tracked source paths or add it to `.gitignore` before exporting private data.

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
