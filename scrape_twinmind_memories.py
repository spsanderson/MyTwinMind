"""Export TwinMind memories to Markdown files.

Run `python scrape_twinmind_memories.py --login` once to save a browser session,
then run `python scrape_twinmind_memories.py --output memories` to export.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set


LOGIN_URL = "https://app.twinmind.com/login"
APP_ORIGIN = "https://app.twinmind.com"
DEFAULT_AUTH_STATE = Path(".auth") / "twinmind_state.json"
DEFAULT_PROFILE_DIR = Path(".auth") / "twinmind_chrome_profile"
DEFAULT_OUTPUT_DIR = Path("memories")
DEFAULT_DATABASE_PATH = Path("twinmind_memories.db")
DEFAULT_BROWSER_CHANNEL = "chrome"

LOGIN_BUTTON_SELECTOR = r".bg-\[\#0b4f75\]"
GOOGLE_BUTTON_SELECTOR = "button.inline-flex:nth-child(1)"
HAMBURGER_SELECTOR = ".lucide-menu"
MEMORIES_BUTTON_SELECTOR = "div.r-1otgn73:nth-child(2)"
MEMORY_LIST_SELECTOR = "div.size-full > div:nth-child(1) > ul:nth-child(1)"
MEMORY_ITEM_SELECTOR = (
    f"{MEMORY_LIST_SELECTOR} li.mb-4 > div:nth-child(2) > ul:nth-child(1) > li"
)
MEMORY_CLICK_TARGET_SELECTOR = "div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"


@dataclass(frozen=True)
class SectionSpec:
    name: str
    tab_selector: str
    copy_selector: str


@dataclass(frozen=True)
class MemoryRecord:
    title: str
    source_index: int
    scraped_at: str
    sections: Dict[str, str]


SECTIONS: Sequence[SectionSpec] = (
    SectionSpec("Summary", "#tab-summary", "button.select-none:nth-child(3)"),
    SectionSpec("Transcript", "#tab-transcript", ".ml-auto"),
    SectionSpec("Notes", "#tab-notes", r".hover\:bg-accent"),
)


def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sanitize_filename(value: str, fallback: str = "memory") -> str:
    """Return a conservative Markdown filename stem."""
    normalized = re.sub(r"\s+", " ", value).strip()
    normalized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", normalized)
    normalized = re.sub(r"[^A-Za-z0-9._ -]+", "", normalized)
    normalized = re.sub(r"[- ]{2,}", "-", normalized).strip(" .-_")
    if not normalized:
        normalized = fallback
    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    if normalized.upper() in reserved:
        normalized = f"{normalized}-memory"
    return normalized[:120]


def markdown_escape_title(value: str) -> str:
    title = value.strip() or "Untitled Memory"
    return title.replace("\r", " ").replace("\n", " ")


def render_markdown(record: MemoryRecord) -> str:
    lines = [
        f"# {markdown_escape_title(record.title)}",
        "",
        f"- Scraped at: {record.scraped_at}",
        f"- Source index: {record.source_index}",
        "",
    ]
    for section in SECTIONS:
        text = record.sections.get(section.name, "").strip()
        lines.extend([f"## {section.name}", "", text or "_No content copied._", ""])
    return "\n".join(lines).rstrip() + "\n"


def unique_markdown_path(
    output_dir: Path, title: str, source_index: int, overwrite: bool = False
) -> Path:
    stem = sanitize_filename(title, fallback=f"memory-{source_index:04d}")
    candidate = output_dir / f"{stem}.md"
    if overwrite or not candidate.exists():
        return candidate
    for suffix in range(2, 10000):
        candidate = output_dir / f"{stem}-{suffix}.md"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find an unused filename for {title!r}")


def write_memory_markdown(
    record: MemoryRecord, output_dir: Path, overwrite: bool = False
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = unique_markdown_path(output_dir, record.title, record.source_index, overwrite)
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.write_text(render_markdown(record), encoding="utf-8")
    return path


def open_memory_database(database_path: Path) -> sqlite3.Connection:
    """Open the download ledger and create its schema when necessary."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            link TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            successful_download INTEGER NOT NULL DEFAULT 0
                CHECK (successful_download IN (0, 1))
        )
        """
    )
    connection.commit()
    return connection


def was_successfully_downloaded(connection: sqlite3.Connection, link: str) -> bool:
    row = connection.execute(
        "SELECT successful_download FROM memories WHERE link = ?", (link,)
    ).fetchone()
    return bool(row and row[0])


def record_download(
    connection: sqlite3.Connection, link: str, title: str, successful: bool
) -> None:
    """Upsert an attempt without ever changing a successful record to failed."""
    connection.execute(
        """
        INSERT INTO memories (link, title, successful_download)
        VALUES (?, ?, ?)
        ON CONFLICT(link) DO UPDATE SET
            title = excluded.title,
            successful_download = MAX(
                memories.successful_download,
                excluded.successful_download
            )
        """,
        (link, title, int(successful)),
    )
    connection.commit()


def debug_log(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[debug] {message}", flush=True)


def import_playwright():
    try:
        from playwright.sync_api import Error, TimeoutError, sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright could not be imported in this Python environment.\n"
            f"Import error: {exc}\n"
            "Recommended setup: `python setup_venv.py`\n"
            "Or, inside an activated virtual environment, run:\n"
            "  python -m pip install --upgrade --force-reinstall -r requirements.txt\n"
            "  python -m playwright install chromium"
        ) from exc
    return Error, TimeoutError, sync_playwright


def windows_chrome_candidates() -> List[Path]:
    candidates = []
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        if env_name == "LOCALAPPDATA":
            env_value = str(Path.home() / "AppData" / "Local")
        else:
            env_value = os.environ.get(env_name)
        if not env_value:
            continue
        base = Path(env_value)
        candidates.append(base / "Google" / "Chrome" / "Application" / "chrome.exe")
    return candidates


def find_chrome_executable(platform: Optional[str] = None) -> Optional[str]:
    current_platform = platform or sys.platform
    if current_platform.startswith("win"):
        for candidate in windows_chrome_candidates():
            if candidate.exists():
                return str(candidate)
        return shutil.which("chrome") or shutil.which("chrome.exe")
    if current_platform == "darwin":
        app_path = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        if app_path.exists():
            return str(app_path)
        return shutil.which("google-chrome") or shutil.which("chrome")
    return (
        shutil.which("google-chrome")
        or shutil.which("google-chrome-stable")
        or shutil.which("chromium-browser")
        or shutil.which("chromium")
    )


def build_manual_login_command(chrome_executable: str, profile_dir: Path) -> List[str]:
    return [chrome_executable, f"--user-data-dir={profile_dir}", LOGIN_URL]


def quote_command(command: Sequence[str]) -> str:
    return " ".join(f'"{part}"' if " " in part else part for part in command)


def save_login_state(profile_dir: Path, debug: bool = False) -> None:
    chrome_executable = find_chrome_executable()
    if not chrome_executable:
        raise SystemExit(
            "Could not find Google Chrome. Install Chrome, then rerun "
            "`python scrape_twinmind_memories.py --login`, or open Chrome manually with "
            f"`--user-data-dir={profile_dir}` and visit {LOGIN_URL}."
        )

    profile_dir.mkdir(parents=True, exist_ok=True)
    command = build_manual_login_command(chrome_executable, profile_dir.resolve())
    debug_log(debug, f"Launching manual Chrome login: {quote_command(command)}")
    print("Opening a normal Chrome window with a dedicated TwinMind profile.", flush=True)
    print("Complete the Google/TwinMind login there, then close that Chrome window.", flush=True)
    print("After Chrome is fully closed, return here and press Enter.", flush=True)
    subprocess.Popen(command)
    input()
    print(f"Manual Chrome profile is ready at {profile_dir}", flush=True)
    print(
        "If scraping reports the profile is locked, close every Chrome window using "
        "that profile and rerun the scrape command.",
        flush=True,
    )


def click_first_visible(locator, timeout_ms: int = 5000) -> bool:
    deadline = time.monotonic() + timeout_ms / 1000
    last_error: Optional[Exception] = None
    while time.monotonic() < deadline:
        count = locator.count()
        for index in range(count):
            candidate = locator.nth(index)
            try:
                if candidate.is_visible(timeout=250):
                    candidate.click(timeout=1000)
                    return True
            except Exception as exc:  # Playwright element churn is expected here.
                last_error = exc
        time.sleep(0.15)
    if last_error:
        raise last_error
    return False


def ensure_app_session(page, timeout_cls) -> None:
    page.goto(APP_ORIGIN, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    if "/login" in page.url:
        raise RuntimeError(
            "TwinMind session is not authenticated. Run "
            "`python scrape_twinmind_memories.py --login` first."
        )
    try:
        page.locator(HAMBURGER_SELECTOR).first.wait_for(state="visible", timeout=12000)
    except timeout_cls as exc:
        raise RuntimeError(
            "Could not find TwinMind navigation after loading the app. "
            "If your session expired, rerun with `--login`."
        ) from exc


def click_if_present(page, selector: str, debug: bool, label: str) -> bool:
    try:
        locator = page.locator(selector)
        if click_first_visible(locator, timeout_ms=3000):
            debug_log(debug, f"Clicked {label}: {selector}")
            return True
    except Exception as exc:
        debug_log(debug, f"Did not click {label}: {exc}")
    return False


def open_memories(page, timeout_cls, debug: bool = False) -> None:
    ensure_app_session(page, timeout_cls)
    click_first_visible(page.locator(HAMBURGER_SELECTOR), timeout_ms=12000)
    debug_log(debug, f"Clicked hamburger selector {HAMBURGER_SELECTOR}")
    click_first_visible(page.locator(MEMORIES_BUTTON_SELECTOR), timeout_ms=12000)
    debug_log(debug, f"Clicked Memories selector {MEMORIES_BUTTON_SELECTOR}")
    page.locator(MEMORY_LIST_SELECTOR).first.wait_for(state="visible", timeout=15000)


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def candidate_key(text: str, source_index: int) -> str:
    compacted = compact_text(text)
    if compacted:
        return compacted[:500]
    return f"memory-index-{source_index}"


def read_item_title(item, source_index: int) -> str:
    selectors = [MEMORY_CLICK_TARGET_SELECTOR, "[role='button']", "div"]
    for selector in selectors:
        try:
            text = item.locator(selector).first.inner_text(timeout=1000)
            text = compact_text(text)
            if text:
                return text[:180]
        except Exception:
            continue
    try:
        text = compact_text(item.inner_text(timeout=1000))
        if text:
            return text[:180]
    except Exception:
        pass
    return f"Memory {source_index:04d}"


def read_item_key(item, source_index: int) -> str:
    try:
        text = item.inner_text(timeout=1000)
        return candidate_key(text, source_index)
    except Exception:
        return f"memory-index-{source_index}"


def click_memory_item(item) -> None:
    for selector in (MEMORY_CLICK_TARGET_SELECTOR, "[role='button']", "div"):
        target = item.locator(selector).first
        try:
            if target.is_visible(timeout=500):
                click_memory_target(target)
                return
        except Exception:
            continue
    click_memory_target(item)


def click_memory_target(target) -> None:
    """Click a memory even when TwinMind's nested scroller confuses Playwright.

    Opening a memory changes the page layout. Items that remain visible in the
    memories sidebar can then be reported as outside the viewport by
    Playwright's actionability checks, even after it tries to scroll them. A
    native DOM click is an appropriate fallback here because these list items
    are already discovered from TwinMind's visible memories list.
    """
    try:
        target.click(timeout=3000)
    except Exception:
        target.evaluate("element => element.click()")


def read_clipboard(page) -> str:
    return page.evaluate("navigator.clipboard.readText()")


def clear_clipboard(page) -> None:
    page.evaluate("navigator.clipboard.writeText('')")


def fallback_section_text(page, tab_selector: str, copy_selector: str) -> str:
    script = """
    ([tabSelector, copySelector]) => {
      const tab = document.querySelector(tabSelector);
      const controls = tab && tab.getAttribute("aria-controls");
      const controlledPanel = controls ? document.getElementById(controls) : null;
      const activePanels = [
        controlledPanel,
        document.querySelector('[role="tabpanel"][data-state="active"]'),
        document.querySelector('[role="tabpanel"]:not([hidden])'),
        document.querySelector('[data-state="active"]'),
      ].filter(Boolean);
      const copy = document.querySelector(copySelector);
      if (copy) {
        activePanels.push(copy.closest('[role="tabpanel"]'));
        activePanels.push(copy.closest("section"));
        activePanels.push(copy.parentElement && copy.parentElement.parentElement);
      }
      activePanels.push(document.body);
      for (const node of activePanels) {
        if (!node) continue;
        const clone = node.cloneNode(true);
        clone.querySelectorAll("button, nav, aside, svg").forEach((el) => el.remove());
        const text = (clone.innerText || clone.textContent || "").trim();
        if (text) return text;
      }
      return "";
    }
    """
    return page.evaluate(script, [tab_selector, copy_selector]).strip()


def copy_section_text(page, section: SectionSpec, debug: bool = False) -> str:
    page.locator(section.tab_selector).first.click(timeout=8000)
    page.wait_for_timeout(500)
    stale = ""
    try:
        clear_clipboard(page)
    except Exception as exc:
        debug_log(debug, f"Could not clear clipboard before {section.name}: {exc}")
        try:
            stale = read_clipboard(page)
        except Exception:
            stale = ""
    try:
        click_first_visible(page.locator(section.copy_selector), timeout_ms=8000)
        page.wait_for_timeout(600)
        copied = read_clipboard(page).strip()
        if copied and copied != stale:
            debug_log(debug, f"Copied {section.name} via clipboard ({len(copied)} chars).")
            return copied
        if copied and not stale:
            return copied
        debug_log(debug, f"Clipboard was empty or stale for {section.name}; using fallback.")
    except Exception as exc:
        debug_log(debug, f"Clipboard copy failed for {section.name}: {exc}")
    fallback = fallback_section_text(page, section.tab_selector, section.copy_selector)
    debug_log(debug, f"Fallback captured {section.name} ({len(fallback)} chars).")
    return fallback


def scrape_visible_items(
    page,
    database: sqlite3.Connection,
    seen: Set[str],
    output_dir: Path,
    overwrite: bool,
    limit: Optional[int],
    debug: bool,
    written: List[Path],
) -> None:
    item_locator = page.locator(MEMORY_ITEM_SELECTOR)
    count = item_locator.count()
    debug_log(debug, f"Found {count} visible memory candidates.")
    for visible_index in range(count):
        if limit is not None and len(written) >= limit:
            return
        item = page.locator(MEMORY_ITEM_SELECTOR).nth(visible_index)
        title = read_item_title(item, len(seen) + 1)
        key = read_item_key(item, len(seen) + 1)
        if key in seen:
            continue
        seen.add(key)
        source_index = len(seen)
        link = ""
        try:
            click_memory_item(item)
            page.wait_for_timeout(1000)
            link = page.url
            if was_successfully_downloaded(database, link):
                debug_log(debug, f"Already downloaded; skipping {link}")
                continue
            # Record the attempt before extraction so interrupted and failed runs
            # remain eligible to retry next time.
            record_download(database, link, title, successful=False)
            sections = {
                section.name: copy_section_text(page, section, debug) for section in SECTIONS
            }
            record = MemoryRecord(
                title=title,
                source_index=source_index,
                scraped_at=utc_timestamp(),
                sections=sections,
            )
            path = write_memory_markdown(record, output_dir, overwrite=overwrite)
            record_download(database, link, title, successful=True)
            written.append(path)
            print(f"Wrote {path}", flush=True)
        except Exception as exc:
            if link:
                record_download(database, link, title, successful=False)
            print(f"Skipped memory {source_index} ({title!r}): {exc}", file=sys.stderr)


def scroll_memory_list(page, debug: bool = False) -> bool:
    script = """
    (selector) => {
      const list = document.querySelector(selector);
      if (!list) return { moved: false, reason: "missing-list" };
      const before = list.scrollTop;
      const maxTop = Math.max(0, list.scrollHeight - list.clientHeight);
      list.scrollTop = Math.min(maxTop, before + Math.max(250, list.clientHeight * 0.85));
      return {
        moved: list.scrollTop > before,
        before,
        after: list.scrollTop,
        maxTop,
        scrollHeight: list.scrollHeight,
        clientHeight: list.clientHeight
      };
    }
    """
    result = page.evaluate(script, MEMORY_LIST_SELECTOR)
    debug_log(debug, f"Scroll result: {result}")
    if result.get("moved"):
        page.wait_for_timeout(900)
        return True
    page.mouse.wheel(0, 900)
    page.wait_for_timeout(900)
    return False


def scrape_memories(
    profile_dir: Path,
    output_dir: Path,
    limit: Optional[int],
    headless: bool,
    overwrite: bool,
    debug: bool,
    browser_channel: str,
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> List[Path]:
    if not profile_dir.exists():
        raise SystemExit(
            f"Missing Chrome profile at {profile_dir}. Run "
            "`python scrape_twinmind_memories.py --login` first."
        )
    _, TimeoutError, sync_playwright = import_playwright()
    written: List[Path] = []
    seen: Set[str] = set()
    with open_memory_database(database_path) as database, sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel=browser_channel,
            headless=headless,
        )
        context.grant_permissions(["clipboard-read", "clipboard-write"], origin=APP_ORIGIN)
        page = context.pages[0] if context.pages else context.new_page()
        open_memories(page, TimeoutError, debug)
        stagnant_rounds = 0
        while limit is None or len(written) < limit:
            before_seen = len(seen)
            scrape_visible_items(
                page, database, seen, output_dir, overwrite, limit, debug, written
            )
            if limit is not None and len(written) >= limit:
                break
            moved = scroll_memory_list(page, debug)
            if len(seen) == before_seen:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0
            if not moved and stagnant_rounds >= 2:
                break
        context.close()
    return written


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export TwinMind memories to Markdown.")
    parser.add_argument("--login", action="store_true", help="Open a browser and save login state.")
    parser.add_argument(
        "--auth-state",
        type=Path,
        default=DEFAULT_AUTH_STATE,
        help="Deprecated. Use --profile-dir instead.",
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=DEFAULT_PROFILE_DIR,
        help=f"Dedicated Chrome profile directory. Default: {DEFAULT_PROFILE_DIR}",
    )
    parser.add_argument(
        "--browser-channel",
        default=DEFAULT_BROWSER_CHANNEL,
        help=f"Playwright browser channel for scraping. Default: {DEFAULT_BROWSER_CHANNEL}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for Markdown exports. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help=f"SQLite download ledger. Default: {DEFAULT_DATABASE_PATH}",
    )
    parser.add_argument("--limit", type=int, help="Export at most N memories.")
    parser.add_argument("--headless", action="store_true", help="Run export browser headlessly.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing Markdown file with the same sanitized title.",
    )
    parser.add_argument("--debug", action="store_true", help="Print selector and fallback details.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be a positive integer.")
    if args.login:
        save_login_state(args.profile_dir, debug=args.debug)
        return 0
    written = scrape_memories(
        profile_dir=args.profile_dir,
        output_dir=args.output,
        limit=args.limit,
        headless=args.headless,
        overwrite=args.overwrite,
        debug=args.debug,
        browser_channel=args.browser_channel,
        database_path=args.database,
    )
    print(f"Exported {len(written)} TwinMind memories to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
