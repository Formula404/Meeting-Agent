from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from meeting_agent.web.database import get_connection


# ── Users ──────────────────────────────────────────────────────────────────

def list_users() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_user(name: str, userid: str, department_name: str = "") -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, userid, department_name) VALUES (?, ?, ?)",
            (name.strip(), userid.strip(), department_name.strip()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)
    except sqlite3.IntegrityError as e:
        raise ValueError(f"用户已存在或 userid 重复: {e}") from e
    finally:
        conn.close()


def update_user(user_id: int, name: str, userid: str, department_name: str = "") -> Dict[str, Any]:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET name=?, userid=?, department_name=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (name.strip(), userid.strip(), department_name.strip(), user_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise ValueError(f"用户 id={user_id} 不存在")
        return dict(row)
    except sqlite3.IntegrityError as e:
        raise ValueError(f"更新失败: {e}") from e
    finally:
        conn.close()


def delete_user(user_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


# ── Departments ────────────────────────────────────────────────────────────

def list_departments() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM departments ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_department(name: str, dept_id: int) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO departments (name, dept_id) VALUES (?, ?)",
            (name.strip(), dept_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM departments WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)
    except sqlite3.IntegrityError as e:
        raise ValueError(f"部门已存在或 dept_id 重复: {e}") from e
    finally:
        conn.close()


def update_department(dept_pk: int, name: str, dept_id: int) -> Dict[str, Any]:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE departments SET name=?, dept_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (name.strip(), dept_id, dept_pk),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM departments WHERE id = ?", (dept_pk,)).fetchone()
        if not row:
            raise ValueError(f"部门 id={dept_pk} 不存在")
        return dict(row)
    except sqlite3.IntegrityError as e:
        raise ValueError(f"更新失败: {e}") from e
    finally:
        conn.close()


def delete_department(dept_pk: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM departments WHERE id = ?", (dept_pk,))
        conn.commit()
    finally:
        conn.close()


# ── Results ────────────────────────────────────────────────────────────────

def create_result(original_filename: str, result_data: Dict[str, Any]) -> Dict[str, Any]:
    result_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO extraction_results (id, original_filename, result_json) VALUES (?, ?, ?)",
            (result_id, original_filename, json.dumps(result_data, ensure_ascii=False)),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM extraction_results WHERE id = ?", (result_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def list_results() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, original_filename, status, created_at, updated_at, pushed_at FROM extraction_results ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_result(result_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM extraction_results WHERE id = ?", (result_id,)).fetchone()
        if row:
            d = dict(row)
            d["result_json"] = json.loads(d["result_json"])
            return d
        return None
    finally:
        conn.close()


def update_result(result_id: str, result_data: Dict[str, Any]) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE extraction_results SET result_json=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (json.dumps(result_data, ensure_ascii=False), result_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def mark_result_pushed(result_id: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE extraction_results SET status='pushed', pushed_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (result_id,),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
