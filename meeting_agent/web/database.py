from __future__ import annotations

import os
from typing import Any, Optional

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

_MIN_CONN = 1
_MAX_CONN = 5

_pool: Optional[pg_pool.ThreadedConnectionPool] = None


def _get_dsn() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    load_dotenv()
    return os.environ.get("DATABASE_URL", "")


def init_connection_pool() -> None:
    global _pool
    if _pool is not None:
        return
    dsn = _get_dsn()
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL 未配置。请在 .env 中设置 DATABASE_URL，"
            "例如: DATABASE_URL=postgresql://user:password@host:5432/dbname"
        )
    _pool = pg_pool.ThreadedConnectionPool(_MIN_CONN, _MAX_CONN, dsn)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


class _PoolConnectionWrapper:
    """Wraps a psycopg2 connection so that .close() returns it to the pool
    instead of actually closing it, keeping models.py's try/finally pattern
    unchanged."""

    def __init__(self, conn: psycopg2.extensions.connection, pool: pg_pool.ThreadedConnectionPool):
        self._conn = conn
        self._pool = pool

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)

    def execute(self, query: str, vars: Optional[tuple] = None) -> psycopg2.extensions.cursor:
        cur = self._conn.cursor()
        cur.execute(query, vars)
        return cur

    def close(self) -> None:
        self._pool.putconn(self._conn)


def get_connection() -> _PoolConnectionWrapper:
    if _pool is None:
        init_connection_pool()
    conn = _pool.getconn()
    conn.cursor_factory = RealDictCursor
    return _PoolConnectionWrapper(conn, _pool)


def init_db() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS departments ("
            "id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE, "
            "dept_id INTEGER NOT NULL UNIQUE, "
            "parent_dept_id INTEGER REFERENCES departments(dept_id) ON DELETE SET NULL, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE, "
            "userid TEXT NOT NULL UNIQUE, "
            "department_name TEXT DEFAULT '', "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS web_users ("
            "id SERIAL PRIMARY KEY, username TEXT NOT NULL UNIQUE, "
            "password_hash TEXT NOT NULL, "
            "role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','admin')), "
            "department_name TEXT NOT NULL DEFAULT '', "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS sessions ("
            "id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL "
            "REFERENCES web_users(id) ON DELETE CASCADE, "
            "token TEXT NOT NULL UNIQUE, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS extraction_results ("
            "id TEXT PRIMARY KEY, original_filename TEXT NOT NULL, "
            "pdf_filename TEXT DEFAULT '', "
            "web_user_id INTEGER DEFAULT NULL "
            "REFERENCES web_users(id) ON DELETE SET NULL, "
            "status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','pushed')), "
            "result_json TEXT NOT NULL, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "pushed_at TIMESTAMP)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS transcription_results ("
            "id TEXT PRIMARY KEY, original_filename TEXT NOT NULL, "
            "user_prompt TEXT NOT NULL DEFAULT '', "
            "web_user_id INTEGER DEFAULT NULL "
            "REFERENCES web_users(id) ON DELETE SET NULL, "
            "status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','pushed')), "
            "result_json TEXT NOT NULL, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "pushed_at TIMESTAMP)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS background_tasks ("
            "id TEXT PRIMARY KEY, "
            "task_type TEXT NOT NULL CHECK(task_type IN ("
            "'extract_docx','extract_text','transcribe_file','transcribe_url'"
            ")), "
            "status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ("
            "'pending','running','success','failed'"
            ")), "
            "web_user_id INTEGER DEFAULT NULL "
            "REFERENCES web_users(id) ON DELETE SET NULL, "
            "payload_json TEXT NOT NULL, "
            "result_type TEXT DEFAULT '', "
            "result_id TEXT DEFAULT '', "
            "error TEXT DEFAULT '', "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "started_at TIMESTAMP, "
            "finished_at TIMESTAMP)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_background_tasks_queue "
            "ON background_tasks (status, task_type, created_at)"
        )
        cur.close()
        # Migrations: add columns if missing (existing DB)
        # Use information_schema checks to avoid transaction-abort from DuplicateColumn
        cur = conn.cursor()

        # pdf_filename on extraction_results
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='extraction_results' AND column_name='pdf_filename'"
        )
        if not cur.fetchone():
            cur.execute("ALTER TABLE extraction_results ADD COLUMN pdf_filename TEXT DEFAULT ''")

        # web_user_id on extraction_results
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='extraction_results' AND column_name='web_user_id'"
        )
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE extraction_results ADD COLUMN web_user_id INTEGER "
                "REFERENCES web_users(id) ON DELETE SET NULL"
            )

        # web_user_id on transcription_results
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='transcription_results' AND column_name='web_user_id'"
        )
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE transcription_results ADD COLUMN web_user_id INTEGER "
                "REFERENCES web_users(id) ON DELETE SET NULL"
            )

        cur.close()
        conn.commit()
    finally:
        conn.close()
