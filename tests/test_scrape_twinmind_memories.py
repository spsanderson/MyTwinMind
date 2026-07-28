import tempfile
import unittest
from pathlib import Path

from scrape_twinmind_memories import (
    MemoryRecord,
    render_markdown,
    sanitize_filename,
    unique_markdown_path,
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


if __name__ == "__main__":
    unittest.main()
