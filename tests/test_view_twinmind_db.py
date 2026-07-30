import sqlite3
import tempfile
import unittest
from pathlib import Path

from view_twinmind_db import (
    LedgerReadError,
    read_ledger,
    resolve_database_path,
    sqlite_read_only_uri,
)


class ViewTwinMindDbTests(unittest.TestCase):
    def create_ledger(self, database_path: Path) -> None:
        database = sqlite3.connect(database_path)
        try:
            database.execute(
                """
                CREATE TABLE memories (
                    link TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    successful_download INTEGER NOT NULL DEFAULT 0
                        CHECK (successful_download IN (0, 1))
                )
                """
            )
            database.executemany(
                """
                INSERT INTO memories (link, title, successful_download)
                VALUES (?, ?, ?)
                """,
                [
                    ("https://example.test/memory/2", "Beta", 0),
                    ("https://example.test/memory/1", "Alpha", 1),
                ],
            )
            database.commit()
        finally:
            database.close()

    def test_read_ledger_returns_rows_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "memories.db"
            self.create_ledger(database_path)

            ledger = read_ledger(database_path)

            self.assertEqual(ledger["summary"], {"total": 2, "successful": 1, "failed": 1})
            self.assertEqual(
                ledger["rows"],
                [
                    {
                        "link": "https://example.test/memory/1",
                        "title": "Alpha",
                        "successful_download": 1,
                    },
                    {
                        "link": "https://example.test/memory/2",
                        "title": "Beta",
                        "successful_download": 0,
                    },
                ],
            )

    def test_resolve_database_path_accepts_relative_db_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            database_path = base_dir / "state" / "memories.db"
            database_path.parent.mkdir()
            database_path.touch()

            self.assertEqual(
                resolve_database_path("state/memories.db", base_dir), database_path
            )

    def test_resolve_database_path_rejects_missing_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(LedgerReadError, "does not exist"):
                resolve_database_path("missing.db", Path(tmp))

    def test_resolve_database_path_rejects_non_db_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memories.sqlite"
            path.touch()

            with self.assertRaisesRegex(LedgerReadError, ".db extension"):
                resolve_database_path(str(path), Path(tmp))

    def test_read_ledger_rejects_database_without_memories_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "other.db"
            database = sqlite3.connect(database_path)
            try:
                database.execute("CREATE TABLE other (id INTEGER PRIMARY KEY)")
                database.commit()
            finally:
                database.close()

            with self.assertRaisesRegex(LedgerReadError, "memories table"):
                read_ledger(database_path)

    def test_read_ledger_rejects_non_sqlite_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "not-sqlite.db"
            database_path.write_text("not sqlite", encoding="utf-8")

            with self.assertRaisesRegex(LedgerReadError, "Could not read SQLite"):
                read_ledger(database_path)

    def test_read_only_uri_does_not_create_missing_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "missing.db"

            with self.assertRaises(sqlite3.OperationalError):
                sqlite3.connect(sqlite_read_only_uri(missing_path), uri=True)

            self.assertFalse(missing_path.exists())


if __name__ == "__main__":
    unittest.main()
