#!/usr/bin/env python
"""One-time script: migrate data from SQLite to PostgreSQL.

Usage:
    python scripts/migrate_sqlite_to_pg.py

Requirements:
    - .env file has DATABASE_URL for PostgreSQL
    - data/meeting_agent.db exists (SQLite source)
    - PostgreSQL tables already exist (run the app once to create them)

The script is idempotent — it truncates PostgreSQL tables before inserting.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


def get_pg_conn():
    load_dotenv()
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        print("ERROR: DATABASE_URL not set in .env")
        sys.exit(1)
    return psycopg2.connect(dsn)


def get_sqlite_conn() -> sqlite3.Connection:
    db_path = Path("data/meeting_agent.db")
    if not db_path.exists():
        print(f"NOTE: SQLite database not found at {db_path}, nothing to migrate.")
        sys.exit(0)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def migrate_table(pg_conn, sqlite_conn, table: str, columns: list[str]):
    """Migrate a single table from SQLite to PostgreSQL."""
    # Read from SQLite
    rows = sqlite_conn.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
    if not rows:
        print(f"  {table}: 0 rows, skipped")
        return

    # Truncate PostgreSQL table
    pg_cur = pg_conn.cursor()
    pg_cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
    pg_cur.close()

    # Build INSERT statement
    placeholders = ", ".join(["%s"] * len(columns))
    col_names = ", ".join(columns)
    insert_sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"

    # Insert all rows
    pg_cur = pg_conn.cursor()
    for row in rows:
        values = []
        for col in columns:
            val = row[col]
            # Convert JSON fields
            if col == "result_json" and isinstance(val, str):
                val = val  # already a string
            values.append(val)
        pg_cur.execute(insert_sql, values)

    pg_conn.commit()
    pg_cur.close()
    print(f"  {table}: {len(rows)} rows migrated")


def main():
    print("=== SQLite → PostgreSQL Migration ===\n")

    # Source: SQLite
    sqlite_conn = get_sqlite_conn()
    # Dest: PostgreSQL
    pg_conn = get_pg_conn()
    pg_conn.autocommit = False

    try:
        # Tables to migrate (in dependency order)
        tables = [
            ("departments", ["id", "name", "dept_id", "created_at", "updated_at"]),
            ("users", ["id", "name", "userid", "department_name", "created_at", "updated_at"]),
            ("extraction_results", [
                "id", "original_filename", "pdf_filename", "status",
                "result_json", "created_at", "updated_at", "pushed_at",
            ]),
            ("transcription_results", [
                "id", "original_filename", "user_prompt", "status",
                "result_json", "created_at", "updated_at", "pushed_at",
            ]),
        ]

        for table_name, columns in tables:
            migrate_table(pg_conn, sqlite_conn, table_name, columns)

        print("\nMigration complete!")
    except Exception as e:
        pg_conn.rollback()
        print(f"\nERROR: {e}")
        sys.exit(1)
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
