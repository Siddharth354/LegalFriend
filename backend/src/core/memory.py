import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    verbatim_hinglish TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS facts (
    session_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (session_id, key)
);
"""


class Memory:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def ensure_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id) VALUES (?)", (session_id,)
            )

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        verbatim_hinglish: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO turns (session_id, role, content, verbatim_hinglish) VALUES (?, ?, ?, ?)",
                (session_id, role, content, verbatim_hinglish),
            )

    def recent_turns(self, session_id: str, limit: int = 6) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM turns WHERE session_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return list(reversed(rows))

    def set_fact(self, session_id: str, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO facts (session_id, key, value, updated_at) VALUES (?, ?, ?, datetime('now')) "
                "ON CONFLICT (session_id, key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
                (session_id, key, value),
            )

    def get_facts(self, session_id: str) -> dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM facts WHERE session_id = ?", (session_id,)
            ).fetchall()
        return {row["key"]: row["value"] for row in rows}
