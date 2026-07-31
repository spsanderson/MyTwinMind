import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from scrape_twinmind_memories import (
    DEFAULT_LOG_DATABASE_PATH,
    MEMORY_DATE_BUTTON_SELECTOR,
    MEMORY_ITEM_SELECTOR,
    MEMORY_LIST_SELECTOR,
    MemoryRecord,
    ScraperLogger,
    build_manual_login_command,
    click_memory_target,
    display_path,
    is_memory_detail_url,
    open_log_database,
    open_memory_database,
    parse_args,
    quote_command,
    record_log,
    record_download,
    render_markdown,
    sanitize_filename,
    scrape_date_groups,
    scrape_visible_items,
    wait_for_memory_list_change,
    unique_markdown_path,
    was_successfully_downloaded,
    write_memory_markdown,
)


class FakeButton:
    def __init__(self, text, selected=False):
        self.text = text
        self.selected = selected
        self.click_count = 0

    def inner_text(self, timeout=1000):
        return self.text

    def click(self, timeout=3000):
        self.click_count += 1

    def evaluate(self, script):
        self.click_count += 1

    def get_attribute(self, name):
        if name == "aria-selected" and self.selected:
            return "true"
        return None


class FakeLocator:
    def __init__(self, items=None, wait_error=None):
        self.items = items or []
        self.wait_error = wait_error

    @property
    def first(self):
        return self

    def wait_for(self, state="visible", timeout=3000):
        if self.wait_error:
            raise self.wait_error

    def count(self):
        return len(self.items)

    def nth(self, index):
        return self.items[index]

    def inner_text(self, timeout=1000):
        return "current list"


class FakePage:
    def __init__(self, date_buttons, has_date_list=True, wait_for_change_error=None):
        self.date_buttons = date_buttons
        self.has_date_list = has_date_list
        self.wait_for_change_error = wait_for_change_error
        self.waited = []

    def locator(self, selector):
        if selector == MEMORY_DATE_BUTTON_SELECTOR:
            error = None if self.has_date_list else RuntimeError("missing date list")
            return FakeLocator(self.date_buttons, wait_error=error)
        if selector == MEMORY_LIST_SELECTOR:
            return FakeLocator()
        return FakeLocator()

    def wait_for_timeout(self, timeout):
        self.waited.append(timeout)

    def wait_for_function(self, expression, arg, timeout):
        if self.wait_for_change_error:
            raise self.wait_for_change_error
        self.waited.append((expression, arg, timeout))

    def evaluate(self, script, selector):
        return True


class FakeMemoryItem:
    def __init__(self, title, key, link):
        self.title = title
        self.key = key
        self.link = link


class FakeMemoryPage:
    def __init__(self, items):
        self.items = items
        self.url = "https://app.twinmind.com"
        self.back_count = 0
        self.list_wait_count = 0
        self.waited = []

    def locator(self, selector):
        if selector == MEMORY_ITEM_SELECTOR:
            return FakeLocator(self.items)
        if selector == MEMORY_LIST_SELECTOR:
            page = self

            class ListLocator(FakeLocator):
                def wait_for(self, state="visible", timeout=3000):
                    page.list_wait_count += 1

            return ListLocator()
        return FakeLocator()

    def open_memory(self, item):
        self.url = item.link

    def wait_for_timeout(self, timeout):
        self.waited.append(timeout)

    def go_back(self, wait_until="domcontentloaded", timeout=5000):
        self.back_count += 1
        self.url = "https://app.twinmind.com"


class ScrapeTwinMindMemoriesTests(unittest.TestCase):
    def test_memory_item_selector_targets_direct_list_items(self):
        self.assertEqual(
            MEMORY_ITEM_SELECTOR,
            f"{MEMORY_LIST_SELECTOR} > li.mb-4",
        )

    def test_date_button_selector_is_anchored_to_memory_list(self):
        self.assertIn("size-full", MEMORY_DATE_BUTTON_SELECTOR)
        self.assertIn("preceding::ul[li/button][1]", MEMORY_DATE_BUTTON_SELECTOR)
        self.assertNotIn("/html/body", MEMORY_DATE_BUTTON_SELECTOR)

    def test_sanitize_filename_removes_windows_unsafe_characters(self):
        self.assertEqual(
            sanitize_filename(' Team Sync: "Launch" / Notes?* '),
            "Team Sync-Launch-Notes",
        )

    def test_sanitize_filename_uses_fallback_for_empty_titles(self):
        self.assertEqual(sanitize_filename("???", fallback="memory-0001"), "memory-0001")

    def test_unique_markdown_path_deduplicates_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "Daily Standup.md").write_text("old", encoding="utf-8")
            path = unique_markdown_path(output_dir, "Daily Standup", 1)
            self.assertEqual(path.name, "Daily Standup-2.md")

    def test_unique_markdown_path_reuses_name_with_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "Daily Standup.md").write_text("old", encoding="utf-8")
            path = unique_markdown_path(output_dir, "Daily Standup", 1, overwrite=True)
            self.assertEqual(path.name, "Daily Standup.md")

    def test_display_path_returns_absolute_path(self):
        self.assertTrue(Path(display_path(Path("memories.db"))).is_absolute())

    def test_is_memory_detail_url_requires_memory_route(self):
        self.assertTrue(is_memory_detail_url("https://app.twinmind.com/m/abc"))
        self.assertFalse(is_memory_detail_url("https://app.twinmind.com/"))

    def test_render_markdown_contains_all_sections(self):
        record = MemoryRecord(
            title="Roadmap Review",
            source_index=3,
            scraped_at="2026-07-22T12:00:00+00:00",
            sections={
                "Summary": "Summary text",
                "Transcript": "Transcript text",
                "Notes": "Notes text",
            },
        )
        markdown = render_markdown(record)
        self.assertIn("# Roadmap Review", markdown)
        self.assertIn("- Source index: 3", markdown)
        self.assertIn("## Summary\n\nSummary text", markdown)
        self.assertIn("## Transcript\n\nTranscript text", markdown)
        self.assertIn("## Notes\n\nNotes text", markdown)

    def test_write_memory_markdown_creates_one_file(self):
        record = MemoryRecord(
            title="Customer Call",
            source_index=1,
            scraped_at="2026-07-22T12:00:00+00:00",
            sections={
                "Summary": "A concise summary.",
                "Transcript": "Speaker transcript.",
                "Notes": "Action items.",
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = write_memory_markdown(record, Path(tmp))
            self.assertEqual(path.name, "Customer Call.md")
            content = path.read_text(encoding="utf-8")
            self.assertIn("A concise summary.", content)
            self.assertIn("Speaker transcript.", content)
            self.assertIn("Action items.", content)

    def test_build_manual_login_command_uses_profile_and_login_url(self):
        command = build_manual_login_command(
            "chrome.exe", Path(".auth") / "twinmind_chrome_profile"
        )
        self.assertEqual(command[0], "chrome.exe")
        self.assertIn("--user-data-dir=.auth", command[1])
        self.assertEqual(command[2], "https://app.twinmind.com/login")

    def test_quote_command_quotes_parts_with_spaces(self):
        command = quote_command(["C:\\Program Files\\Chrome\\chrome.exe", "--flag=value"])
        self.assertEqual(command, '"C:\\Program Files\\Chrome\\chrome.exe" --flag=value')

    def test_database_records_download_status_and_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "state" / "memories.db"
            with open_memory_database(database_path) as database:
                record_download(database, "https://example.test/memory/1", "First", False)
                self.assertFalse(
                    was_successfully_downloaded(database, "https://example.test/memory/1")
                )
                record_download(database, "https://example.test/memory/1", "Updated", True)
                self.assertTrue(
                    was_successfully_downloaded(database, "https://example.test/memory/1")
                )
                row = database.execute(
                    "SELECT title, successful_download FROM memories"
                ).fetchone()
                self.assertEqual(row, ("Updated", 1))

    def test_database_never_downgrades_successful_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open_memory_database(Path(tmp) / "memories.db") as database:
                link = "https://example.test/memory/2"
                record_download(database, link, "Done", True)
                record_download(database, link, "Done", False)
                self.assertTrue(was_successfully_downloaded(database, link))

    def test_log_database_records_operational_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "state" / "logs.db"
            with open_log_database(database_path) as database:
                record_log(
                    database,
                    "info",
                    "memory_written",
                    "Wrote memory.md",
                    memory_link="https://example.test/memory/1",
                    memory_title="Daily Standup",
                    details="path=memory.md",
                )
                row = database.execute(
                    """
                    SELECT level, event, message, memory_link, memory_title, details
                    FROM logs
                    """
                ).fetchone()

            self.assertEqual(
                row,
                (
                    "info",
                    "memory_written",
                    "Wrote memory.md",
                    "https://example.test/memory/1",
                    "Daily Standup",
                    "path=memory.md",
                ),
            )

    def test_logger_prints_info_to_stdout_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with open_log_database(Path(tmp) / "logs.db") as database:
                logger = ScraperLogger(database, debug=False)
                with redirect_stdout(stdout):
                    logger.info("export_start", "Starting export")
                row = database.execute("SELECT level, event, message FROM logs").fetchone()

            self.assertIn("[info] Starting export", stdout.getvalue())
            self.assertEqual(row, ("info", "export_start", "Starting export"))

    def test_logger_suppresses_debug_stdout_unless_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with open_log_database(Path(tmp) / "logs.db") as database:
                logger = ScraperLogger(database, debug=False)
                with redirect_stdout(stdout):
                    logger.debug_log("selector", "Clicked selector")
                row = database.execute("SELECT level, event, message FROM logs").fetchone()

            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(row, ("debug", "selector", "Clicked selector"))

    def test_logger_prints_debug_stdout_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with open_log_database(Path(tmp) / "logs.db") as database:
                logger = ScraperLogger(database, debug=True)
                with redirect_stdout(stdout):
                    logger.debug_log("selector", "Clicked selector")

            self.assertIn("[debug] Clicked selector", stdout.getvalue())

    def test_logger_prints_warning_to_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with open_log_database(Path(tmp) / "logs.db") as database:
                logger = ScraperLogger(database, debug=False)
                with redirect_stderr(stderr):
                    logger.warning("memory_skipped", "Skipped memory 1")

            self.assertIn("[warning] Skipped memory 1", stderr.getvalue())

    def test_parse_args_supports_log_database_default_and_override(self):
        default_args = parse_args([])
        override_args = parse_args(["--log-database", "data/logs.db"])

        self.assertEqual(default_args.log_database, DEFAULT_LOG_DATABASE_PATH)
        self.assertEqual(override_args.log_database, Path("data/logs.db"))

    def test_click_memory_target_uses_normal_playwright_click(self):
        target = Mock()

        click_memory_target(target)

        target.click.assert_called_once_with(timeout=3000)
        target.evaluate.assert_not_called()

    def test_click_memory_target_falls_back_to_dom_click_outside_viewport(self):
        target = Mock()
        target.click.side_effect = RuntimeError("element is outside of the viewport")

        click_memory_target(target)

        target.evaluate.assert_called_once_with("element => element.click()")

    def test_scrape_date_groups_clicks_each_date_and_delegates_scraping(self):
        buttons = [FakeButton("Today", selected=True), FakeButton("Yesterday")]
        page = FakePage(buttons)
        database = object()
        seen = set()
        written = []
        output_dir = Path("memories")

        def scrape_one_date(*args):
            args[-1].append(Path(f"memory-{len(args[-1])}.md"))

        with patch(
            "scrape_twinmind_memories.scrape_current_memory_list",
            side_effect=scrape_one_date,
        ) as scrape_current:
            scrape_date_groups(
                page, database, seen, output_dir, False, None, False, written
            )

        self.assertEqual([button.click_count for button in buttons], [1, 1])
        self.assertEqual(scrape_current.call_count, 2)
        self.assertEqual(len(page.waited), 1)
        self.assertEqual(page.waited[0][1], [MEMORY_LIST_SELECTOR, "current list"])
        first_call = scrape_current.call_args_list[0].args
        second_call = scrape_current.call_args_list[1].args
        self.assertIs(first_call[1], database)
        self.assertIsNot(first_call[2], seen)
        self.assertIsNot(first_call[2], second_call[2])
        self.assertEqual(first_call[3], output_dir)

    def test_scrape_date_groups_stops_after_global_limit(self):
        buttons = [
            FakeButton("Today", selected=True),
            FakeButton("Yesterday"),
            FakeButton("Older"),
        ]
        page = FakePage(buttons)
        written = []

        def scrape_one_date(*args):
            args[-1].append(Path("memory.md"))

        with patch(
            "scrape_twinmind_memories.scrape_current_memory_list",
            side_effect=scrape_one_date,
        ) as scrape_current:
            scrape_date_groups(
                page, object(), set(), Path("memories"), False, 1, False, written
            )

        self.assertEqual([button.click_count for button in buttons], [1, 0, 0])
        self.assertEqual(scrape_current.call_count, 1)

    def test_scrape_date_groups_skips_duplicate_date_keys(self):
        buttons = [
            FakeButton("Today", selected=True),
            FakeButton("Today"),
            FakeButton("Yesterday"),
        ]
        page = FakePage(buttons)

        with patch("scrape_twinmind_memories.scrape_current_memory_list") as scrape_current:
            scrape_date_groups(
                page, object(), set(), Path("memories"), False, None, False, []
            )

        self.assertEqual([button.click_count for button in buttons], [1, 0, 1])
        self.assertEqual(scrape_current.call_count, 2)

    def test_scrape_date_groups_scrapes_visible_list_when_date_does_not_change(self):
        buttons = [FakeButton("Today", selected=False)]
        page = FakePage(buttons, wait_for_change_error=RuntimeError("same list"))

        with patch("scrape_twinmind_memories.scrape_current_memory_list") as scrape_current:
            scrape_date_groups(
                page, object(), set(), Path("memories"), False, None, False, []
            )

        self.assertEqual(buttons[0].click_count, 1)
        scrape_current.assert_called_once()

    def test_scrape_date_groups_falls_back_to_current_list_when_dates_missing(self):
        page = FakePage([], has_date_list=False)

        with patch("scrape_twinmind_memories.scrape_current_memory_list") as scrape_current:
            scrape_date_groups(
                page, object(), set(), Path("memories"), False, None, False, []
            )

        scrape_current.assert_called_once()

    def test_wait_for_memory_list_change_uses_previous_list_content(self):
        page = Mock()

        wait_for_memory_list_change(page, "old memory")

        page.wait_for_function.assert_called_once()
        args, kwargs = page.wait_for_function.call_args
        self.assertEqual(args[1], [MEMORY_LIST_SELECTOR, "old memory"])
        self.assertEqual(kwargs["timeout"], 10000)

    def test_scrape_visible_items_returns_to_list_after_downloaded_skip(self):
        downloaded = "https://app.twinmind.com/m/already"
        new = "https://app.twinmind.com/m/new"
        page = FakeMemoryPage(
            [
                FakeMemoryItem("Already", "already-key", downloaded),
                FakeMemoryItem("New", "new-key", new),
            ]
        )
        written = []

        with tempfile.TemporaryDirectory() as tmp:
            with open_memory_database(Path(tmp) / "memories.db") as database:
                record_download(database, downloaded, "Already", True)
                with (
                    patch(
                        "scrape_twinmind_memories.click_memory_item",
                        side_effect=page.open_memory,
                    ),
                    patch(
                        "scrape_twinmind_memories.read_item_title",
                        side_effect=lambda item, source_index: item.title,
                    ),
                    patch(
                        "scrape_twinmind_memories.read_item_key",
                        side_effect=lambda item, source_index: item.key,
                    ),
                    patch("scrape_twinmind_memories.copy_section_text", return_value="text"),
                    patch(
                        "scrape_twinmind_memories.write_memory_markdown",
                        return_value=Path("memories/New.md"),
                    ),
                ):
                    with redirect_stdout(io.StringIO()):
                        scrape_visible_items(
                            page,
                            database,
                            set(),
                            Path("memories"),
                            False,
                            1,
                            False,
                            written,
                        )

        self.assertEqual(written, [Path("memories/New.md")])
        self.assertEqual(page.back_count, 2)
        self.assertEqual(page.list_wait_count, 2)

    def test_scrape_visible_items_skips_duplicate_opened_links(self):
        link = "https://app.twinmind.com/m/same"
        page = FakeMemoryPage(
            [
                FakeMemoryItem("First", "first-key", link),
                FakeMemoryItem("Second", "second-key", link),
            ]
        )
        written = []

        with tempfile.TemporaryDirectory() as tmp:
            with open_memory_database(Path(tmp) / "memories.db") as database:
                with (
                    patch(
                        "scrape_twinmind_memories.click_memory_item",
                        side_effect=page.open_memory,
                    ),
                    patch(
                        "scrape_twinmind_memories.read_item_title",
                        side_effect=lambda item, source_index: item.title,
                    ),
                    patch(
                        "scrape_twinmind_memories.read_item_key",
                        side_effect=lambda item, source_index: item.key,
                    ),
                    patch("scrape_twinmind_memories.copy_section_text", return_value="text"),
                    patch(
                        "scrape_twinmind_memories.write_memory_markdown",
                        return_value=Path("memories/First.md"),
                    ) as write_markdown,
                ):
                    with redirect_stdout(io.StringIO()):
                        scrape_visible_items(
                            page,
                            database,
                            set(),
                            Path("memories"),
                            False,
                            None,
                            False,
                            written,
                        )
                rows = database.execute("SELECT link FROM memories").fetchall()

        self.assertEqual(written, [Path("memories/First.md")])
        self.assertEqual(rows, [(link,)])
        self.assertEqual(write_markdown.call_count, 1)
        self.assertEqual(page.back_count, 2)

    def test_scrape_visible_items_skips_when_click_does_not_open_memory_detail(self):
        page = FakeMemoryPage(
            [
                FakeMemoryItem("Home", "home-key", "https://app.twinmind.com/"),
            ]
        )
        written = []

        with tempfile.TemporaryDirectory() as tmp:
            with open_memory_database(Path(tmp) / "memories.db") as database:
                with (
                    patch(
                        "scrape_twinmind_memories.click_memory_item",
                        side_effect=page.open_memory,
                    ),
                    patch(
                        "scrape_twinmind_memories.read_item_title",
                        side_effect=lambda item, source_index: item.title,
                    ),
                    patch(
                        "scrape_twinmind_memories.read_item_key",
                        side_effect=lambda item, source_index: item.key,
                    ),
                    patch("scrape_twinmind_memories.copy_section_text") as copy_section,
                ):
                    with redirect_stderr(io.StringIO()):
                        scrape_visible_items(
                            page,
                            database,
                            set(),
                            Path("memories"),
                            False,
                            None,
                            False,
                            written,
                        )
                rows = database.execute("SELECT link FROM memories").fetchall()

        self.assertEqual(written, [])
        self.assertEqual(rows, [])
        copy_section.assert_not_called()
        self.assertEqual(page.back_count, 0)
        self.assertEqual(page.list_wait_count, 1)


if __name__ == "__main__":
    unittest.main()
