from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock

DB_DIR = Path("data")
DB_PATH = DB_DIR / "meeting_agent.db"

_lock = Lock()


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with _lock:
        conn = get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS departments (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL UNIQUE,
                    dept_id     INTEGER NOT NULL UNIQUE,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS users (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    name            TEXT NOT NULL UNIQUE,
                    userid          TEXT NOT NULL UNIQUE,
                    department_name TEXT DEFAULT '',
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS extraction_results (
                    id                  TEXT PRIMARY KEY,
                    original_filename   TEXT NOT NULL,
                    pdf_filename        TEXT DEFAULT '',
                    status              TEXT NOT NULL DEFAULT 'draft'
                                        CHECK(status IN ('draft','pushed')),
                    result_json         TEXT NOT NULL,
                    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pushed_at           TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS transcription_results (
                    id                  TEXT PRIMARY KEY,
                    original_filename   TEXT NOT NULL,
                    user_prompt         TEXT NOT NULL DEFAULT '',
                    status              TEXT NOT NULL DEFAULT 'draft'
                                        CHECK(status IN ('draft','pushed')),
                    result_json         TEXT NOT NULL,
                    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pushed_at           TIMESTAMP
                );
            """)
            # Migration: add pdf_filename column if missing (existing DB)
            try:
                conn.execute("ALTER TABLE extraction_results ADD COLUMN pdf_filename TEXT DEFAULT ''")
            except Exception:
                pass  # column already exists
            conn.commit()
        finally:
            conn.close()
