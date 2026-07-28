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

The dedicated Chrome profile lives under `.auth/`, which is ignored by git
because it can contain sensitive session cookies. Do not keep that profile open
in Chrome while scraping; Chrome locks active profiles.
