# MyTwinMind
My TwinMind Files

## TwinMind memory export

Create a local virtual environment and install everything the scraper needs:

```powershell
python setup_venv.py
```

Activate it in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Save a TwinMind browser session once:

```powershell
python scrape_twinmind_memories.py --login
```

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

The saved login state lives under `.auth/`, which is ignored by git because it can
contain sensitive session cookies.
