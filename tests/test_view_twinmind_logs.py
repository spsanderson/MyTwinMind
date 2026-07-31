import sqlite3
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from view_twinmind_logs import (
    decode_uploaded_filename,
    LogReadError,
<<<<<<< ours
    LogViewerHandler,
    LogViewerServer,
=======
    MAX_LOG_ROWS,
>>>>>>> theirs
    MAX_UPLOAD_BYTES,
    read_logs,
    read_uploaded_logs,
    resolve_database_path,
    sqlite_read_only_uri,
    validate_uploaded_logs,
)


class ViewTwinMindLogsTests(unittest.TestCase):
    def create_logs(self, database_path: Path) -> None:
        database = sqlite3.connect(database_path)
        try:
            database.execute(
                """
                CREATE TABLE logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    level TEXT NOT NULL,
                    event TEXT NOT NULL,
                    message TEXT NOT NULL,
                    memory_link TEXT,
                    memory_title TEXT,
                    details TEXT
                )
                """
            )
            database.executemany(
                """
                INSERT INTO logs (
                    created_at,
                    level,
                    event,
                    message,
                    memory_link,
                    memory_title,
                    details
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "2026-07-30T12:00:00+00:00",
                        "info",
                        "export_start",
                        "Starting export",
                        None,
                        None,
                        None,
                    ),
                    (
                        "2026-07-30T12:01:00+00:00",
                        "warning",
                        "memory_failed",
                        "Skipped memory",
                        "https://example.test/memory/1",
                        "Daily Standup",
                        "copy failed",
                    ),
                    (
                        "2026-07-30T12:02:00+00:00",
                        "debug",
                        "selector",
                        "Clicked selector",
                        None,
                        None,
                        None,
                    ),
                    (
                        "2026-07-30T12:03:00+00:00",
                        "notice",
                        "custom",
                        "Custom level",
                        None,
                        None,
                        None,
                    ),
                ],
            )
            database.commit()
        finally:
            database.close()

    def read_bytes(self, path: Path) -> bytes:
        return path.read_bytes()

    def test_read_logs_returns_rows_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "logs.db"
            self.create_logs(database_path)

            logs = read_logs(database_path)

            self.assertEqual(
                logs["summary"],
                {"total": 4, "info": 1, "warning": 1, "debug": 1, "other": 1},
            )
            self.assertEqual(
                [row["event"] for row in logs["rows"]],
                ["custom", "selector", "memory_failed", "export_start"],
            )
            self.assertEqual(logs["rows"][1]["level"], "debug")
            self.assertEqual(logs["rows"][2]["memory_title"], "Daily Standup")
            self.assertEqual(logs["rows"][2]["details"], "copy failed")
            self.assertEqual(logs["rows"][3]["memory_link"], "")

    def test_read_uploaded_logs_returns_rows_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "logs.db"
            self.create_logs(database_path)

            logs = read_uploaded_logs("selected.db", self.read_bytes(database_path))

            self.assertEqual(logs["path"], "selected.db")
            self.assertEqual(logs["summary"]["total"], 4)
            self.assertEqual(logs["rows"][0]["event"], "custom")

    def test_read_logs_returns_only_the_newest_bounded_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "logs.db"
            self.create_logs(database_path)
            database = sqlite3.connect(database_path)
            try:
                database.executemany(
                    """
                    INSERT INTO logs (created_at, level, event, message)
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        ("2026-07-31T12:00:00+00:00", "info", f"event-{index}", "message")
                        for index in range(MAX_LOG_ROWS)
                    ],
                )
                database.commit()
            finally:
                database.close()

            logs = read_logs(database_path)

            self.assertEqual(logs["summary"]["total"], MAX_LOG_ROWS + 4)
            self.assertEqual(logs["returned"], MAX_LOG_ROWS)
            self.assertEqual(len(logs["rows"]), MAX_LOG_ROWS)
            self.assertEqual(logs["rows"][0]["event"], f"event-{MAX_LOG_ROWS - 1}")
            self.assertNotIn("export_start", [row["event"] for row in logs["rows"]])

    def test_validate_uploaded_logs_rejects_missing_filename(self):
        with self.assertRaisesRegex(LogReadError, "missing a filename"):
            validate_uploaded_logs("", 1)

    def test_validate_uploaded_logs_rejects_non_db_filename(self):
        with self.assertRaisesRegex(LogReadError, ".db extension"):
            validate_uploaded_logs("logs.sqlite", 1)

    def test_validate_uploaded_logs_rejects_empty_upload(self):
        with self.assertRaisesRegex(LogReadError, "empty"):
            validate_uploaded_logs("logs.db", 0)

    def test_validate_uploaded_logs_rejects_oversized_upload(self):
        with self.assertRaisesRegex(LogReadError, "larger than 100 MB"):
            validate_uploaded_logs("logs.db", MAX_UPLOAD_BYTES + 1)

    def test_decode_uploaded_filename_supports_non_latin_characters(self):
        self.assertEqual(decode_uploaded_filename("%E6%97%A5%E5%BF%97.db"), "日志.db")

    def test_read_uploaded_logs_rejects_invalid_sqlite_bytes(self):
        with self.assertRaisesRegex(LogReadError, "Could not read SQLite"):
            read_uploaded_logs("not-sqlite.db", b"not sqlite")

    def test_read_uploaded_logs_closes_temp_database_before_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "logs.db"
            self.create_logs(database_path)

            logs = read_uploaded_logs("selected.db", self.read_bytes(database_path))

            self.assertEqual(logs["summary"]["total"], 4)

    def test_resolve_database_path_accepts_relative_db_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            database_path = base_dir / "state" / "logs.db"
            database_path.parent.mkdir()
            database_path.touch()

            self.assertEqual(
                resolve_database_path("state/logs.db", base_dir), database_path
            )

    def test_resolve_database_path_rejects_missing_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(LogReadError, "does not exist"):
                resolve_database_path("missing.db", Path(tmp))

    def test_resolve_database_path_rejects_non_db_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.sqlite"
            path.touch()

            with self.assertRaisesRegex(LogReadError, ".db extension"):
                resolve_database_path(str(path), Path(tmp))

    def test_read_logs_rejects_database_without_logs_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "other.db"
            database = sqlite3.connect(database_path)
            try:
                database.execute("CREATE TABLE other (id INTEGER PRIMARY KEY)")
                database.commit()
            finally:
                database.close()

            with self.assertRaisesRegex(LogReadError, "logs table"):
                read_logs(database_path)

    def test_read_logs_rejects_non_sqlite_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "not-sqlite.db"
            database_path.write_text("not sqlite", encoding="utf-8")

            with self.assertRaisesRegex(LogReadError, "Could not read SQLite"):
                read_logs(database_path)

    def test_read_only_uri_does_not_create_missing_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "missing.db"

            with self.assertRaises(sqlite3.OperationalError):
                sqlite3.connect(sqlite_read_only_uri(missing_path), uri=True)

            self.assertFalse(missing_path.exists())

    def test_path_based_logs_endpoint_is_not_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = LogViewerServer(
                ("127.0.0.1", 0), LogViewerHandler, Path(tmp)
            )
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            connection = HTTPConnection("127.0.0.1", server.server_port)
            try:
                connection.request(
                    "POST",
                    "/api/logs",
                    body='{"path": "logs.db"}',
                    headers={"Content-Type": "application/json"},
                )
                response = connection.getresponse()

                self.assertEqual(response.status, 404)
            finally:
                connection.close()
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == "__main__":
    unittest.main()
