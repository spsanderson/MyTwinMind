"""Serve a read-only local web viewer for the TwinMind SQLite ledger."""

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
DEFAULT_PORT = 8765
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TwinMind SQLite Ledger Viewer</title>
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
      --ok-bg: #e8f5ed;
      --ok-text: #166534;
      --fail-bg: #fff3d7;
      --fail-text: #92400e;
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
      width: min(1180px, calc(100% - 32px));
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
      grid-template-columns: repeat(3, minmax(0, 1fr));
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
      grid-template-columns: minmax(180px, 1fr) 180px;
      gap: 10px;
      padding: 12px;
      margin-bottom: 14px;
    }

    .table-wrap {
      overflow: auto;
    }

    table {
      width: 100%;
      min-width: 760px;
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

    .status {
      display: inline-flex;
      min-width: 86px;
      justify-content: center;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
    }

    .status.success {
      background: var(--ok-bg);
      color: var(--ok-text);
    }

    .status.failed {
      background: var(--fail-bg);
      color: var(--fail-text);
    }

    .empty {
      padding: 28px;
      text-align: center;
      color: var(--muted);
    }

    @media (max-width: 720px) {
      main {
        width: min(100% - 20px, 1180px);
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
        <h1>TwinMind Ledger</h1>
        <p class="subtle">Read-only view of the local SQLite download ledger.</p>
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

    <section class="summary" aria-label="Ledger summary">
      <div class="metric"><span>Total</span><strong id="totalCount">0</strong></div>
      <div class="metric"><span>Successful</span><strong id="successCount">0</strong></div>
      <div class="metric"><span>Failed or interrupted</span><strong id="failedCount">0</strong></div>
    </section>

    <section class="toolbar" aria-label="Table controls">
      <div>
        <label for="searchInput">Search</label>
        <input id="searchInput" autocomplete="off" placeholder="Filter by title or link">
      </div>
      <div>
        <label for="statusFilter">Status</label>
        <select id="statusFilter">
          <option value="all">All</option>
          <option value="success">Successful</option>
          <option value="failed">Failed or interrupted</option>
        </select>
      </div>
    </section>

    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th data-sort="title">Title</th>
            <th data-sort="link">Link</th>
            <th data-sort="successful_download">Status</th>
          </tr>
        </thead>
        <tbody id="rows">
          <tr><td class="empty" colspan="3">Select a database file to view the ledger.</td></tr>
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
    const successCount = document.getElementById("successCount");
    const failedCount = document.getElementById("failedCount");
    const searchInput = document.getElementById("searchInput");
    const statusFilter = document.getElementById("statusFilter");
    const rowsBody = document.getElementById("rows");

    let rows = [];
    let sortKey = "title";
    let sortDirection = "asc";

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
      successCount.textContent = summary.successful;
      failedCount.textContent = summary.failed;
    }

    function statusLabel(value) {
      return Number(value) === 1 ? "Successful" : "Failed";
    }

    function renderRows() {
      const query = searchInput.value.trim().toLowerCase();
      const filter = statusFilter.value;
      const filtered = rows.filter((row) => {
        const matchesQuery = !query ||
          row.title.toLowerCase().includes(query) ||
          row.link.toLowerCase().includes(query);
        const matchesStatus = filter === "all" ||
          (filter === "success" && Number(row.successful_download) === 1) ||
          (filter === "failed" && Number(row.successful_download) !== 1);
        return matchesQuery && matchesStatus;
      });

      filtered.sort((left, right) => {
        const a = String(left[sortKey] ?? "").toLowerCase();
        const b = String(right[sortKey] ?? "").toLowerCase();
        if (a < b) return sortDirection === "asc" ? -1 : 1;
        if (a > b) return sortDirection === "asc" ? 1 : -1;
        return 0;
      });

      rowsBody.replaceChildren();
      if (!filtered.length) {
        const emptyRow = document.createElement("tr");
        const emptyCell = document.createElement("td");
        emptyCell.className = "empty";
        emptyCell.colSpan = 3;
        emptyCell.textContent = rows.length ? "No rows match the current filters." : "No ledger rows found.";
        emptyRow.appendChild(emptyCell);
        rowsBody.appendChild(emptyRow);
        return;
      }

      for (const row of filtered) {
        const tr = document.createElement("tr");

        const title = document.createElement("td");
        title.textContent = row.title;

        const link = document.createElement("td");
        const anchor = document.createElement("a");
        anchor.href = row.link;
        anchor.target = "_blank";
        anchor.rel = "noreferrer";
        anchor.textContent = row.link;
        link.appendChild(anchor);

        const status = document.createElement("td");
        const badge = document.createElement("span");
        const successful = Number(row.successful_download) === 1;
        badge.className = successful ? "status success" : "status failed";
        badge.textContent = statusLabel(row.successful_download);
        status.appendChild(badge);

        tr.append(title, link, status);
        rowsBody.appendChild(tr);
      }
    }

    async function loadLedger(file) {
      loadButton.disabled = true;
      loadButton.textContent = "Loading";
      clearError();
      try {
        if (!file) {
          throw new Error("Select a .db file first.");
        }
        const response = await fetch("/api/ledger-file", {
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
        setSummary(data.summary || { total: 0, successful: 0, failed: 0 });
        renderRows();
      } catch (error) {
        rows = [];
        loadedPath.textContent = "";
        setSummary({ total: 0, successful: 0, failed: 0 });
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
      loadLedger(dbFile.files[0]);
    });

    dbFile.addEventListener("change", () => {
      const file = dbFile.files[0];
      loadButton.disabled = !file;
      fileStatus.textContent = file ? `${file.name} (${file.size.toLocaleString()} bytes)` : "No file selected.";
      clearError();
    });

    searchInput.addEventListener("input", renderRows);
    statusFilter.addEventListener("change", renderRows);

    for (const header of document.querySelectorAll("th[data-sort]")) {
      header.addEventListener("click", () => {
        const nextKey = header.dataset.sort;
        if (sortKey === nextKey) {
          sortDirection = sortDirection === "asc" ? "desc" : "asc";
        } else {
          sortKey = nextKey;
          sortDirection = "asc";
        }
        renderRows();
      });
    }
  </script>
</body>
</html>
"""


class LedgerReadError(ValueError):
    """Raised when a ledger path cannot be read as a TwinMind ledger."""


def validate_uploaded_ledger(filename: str, content_length: int) -> None:
    if not filename.strip():
        raise LedgerReadError("Selected file is missing a filename.")
    if Path(filename).suffix.lower() != ".db":
        raise LedgerReadError("Choose a file with a .db extension.")
    if content_length <= 0:
        raise LedgerReadError("Selected database file is empty.")
    if content_length > MAX_UPLOAD_BYTES:
        raise LedgerReadError("Selected database file is larger than 100 MB.")


def read_uploaded_ledger(filename: str, content: bytes) -> dict[str, Any]:
    validate_uploaded_ledger(filename, len(content))
    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        ledger = read_ledger(temp_path)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
    ledger["path"] = filename
    return ledger


def resolve_database_path(raw_path: str, base_dir: Path) -> Path:
    path_text = raw_path.strip()
    if not path_text:
        raise LedgerReadError("Enter the path to a .db file.")
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    resolved = path.resolve(strict=False)
    if resolved.suffix.lower() != ".db":
        raise LedgerReadError("Choose a file with a .db extension.")
    if not resolved.exists():
        raise LedgerReadError(f"Database does not exist: {resolved}")
    if not resolved.is_file():
        raise LedgerReadError(f"Database path is not a file: {resolved}")
    return resolved


def sqlite_read_only_uri(database_path: Path) -> str:
    return "file:" + quote(database_path.as_posix(), safe="/:") + "?mode=ro"


def read_ledger(database_path: Path) -> dict[str, Any]:
    connection: Optional[sqlite3.Connection] = None
    try:
        connection = sqlite3.connect(sqlite_read_only_uri(database_path), uri=True)
        has_table = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'memories'
            """
        ).fetchone()
        if not has_table:
            raise LedgerReadError("This database does not contain a memories table.")
        rows = [
            {
                "link": str(link),
                "title": str(title),
                "successful_download": int(successful_download),
            }
            for link, title, successful_download in connection.execute(
                """
                SELECT link, title, successful_download
                FROM memories
                ORDER BY title COLLATE NOCASE, link COLLATE NOCASE
                """
            )
        ]
    except LedgerReadError:
        raise
    except sqlite3.DatabaseError as exc:
        raise LedgerReadError(f"Could not read SQLite database: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()

    successful = sum(1 for row in rows if row["successful_download"] == 1)
    failed = len(rows) - successful
    return {
        "path": str(database_path),
        "summary": {
            "total": len(rows),
            "successful": successful,
            "failed": failed,
        },
        "rows": rows,
    }


class LedgerViewerHandler(BaseHTTPRequestHandler):
    server_version = "TwinMindLedgerViewer/1.0"

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_text(HTTPStatus.OK, HTML_PAGE, "text/html; charset=utf-8")

    def do_POST(self) -> None:
        if self.path == "/api/ledger":
            self.handle_path_ledger()
            return
        if self.path == "/api/ledger-file":
            self.handle_file_ledger()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def handle_path_ledger(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise LedgerReadError("Expected a JSON object.")
            raw_path = payload.get("path")
            if not isinstance(raw_path, str):
                raise LedgerReadError("Expected path to be a string.")
            database_path = resolve_database_path(raw_path, self.server.base_dir)
            response = read_ledger(database_path)
        except json.JSONDecodeError:
            self.send_json(
                HTTPStatus.BAD_REQUEST, {"error": "Request body must be valid JSON."}
            )
            return
        except LedgerReadError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self.send_json(HTTPStatus.OK, response)

    def handle_file_ledger(self) -> None:
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
            response = read_uploaded_ledger(filename, self.rfile.read(length))
        except LedgerReadError as exc:
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


class LedgerViewerServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler],
        base_dir: Path,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.base_dir = base_dir


def run_server(host: str, port: int, base_dir: Path) -> None:
    server = LedgerViewerServer((host, port), LedgerViewerHandler, base_dir)
    url = f"http://{host}:{server.server_port}/"
    print(f"Serving TwinMind ledger viewer at {url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("", flush=True)
    finally:
        server.server_close()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve a read-only local viewer for the TwinMind SQLite ledger."
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
