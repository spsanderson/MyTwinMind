import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from scrape_twinmind_memories import (
    MemoryRecord,
    build_manual_login_command,
<<<<<<< ours
    open_memory_database,
=======
    click_memory_target,
>>>>>>> theirs
    quote_command,
    record_download,
    render_markdown,
    sanitize_filename,
    unique_markdown_path,
    was_successfully_downloaded,
    write_memory_markdown,
)


class ScrapeTwinMindMemoriesTests(unittest.TestCase):
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

<<<<<<< ours
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
=======
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
>>>>>>> theirs


if __name__ == "__main__":
    unittest.main()
