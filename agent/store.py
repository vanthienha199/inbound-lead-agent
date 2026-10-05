"""SQLite CRM. Small on purpose, so a buyer can see the whole schema at once."""

import pathlib
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
  id            TEXT PRIMARY KEY,
  received_at   TEXT NOT NULL,
  source        TEXT,
  name          TEXT NOT NULL,
  email         TEXT NOT NULL,
  company       TEXT,
  industry      TEXT,
  employees     INTEGER,
  budget_usd    INTEGER,
  score         INTEGER NOT NULL,
  band          TEXT NOT NULL,
  guardrail     TEXT NOT NULL,
  status        TEXT NOT NULL,
  reply         TEXT,
  reasons       TEXT,
  findings      TEXT,
  backend       TEXT,
  trail         TEXT,
  decided_by    TEXT,
  decided_at    TEXT
);
"""

# Columns added after the first release. SQLite has no "add column if missing",
# so an existing database is brought forward one column at a time.
LATER_COLUMNS = {"source": "TEXT", "reasons": "TEXT", "findings": "TEXT",
                 "backend": "TEXT", "trail": "TEXT"}


class Crm:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)
            have = {r["name"] for r in c.execute("PRAGMA table_info(leads)")}
            for column, kind in LATER_COLUMNS.items():
                if column not in have:
                    c.execute(f"ALTER TABLE leads ADD COLUMN {column} {kind}")

    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def upsert(self, row):
        cols = ", ".join(row)
        marks = ", ".join("?" for _ in row)
        with self._conn() as c:
            c.execute(f"INSERT OR REPLACE INTO leads ({cols}) VALUES ({marks})", list(row.values()))

    def set_decision(self, lead_id, status, decided_by, decided_at):
        with self._conn() as c:
            c.execute(
                "UPDATE leads SET status=?, decided_by=?, decided_at=? WHERE id=?",
                (status, decided_by, decided_at, lead_id),
            )

    def all(self):
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM leads ORDER BY score DESC, id")]

    def get(self, lead_id):
        with self._conn() as c:
            r = c.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
            return dict(r) if r else None

    def reset(self):
        with self._conn() as c:
            c.execute("DELETE FROM leads")
