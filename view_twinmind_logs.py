"""Serve a read-only local web viewer for the TwinMind SQLite logs."""

from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional, Sequence
from urllib.parse import quote


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8767
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TwinMind SQLite Log Viewer</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #667085;
      --border: #d8dee8;
      --accent: #2563eb;
      --accent-dark: #1d4ed8;
      --info-bg: #e8f5ed;
      --info-text: #166534;
      --warn-bg: #fff3d7;
      --warn-text: #92400e;
      --debug-bg: #eef4ff;
      --debug-text: #1e40af;
      --other-bg: #f2f4f7;
      --other-text: #475467;
      --error-bg: #fff1f2;
      --error-text: #9f1239;
      --shadow: 0 16px 40px rgba(21, 30, 46, 0.08);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }

    main {
      width: min(1240px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 36px;
    }

    header {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
    }

    h1 {
      margin: 0;
      font-size: 26px;
      font-weight: 700;
    }

    .subtle {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 14px;
    }

    .path-bar,
    .toolbar,
    .summary,
    .table-wrap {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }

    .path-bar {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      padding: 14px;
      margin-bottom: 14px;
    }

    label {
      display: block;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 6px;
    }

    input,
    select,
    button {
      height: 40px;
      border-radius: 6px;
      border: 1px solid var(--border);
      font: inherit;
    }

    input,
    select {
      width: 100%;
      padding: 0 10px;
      background: #ffffff;
      color: var(--text);
    }

    input[type="file"] {
      padding: 8px 10px;
    }

    button {
      min-width: 92px;
      align-self: end;
      border-color: var(--accent);
      background: var(--accent);
      color: #ffffff;
      font-weight: 700;
      cursor: pointer;
    }

    button:hover {
      background: var(--accent-dark);
    }

    button:disabled {
      cursor: wait;
      opacity: 0.72;
    }

    .message {
      display: none;
      margin: 0 0 14px;
      padding: 10px 12px;
      border-radius: 6px;
      font-size: 14px;
    }

    .message.error {
      display: block;
      background: var(--error-bg);
      color: var(--error-text);
      border: 1px solid #fecdd3;
    }

    .file-status {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 13px;
    }

    .summary {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 1px;
      overflow: hidden;
      margin-bottom: 14px;
    }

    .metric {
      padding: 14px;
      background: #ffffff;
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }

    .metric strong {
      display: block;
      margin-top: 4px;
      font-size: 24px;
    }

    .toolbar {
      display: grid;
      grid-template-columns: minmax(220px, 1fr) 180px;
      gap: 10px;
      padding: 12px;
      margin-bottom: 14px;
    }

    .table-wrap {
      overflow: auto;
    }

    table {
      width: 100%;
      min-width: 1120px;
      border-collapse: collapse;
    }

    th,
    td {
      padding: 11px 12px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }

    th {
      position: sticky;
      top: 0;
      background: #f9fafb;
      color: #344054;
      font-size: 12px;
      text-transform: uppercase;
      cursor: pointer;
      user-select: none;
    }

    tbody tr:hover {
      background: #f8fbff;
    }

    a {
      color: var(--accent);
      overflow-wrap: anywhere;
    }

    .level {
      display: inline-flex;
      min-width: 72px;
      justify-content: center;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      text-transform: capitalize;
    }

    .level.info {
      background: var(--info-bg);
      color: var(--info-text);
    }

    .level.warning {
      background: var(--warn-bg);
      color: var(--warn-text);
    }

    .level.debug {
      background: var(--debug-bg);
      color: var(--debug-text);
    }

    .level.other {
      background: var(--other-bg);
      color: var(--other-text);
    }

    .details,
    .message-cell {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .empty {
      padding: 28px;
      text-align: center;
      color: var(--muted);
    }

    @media (max-width: 720px) {
      main {
        width: min(100% - 20px, 1240px);
        padding-top: 18px;
      }

      header,
      .path-bar,
      .toolbar,
      .summary {
        grid-template-columns: 1fr;
      }

      header {
        display: block;
      }

      button {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>TwinMind Logs</h1>
        <p class="subtle">Read-only view of the local SQLite operational log database.</p>
      </div>
      <p class="subtle" id="loadedPath"></p>
    </header>

    <form class="path-bar" id="fileForm">
      <div>
        <label for="dbFile">SQLite .db file</label>
        <input id="dbFile" name="dbFile" type="file" accept=".db">
        <p class="file-status" id="fileStatus">No file selected.</p>
      </div>
      <button id="loadButton" type="submit" disabled>Load</button>
    </form>

    <p class="message" id="message"></p>

    <section class="summary" aria-label="Log summary">
      <div class="metric"><span>Total</span><strong id="totalCount">0</strong></div>
      <div class="metric"><span>Info</span><strong id="infoCount">0</strong></div>
      <div class="metric"><span>Warning</span><strong id="warningCount">0</strong></div>
      <div class="metric"><span>Debug</span><strong id="debugCount">0</strong></div>
      <div class="metric"><span>Other</span><strong id="otherCount">0</strong></div>
    </section>

    <section class="toolbar" aria-label="Table controls">
      <div>
        <label for="searchInput">Search</label>
        <input id="searchInput" autocomplete="off" placeholder="Filter logs">
      </div>
      <div>
        <label for="levelFilter">Level</label>
        <select id="levelFilter">
          <option value="all">All</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="debug">Debug</option>
          <option value="other">Other</option>
        </select>
      </div>
    </section>

    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th data-sort="created_at">Created</th>
            <th data-sort="level">Level</th>
            <th data-sort="event">Event</th>
            <th data-sort="message">Message</th>
            <th data-sort="memory_title">Memory Title</th>
            <th data-sort="memory_link">Memory Link</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody id="rows">
          <tr><td class="empty" colspan="7">Select a database file to view logs.</td></tr>
        </tbody>
      </table>
    </section>
  </main>

  <script>
    const form = document.getElementById("fileForm");
    const dbFile = document.getElementById("dbFile");
    const fileStatus = document.getElementById("fileStatus");
    const loadButton = document.getElementById("loadButton");
    const message = document.getElementById("message");
    const loadedPath = document.getElementById("loadedPath");
    const totalCount = document.getElementById("totalCount");
    const infoCount = document.getElementById("infoCount");
    const warningCount = document.getElementById("warningCount");
    const debugCount = document.getElementById("debugCount");
    const otherCount = document.getElementById("otherCount");
    const searchInput = document.getElementById("searchInput");
    const levelFilter = document.getElementById("levelFilter");
    const rowsBody = document.getElementById("rows");

    let rows = [];
    let sortKey = "created_at";
    let sortDirection = "desc";

    function showError(text) {
      message.textContent = text;
      message.className = "message error";
    }

    function clearError() {
      message.textContent = "";
      message.className = "message";
    }

    function setSummary(summary) {
      totalCount.textContent = summary.total;
      infoCount.textContent = summary.info;
      warningCount.textContent = summary.warning;
      debugCount.textContent = summary.debug;
      otherCount.textContent = summary.other;
    }

    function normalizedLevel(row) {
      const level = String(row.level || "").toLowerCase();
      return ["info", "warning", "debug"].includes(level) ? level : "other";
    }

    function appendTextCell(row, text, className) {
      const cell = document.createElement("td");
      if (className) {
        cell.className = className;
      }
      cell.textContent = text || "";
      row.appendChild(cell);
    }

    function renderRows() {
      const query = searchInput.value.trim().toLowerCase();
      const filter = levelFilter.value;
      const filtered = rows.filter((row) => {
        const haystack = [
          row.created_at,
          row.level,
          row.event,
          row.message,
          row.memory_link,
          row.memory_title,
          row.details,
        ].map((value) => String(value || "").toLowerCase()).join(" ");
        const matchesQuery = !query || haystack.includes(query);
        const rowLevel = normalizedLevel(row);
        const matchesLevel = filter === "all" || rowLevel === filter;
        return matchesQuery && matchesLevel;
      });

      filtered.sort((left, right) => {
        const a = String(left[sortKey] || "").toLowerCase();
        const b = String(right[sortKey] || "").toLowerCase();
        if (a < b) return sortDirection === "asc" ? -1 : 1;
        if (a > b) return sortDirection === "asc" ? 1 : -1;
        return 0;
      });

      rowsBody.replaceChildren();
      if (!filtered.length) {
        const emptyRow = document.createElement("tr");
        const emptyCell = document.createElement("td");
        emptyCell.className = "empty";
        emptyCell.colSpan = 7;
        emptyCell.textContent = rows.length ? "No rows match the current filters." : "No log rows found.";
        emptyRow.appendChild(emptyCell);
        rowsBody.appendChild(emptyRow);
        return;
      }

      for (const row of filtered) {
        const tr = document.createElement("tr");
        appendTextCell(tr, row.created_at, "");

        const levelCell = document.createElement("td");
        const badge = document.createElement("span");
        const level = normalizedLevel(row);
        badge.className = `level ${level}`;
        badge.textContent = row.level || "other";
        levelCell.appendChild(badge);
        tr.appendChild(levelCell);

        appendTextCell(tr, row.event, "");
        appendTextCell(tr, row.message, "message-cell");
        appendTextCell(tr, row.memory_title, "");

        const linkCell = document.createElement("td");
        if (row.memory_link) {
          const anchor = document.createElement("a");
          anchor.href = row.memory_link;
          anchor.target = "_blank";
          anchor.rel = "noreferrer";
          anchor.textContent = row.memory_link;
          linkCell.appendChild(anchor);
        }
        tr.appendChild(linkCell);

        appendTextCell(tr, row.details, "details");
        rowsBody.appendChild(tr);
      }
    }

    async function loadLogs(file) {
      loadButton.disabled = true;
      loadButton.textContent = "Loading";
      clearError();
      try {
        if (!file) {
          throw new Error("Select a .db file first.");
        }
        const response = await fetch("/api/logs-file", {
          method: "POST",
          headers: { "X-Filename": file.name },
          body: file,
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || "Unable to load database.");
        }
        rows = data.rows || [];
        loadedPath.textContent = data.path || "";
        setSummary(data.summary || { total: 0, info: 0, warning: 0, debug: 0, other: 0 });
        renderRows();
      } catch (error) {
        rows = [];
        loadedPath.textContent = "";
        setSummary({ total: 0, info: 0, warning: 0, debug: 0, other: 0 });
        renderRows();
        showError(error.message);
      } finally {
        loadButton.disabled = false;
        loadButton.textContent = "Load";
        loadButton.disabled = !dbFile.files.length;
      }
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      loadLogs(dbFile.files[0]);
    });

    dbFile.addEventListener("change", () => {
      const file = dbFile.files[0];
      loadButton.disabled = !file;
      fileStatus.textContent = file ? `${file.name} (${file.size.toLocaleString()} bytes)` : "No file selected.";
      clearError();
    });

    searchInput.addEventListener("input", renderRows);
    levelFilter.addEventListener("change", renderRows);

    for (const header of document.querySelectorAll("th[data-sort]")) {
      header.addEventListener("click", () => {
        const nextKey = header.dataset.sort;
        if (sortKey === nextKey) {
          sortDirection = sortDirection === "asc" ? "desc" : "asc";
        } else {
          sortKey = nextKey;
          sortDirection = nextKey === "created_at" ? "desc" : "asc";
        }
        renderRows();
      });
    }
  </script>
</body>
</html>
"""


class LogReadError(ValueError):
    """Raised when a log path cannot be read as a TwinMind log database."""


def validate_uploaded_logs(filename: str, content_length: int) -> None:
    if not filename.strip():
        raise LogReadError("Selected file is missing a filename.")
    if Path(filename).suffix.lower() != ".db":
        raise LogReadError("Choose a file with a .db extension.")
    if content_length <= 0:
        raise LogReadError("Selected database file is empty.")
    if content_length > MAX_UPLOAD_BYTES:
        raise LogReadError("Selected database file is larger than 100 MB.")


def read_uploaded_logs(filename: str, content: bytes) -> dict[str, Any]:
    validate_uploaded_logs(filename, len(content))
    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        logs = read_logs(temp_path)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
    logs["path"] = filename
    return logs


def resolve_database_path(raw_path: str, base_dir: Path) -> Path:
    path_text = raw_path.strip()
    if not path_text:
        raise LogReadError("Enter the path to a .db file.")
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    resolved = path.resolve(strict=False)
    if resolved.suffix.lower() != ".db":
        raise LogReadError("Choose a file with a .db extension.")
    if not resolved.exists():
        raise LogReadError(f"Database does not exist: {resolved}")
    if not resolved.is_file():
        raise LogReadError(f"Database path is not a file: {resolved}")
    return resolved


def sqlite_read_only_uri(database_path: Path) -> str:
    return "file:" + quote(database_path.as_posix(), safe="/:") + "?mode=ro"


def normalize_level(level: str) -> str:
    normalized = level.lower()
    if normalized in {"info", "warning", "debug"}:
        return normalized
    return "other"


def read_logs(database_path: Path) -> dict[str, Any]:
    connection: Optional[sqlite3.Connection] = None
    try:
        connection = sqlite3.connect(sqlite_read_only_uri(database_path), uri=True)
        has_table = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'logs'
            """
        ).fetchone()
        if not has_table:
            raise LogReadError("This database does not contain a logs table.")
        rows = [
            {
                "id": int(id_value),
                "created_at": str(created_at),
                "level": str(level),
                "event": str(event),
                "message": str(message),
                "memory_link": memory_link if memory_link is not None else "",
                "memory_title": memory_title if memory_title is not None else "",
                "details": details if details is not None else "",
            }
            for (
                id_value,
                created_at,
                level,
                event,
                message,
                memory_link,
                memory_title,
                details,
            ) in connection.execute(
                """
                SELECT
                    id,
                    created_at,
                    level,
                    event,
                    message,
                    memory_link,
                    memory_title,
                    details
                FROM logs
                ORDER BY id DESC
                """
            )
        ]
    except LogReadError:
        raise
    except sqlite3.DatabaseError as exc:
        raise LogReadError(f"Could not read SQLite database: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()

    summary = {"total": len(rows), "info": 0, "warning": 0, "debug": 0, "other": 0}
    for row in rows:
        summary[normalize_level(row["level"])] += 1
    return {
        "path": str(database_path),
        "summary": summary,
        "rows": rows,
    }


class LogViewerHandler(BaseHTTPRequestHandler):
    server_version = "TwinMindLogViewer/1.0"

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_text(HTTPStatus.OK, HTML_PAGE, "text/html; charset=utf-8")

    def do_POST(self) -> None:
        if self.path == "/api/logs":
            self.handle_path_logs()
            return
        if self.path == "/api/logs-file":
            self.handle_file_logs()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def handle_path_logs(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise LogReadError("Expected a JSON object.")
            raw_path = payload.get("path")
            if not isinstance(raw_path, str):
                raise LogReadError("Expected path to be a string.")
            database_path = resolve_database_path(raw_path, self.server.base_dir)
            response = read_logs(database_path)
        except json.JSONDecodeError:
            self.send_json(
                HTTPStatus.BAD_REQUEST, {"error": "Request body must be valid JSON."}
            )
            return
        except LogReadError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self.send_json(HTTPStatus.OK, response)

    def handle_file_logs(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(
                HTTPStatus.BAD_REQUEST, {"error": "Content-Length must be a number."}
            )
            return
        if length <= 0:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Selected database file is empty."},
            )
            return
        if length > MAX_UPLOAD_BYTES:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Selected database file is larger than 100 MB."},
            )
            return
        filename = self.headers.get("X-Filename", "")
        try:
            response = read_uploaded_logs(filename, self.rfile.read(length))
        except LogReadError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self.send_json(HTTPStatus.OK, response)

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_text(
        self, status: HTTPStatus, body: str, content_type: str = "text/plain"
    ) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class LogViewerServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler],
        base_dir: Path,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.base_dir = base_dir


def run_server(host: str, port: int, base_dir: Path) -> None:
    server = LogViewerServer((host, port), LogViewerHandler, base_dir)
    url = f"http://{host}:{server.server_port}/"
    print(f"Serving TwinMind log viewer at {url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("", flush=True)
    finally:
        server.server_close()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve a read-only local viewer for the TwinMind SQLite logs."
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Host interface to bind. Default: {DEFAULT_HOST}",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on. Default: {DEFAULT_PORT}",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    run_server(args.host, args.port, Path.cwd())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
