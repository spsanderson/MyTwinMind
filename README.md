# MyTwinMind
My TwinMind Files

## TwinMind memory export

Install dependencies:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Save a TwinMind browser session once:

```powershell
python scrape_twinmind_memories.py --login
```

Export memories to Markdown:

```powershell
python scrape_twinmind_memories.py --output memories
```

Useful options:

```powershell
python scrape_twinmind_memories.py --limit 1 --debug
python scrape_twinmind_memories.py --output memories --overwrite
python scrape_twinmind_memories.py --output memories --headless
```

The saved login state lives under `.auth/`, which is ignored by git because it can
contain sensitive session cookies.
