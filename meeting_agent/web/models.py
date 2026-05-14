from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from psycopg2.errors import UniqueViolation

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
            "INSERT INTO users (name, userid, department_name) VALUES (%s, %s, %s) RETURNING id",
            (name.strip(), userid.strip(), department_name.strip()),
        )
        conn.commit()
        row_id = cur.fetchone()["id"]
        row = conn.execute("SELECT * FROM users WHERE id = %s", (row_id,)).fetchone()
        return dict(row)
    except UniqueViolation as e:
        raise ValueError(f"用户已存在或 userid 重复: {e}") from e
    finally:
        conn.close()


def update_user(user_id: int, name: str, userid: str, department_name: str = "") -> Dict[str, Any]:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET name=%s, userid=%s, department_name=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (name.strip(), userid.strip(), department_name.strip(), user_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()
        if not row:
            raise ValueError(f"用户 id={user_id} 不存在")
        return dict(row)
    except UniqueViolation as e:
        raise ValueError(f"更新失败: {e}") from e
    finally:
        conn.close()


def delete_user(user_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))
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
            "INSERT INTO departments (name, dept_id) VALUES (%s, %s) RETURNING id",
            (name.strip(), dept_id),
        )
        conn.commit()
        row_id = cur.fetchone()["id"]
        row = conn.execute("SELECT * FROM departments WHERE id = %s", (row_id,)).fetchone()
        return dict(row)
    except UniqueViolation as e:
        raise ValueError(f"部门已存在或 dept_id 重复: {e}") from e
    finally:
        conn.close()


def update_department(dept_pk: int, name: str, dept_id: int) -> Dict[str, Any]:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE departments SET name=%s, dept_id=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (name.strip(), dept_id, dept_pk),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM departments WHERE id = %s", (dept_pk,)).fetchone()
        if not row:
            raise ValueError(f"部门 id={dept_pk} 不存在")
        return dict(row)
    except UniqueViolation as e:
        raise ValueError(f"更新失败: {e}") from e
    finally:
        conn.close()


def delete_department(dept_pk: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM departments WHERE id = %s", (dept_pk,))
        conn.commit()
    finally:
        conn.close()


# ── Web Users (login accounts) ─────────────────────────────────────────────

def create_web_user(username: str, password_hash: str, department_name: str = "", role: str = "user") -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO web_users (username, password_hash, department_name, role) VALUES (%s, %s, %s, %s) RETURNING id",
            (username.strip(), password_hash, department_name.strip(), role),
        )
        conn.commit()
        row_id = cur.fetchone()["id"]
        row = conn.execute("SELECT * FROM web_users WHERE id = %s", (row_id,)).fetchone()
        return dict(row)
    except UniqueViolation:
        raise ValueError("用户名已存在")
    finally:
        conn.close()


def get_web_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM web_users WHERE username = %s", (username.strip(),)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_web_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM web_users WHERE id = %s", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_web_users() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, username, role, department_name, created_at FROM web_users ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_web_user(user_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM web_users WHERE id = %s", (user_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Sessions ───────────────────────────────────────────────────────────────

def create_session(user_id: int, token: str) -> None:
    conn = get_connection()
    try:
        conn.execute("INSERT INTO sessions (user_id, token) VALUES (%s, %s)", (user_id, token))
        conn.commit()
    finally:
        conn.close()


def get_session_by_token(token: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE token = %s", (token,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_session(token: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE token = %s", (token,))
        conn.commit()
    finally:
        conn.close()


# ── Results ────────────────────────────────────────────────────────────────

def create_result(
    original_filename: str,
    result_data: Dict[str, Any],
    pdf_filename: str = "",
    web_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    result_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO extraction_results (id, original_filename, pdf_filename, web_user_id, result_json) VALUES (%s, %s, %s, %s, %s)",
            (result_id, original_filename, pdf_filename, web_user_id, json.dumps(result_data, ensure_ascii=False)),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM extraction_results WHERE id = %s", (result_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def list_results(web_user_id: Optional[int] = None, is_admin: bool = False) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        if is_admin:
            rows = conn.execute(
                "SELECT id, original_filename, pdf_filename, status, created_at, updated_at, pushed_at FROM extraction_results ORDER BY created_at DESC"
            ).fetchall()
        elif web_user_id is not None:
            rows = conn.execute(
                "SELECT id, original_filename, pdf_filename, status, created_at, updated_at, pushed_at FROM extraction_results WHERE web_user_id = %s ORDER BY created_at DESC",
                (web_user_id,),
            ).fetchall()
        else:
            rows = []
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_result(result_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM extraction_results WHERE id = %s", (result_id,)).fetchone()
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
            "UPDATE extraction_results SET result_json=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (json.dumps(result_data, ensure_ascii=False), result_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_result(result_id: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM extraction_results WHERE id = %s", (result_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def mark_result_pushed(result_id: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE extraction_results SET status='pushed', pushed_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (result_id,),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def update_pdf_filename(result_id: str, pdf_filename: str) -> bool:
    """更新 extraction_result 的 pdf_filename 字段。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE extraction_results SET pdf_filename=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (pdf_filename, result_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Transcription Results ──────────────────────────────────────────

def create_transcription_result(
    original_filename: str,
    result_data: Dict[str, Any],
    user_prompt: str = "",
    web_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    result_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO transcription_results (id, original_filename, user_prompt, web_user_id, result_json) VALUES (%s, %s, %s, %s, %s)",
            (result_id, original_filename, user_prompt, web_user_id, json.dumps(result_data, ensure_ascii=False)),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM transcription_results WHERE id = %s", (result_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def list_transcription_results(web_user_id: Optional[int] = None, is_admin: bool = False) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        if is_admin:
            rows = conn.execute(
                "SELECT id, original_filename, status, created_at, updated_at, pushed_at FROM transcription_results ORDER BY created_at DESC"
            ).fetchall()
        elif web_user_id is not None:
            rows = conn.execute(
                "SELECT id, original_filename, status, created_at, updated_at, pushed_at FROM transcription_results WHERE web_user_id = %s ORDER BY created_at DESC",
                (web_user_id,),
            ).fetchall()
        else:
            rows = []
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_transcription_result(result_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM transcription_results WHERE id = %s", (result_id,)).fetchone()
        if row:
            d = dict(row)
            d["result_json"] = json.loads(d["result_json"])
            return d
        return None
    finally:
        conn.close()


def update_transcription_result(result_id: str, result_data: Dict[str, Any]) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE transcription_results SET result_json=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (json.dumps(result_data, ensure_ascii=False), result_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_transcription_result(result_id: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM transcription_results WHERE id = %s", (result_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def mark_transcription_result_pushed(result_id: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE transcription_results SET status='pushed', pushed_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (result_id,),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
