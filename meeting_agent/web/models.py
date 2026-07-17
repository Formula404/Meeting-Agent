from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

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
    name = name.strip()
    userid = userid.strip()
    department_name = department_name.strip()
    conn = get_connection()
    try:
        return _insert_user(conn, name, userid, department_name)
    except UniqueViolation as e:
        conn.rollback()
        # Data imported with an explicit id can leave the SERIAL sequence
        # behind the table.  In that case a genuinely new name/userid fails on
        # users_pkey and the old generic message misleadingly says the user is
        # duplicated. Repair the sequence once and retry the insert.
        if e.diag.constraint_name == "users_pkey":
            conn.execute(
                "SELECT setval(pg_get_serial_sequence('users', 'id'), "
                "COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM users"
            )
            conn.commit()
            try:
                return _insert_user(conn, name, userid, department_name)
            except UniqueViolation as retry_error:
                conn.rollback()
                raise ValueError(_user_conflict_message(retry_error)) from retry_error
        raise ValueError(_user_conflict_message(e)) from e
    finally:
        conn.close()


def _insert_user(conn: Any, name: str, userid: str, department_name: str) -> Dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO users (name, userid, department_name) VALUES (%s, %s, %s) RETURNING *",
        (name, userid, department_name),
    )
    row = cur.fetchone()
    conn.commit()
    return dict(row)


def _user_conflict_message(error: UniqueViolation) -> str:
    constraint = error.diag.constraint_name
    if constraint == "users_name_key":
        return "姓名已存在"
    if constraint == "users_userid_key":
        return "UserID 已存在"
    if constraint == "users_pkey":
        return "用户编号序列异常，请重试"
    return "用户姓名或 UserID 已存在"


def create_users_batch(items: Sequence[Dict[str, str]]) -> Dict[str, Any]:
    """Create only new users and report existing rows as skipped.

    Existing means either the normalized name or userid is already present,
    including a duplicate earlier in the same batch. Each create has its own
    transaction so one conflict cannot poison or roll back the remaining rows.
    """
    existing = list_users()
    names = {row["name"].strip() for row in existing}
    userids = {row["userid"].strip() for row in existing}
    created: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for index, item in enumerate(items, start=1):
        name = item["name"].strip()
        userid = item["userid"].strip()
        department_name = item.get("department_name", "").strip()

        reasons = []
        if name in names:
            reasons.append("姓名已存在")
        if userid in userids:
            reasons.append("UserID 已存在")
        if reasons:
            skipped.append({"index": index, "name": name, "userid": userid, "reason": "、".join(reasons)})
            continue

        try:
            row = create_user(name, userid, department_name)
        except ValueError as error:
            # Covers a concurrent insert between list_users() and create_user().
            if str(error) not in {"姓名已存在", "UserID 已存在", "用户姓名或 UserID 已存在"}:
                raise
            skipped.append({"index": index, "name": name, "userid": userid, "reason": str(error)})
            names.add(name)
            userids.add(userid)
            continue

        created.append(row)
        names.add(name)
        userids.add(userid)

    return {
        "created_count": len(created),
        "skipped_count": len(skipped),
        "created": created,
        "skipped": skipped,
    }


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
        conn.rollback()
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
        conn.rollback()
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
        conn.rollback()
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
        conn.rollback()
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
    template_id: str = "",
) -> Dict[str, Any]:
    result_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO extraction_results (id, original_filename, pdf_filename, web_user_id, result_json, template_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (result_id, original_filename, pdf_filename, web_user_id, json.dumps(result_data, ensure_ascii=False), template_id or None),
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
                "SELECT r.id, r.original_filename, r.pdf_filename, r.status, "
                "r.created_at, r.updated_at, r.pushed_at, "
                "r.project_id, COALESCE(p.name, '') AS project_name, "
                "COALESCE(u.username, '') AS operator_name "
                "FROM extraction_results r "
                "LEFT JOIN web_users u ON r.web_user_id = u.id "
                "LEFT JOIN projects p ON r.project_id = p.id "
                "ORDER BY r.created_at DESC"
            ).fetchall()
        elif web_user_id is not None:
            rows = conn.execute(
                "SELECT r.id, r.original_filename, r.pdf_filename, r.status, "
                "r.created_at, r.updated_at, r.pushed_at, "
                "r.project_id, COALESCE(p.name, '') AS project_name, "
                "COALESCE(u.username, '') AS operator_name "
                "FROM extraction_results r "
                "LEFT JOIN web_users u ON r.web_user_id = u.id "
                "LEFT JOIN projects p ON r.project_id = p.id "
                "WHERE r.web_user_id = %s ORDER BY r.created_at DESC",
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
        row = conn.execute(
            "SELECT r.*, COALESCE(u.username, '') AS operator_name "
            "FROM extraction_results r "
            "LEFT JOIN web_users u ON r.web_user_id = u.id "
            "WHERE r.id = %s", (result_id,)
        ).fetchone()
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
    template_id: str = "",
) -> Dict[str, Any]:
    result_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO transcription_results (id, original_filename, user_prompt, web_user_id, result_json, template_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (result_id, original_filename, user_prompt, web_user_id, json.dumps(result_data, ensure_ascii=False), template_id or None),
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
                "SELECT r.id, r.original_filename, r.status, "
                "r.created_at, r.updated_at, r.pushed_at, "
                "r.project_id, COALESCE(p.name, '') AS project_name, "
                "COALESCE(u.username, '') AS operator_name "
                "FROM transcription_results r "
                "LEFT JOIN web_users u ON r.web_user_id = u.id "
                "LEFT JOIN projects p ON r.project_id = p.id "
                "ORDER BY r.created_at DESC"
            ).fetchall()
        elif web_user_id is not None:
            rows = conn.execute(
                "SELECT r.id, r.original_filename, r.status, "
                "r.created_at, r.updated_at, r.pushed_at, "
                "r.project_id, COALESCE(p.name, '') AS project_name, "
                "COALESCE(u.username, '') AS operator_name "
                "FROM transcription_results r "
                "LEFT JOIN web_users u ON r.web_user_id = u.id "
                "LEFT JOIN projects p ON r.project_id = p.id "
                "WHERE r.web_user_id = %s ORDER BY r.created_at DESC",
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
        row = conn.execute(
            "SELECT r.*, COALESCE(u.username, '') AS operator_name "
            "FROM transcription_results r "
            "LEFT JOIN web_users u ON r.web_user_id = u.id "
            "WHERE r.id = %s", (result_id,)
        ).fetchone()
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


# ── Background Tasks ──────────────────────────────────────────────────────

def create_background_task(
    task_type: str,
    payload: Dict[str, Any],
    web_user_id: Optional[int] = None,
    template_id: str = "",
) -> Dict[str, Any]:
    task_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO background_tasks "
            "(id, task_type, web_user_id, payload_json, template_id) "
            "VALUES (%s, %s, %s, %s, %s)",
            (task_id, task_type, web_user_id, json.dumps(payload, ensure_ascii=False), template_id or None),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM background_tasks WHERE id = %s", (task_id,)).fetchone()
        return _decode_task_row(dict(row))
    finally:
        conn.close()


def get_background_task(task_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM background_tasks WHERE id = %s", (task_id,)).fetchone()
        return _decode_task_row(dict(row)) if row else None
    finally:
        conn.close()


def claim_next_background_task(task_types: Sequence[str]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE background_tasks SET "
            "status='running', started_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP "
            "WHERE id = ("
            "  SELECT id FROM background_tasks "
            "  WHERE status='pending' AND task_type = ANY(%s) "
            "  ORDER BY created_at "
            "  FOR UPDATE SKIP LOCKED "
            "  LIMIT 1"
            ") "
            "RETURNING *",
            (list(task_types),),
        )
        row = cur.fetchone()
        conn.commit()
        return _decode_task_row(dict(row)) if row else None
    finally:
        conn.close()


def complete_background_task(task_id: str, result_type: str, result_id: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE background_tasks SET "
            "status='success', result_type=%s, result_id=%s, error='', "
            "updated_at=CURRENT_TIMESTAMP, finished_at=CURRENT_TIMESTAMP "
            "WHERE id=%s",
            (result_type, result_id, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def fail_background_task(task_id: str, error: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE background_tasks SET "
            "status='failed', error=%s, updated_at=CURRENT_TIMESTAMP, finished_at=CURRENT_TIMESTAMP "
            "WHERE id=%s",
            (error[:4000], task_id),
        )
        conn.commit()
    finally:
        conn.close()


def reset_running_background_tasks() -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE background_tasks SET "
            "status='pending', updated_at=CURRENT_TIMESTAMP, started_at=NULL "
            "WHERE status='running'"
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ── Templates ─────────────────────────────────────────────────────────────

def create_template(
    name: str,
    style_prompt: str,
    created_by: int,
    description: str = "",
    sample_output: str = "{}",
    is_default: bool = False,
    is_builtin: bool = False,
) -> Dict[str, Any]:
    template_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO templates (id, name, description, style_prompt, sample_output, "
            "created_by, is_default, is_builtin) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (template_id, name.strip(), description.strip(), style_prompt.strip(),
             sample_output, created_by, is_default, is_builtin),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM templates WHERE id = %s", (template_id,)).fetchone()
        return dict(row)
    except UniqueViolation as e:
        conn.rollback()
        raise ValueError(f"创建模板失败: {e}") from e
    finally:
        conn.close()


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT t.*, COALESCE(u.username, '') AS creator_name "
            "FROM templates t LEFT JOIN web_users u ON t.created_by = u.id "
            "WHERE t.id = %s", (template_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_templates() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT t.*, COALESCE(u.username, '') AS creator_name "
            "FROM templates t LEFT JOIN web_users u ON t.created_by = u.id "
            "ORDER BY t.is_builtin DESC, t.created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_template(
    template_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    style_prompt: Optional[str] = None,
    sample_output: Optional[str] = None,
) -> bool:
    conn = get_connection()
    try:
        fields = []
        values = []
        if name is not None:
            fields.append("name = %s")
            values.append(name.strip())
        if description is not None:
            fields.append("description = %s")
            values.append(description.strip())
        if style_prompt is not None:
            fields.append("style_prompt = %s")
            values.append(style_prompt.strip())
        if sample_output is not None:
            fields.append("sample_output = %s")
            values.append(sample_output)
        if not fields:
            return False
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(template_id)
        cur = conn.execute(
            f"UPDATE templates SET {', '.join(fields)} WHERE id = %s",
            tuple(values),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_template(template_id: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM templates WHERE id = %s", (template_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Projects ──────────────────────────────────────────────────────────────

def create_project(name: str, description: str, web_user_id: int) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO projects (name, description, web_user_id) VALUES (%s, %s, %s) RETURNING id",
            (name.strip(), description.strip(), web_user_id),
        )
        conn.commit()
        row_id = cur.fetchone()["id"]
        row = conn.execute("SELECT * FROM projects WHERE id = %s", (row_id,)).fetchone()
        return dict(row)
    except UniqueViolation:
        conn.rollback()
        raise ValueError("该项目名称已存在")
    finally:
        conn.close()


def list_projects(web_user_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM projects WHERE web_user_id = %s ORDER BY updated_at DESC",
            (web_user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_project(project_id: int, name: str, description: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE projects SET name=%s, description=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (name.strip(), description.strip(), project_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM projects WHERE id = %s", (project_id,)).fetchone()
        if not row:
            raise ValueError(f"项目 id={project_id} 不存在")
        return dict(row)
    except UniqueViolation:
        conn.rollback()
        raise ValueError("该项目名称已存在")
    finally:
        conn.close()


def delete_project(project_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


_RESULT_TABLES = {"extraction": "extraction_results", "transcription": "transcription_results"}


def update_result_project(result_type: str, result_id: str, project_id: Optional[int]) -> bool:
    """Set or clear project association on a result."""
    table = _RESULT_TABLES[result_type]  # KeyError if unknown type
    conn = get_connection()
    try:
        cur = conn.execute(
            f"UPDATE {table} SET project_id=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (project_id, result_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_statistics(web_user_id: Optional[int] = None, is_admin: bool = False) -> Dict[str, Any]:
    """Aggregate statistics across pushed extraction and transcription results."""
    conn = get_connection()
    try:
        # Query pushed results with project info
        if is_admin:
            ext_rows = conn.execute(
                "SELECT r.id, r.result_json, r.project_id, r.created_at, r.pushed_at, "
                "COALESCE(p.name, '') AS project_name "
                "FROM extraction_results r "
                "LEFT JOIN projects p ON r.project_id = p.id "
                "WHERE r.status = 'pushed'"
            ).fetchall()
            tra_rows = conn.execute(
                "SELECT r.id, r.result_json, r.project_id, r.created_at, r.pushed_at, "
                "COALESCE(p.name, '') AS project_name "
                "FROM transcription_results r "
                "LEFT JOIN projects p ON r.project_id = p.id "
                "WHERE r.status = 'pushed'"
            ).fetchall()
        else:
            ext_rows = conn.execute(
                "SELECT r.id, r.result_json, r.project_id, r.created_at, r.pushed_at, "
                "COALESCE(p.name, '') AS project_name "
                "FROM extraction_results r "
                "LEFT JOIN projects p ON r.project_id = p.id "
                "WHERE r.status = 'pushed' AND r.web_user_id = %s",
                (web_user_id,),
            ).fetchall()
            tra_rows = conn.execute(
                "SELECT r.id, r.result_json, r.project_id, r.created_at, r.pushed_at, "
                "COALESCE(p.name, '') AS project_name "
                "FROM transcription_results r "
                "LEFT JOIN projects p ON r.project_id = p.id "
                "WHERE r.status = 'pushed' AND r.web_user_id = %s",
                (web_user_id,),
            ).fetchall()
    finally:
        conn.close()

    now = datetime.now()
    all_rows = list(ext_rows) + list(tra_rows)

    total_meetings = len(all_rows)
    project_set: set = set()
    project_meetings: Dict[str, int] = {}
    project_last: Dict[str, datetime] = {}

    all_schedules: List[Dict[str, Any]] = []
    person_tasks: Dict[str, Dict[str, int]] = {}  # name -> {active, expired}

    for row in all_rows:
        pid = row.get("project_id")
        pname = row.get("project_name", "") or "未归类"

        if pid:
            project_set.add(pid)
        project_meetings[pname] = project_meetings.get(pname, 0) + 1
        created = row.get("created_at")
        if isinstance(created, datetime):
            if pname not in project_last or created > project_last[pname]:
                project_last[pname] = created

        try:
            data = json.loads(row["result_json"]) if isinstance(row["result_json"], str) else row["result_json"]
        except (json.JSONDecodeError, TypeError):
            continue

        schedules = data.get("schedules", []) or []
        for s in schedules:
            title = s.get("title", "")
            owners = s.get("owner", []) or []
            end_raw = s.get("end_time", "")

            is_expired = False
            end_display = ""
            if end_raw:
                try:
                    end_dt = None
                    if isinstance(end_raw, (int, float)):
                        end_dt = datetime.fromtimestamp(end_raw)
                        end_display = end_dt.strftime("%Y-%m-%d %H:%M")
                    elif isinstance(end_raw, str) and end_raw.strip():
                        end_str = end_raw.strip()
                        end_display = end_str
                        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                            try:
                                end_dt = datetime.strptime(end_str[:16] if len(end_str) >= 16 else end_str[:10], fmt)
                                break
                            except ValueError:
                                continue
                    if end_dt and end_dt <= now:
                        is_expired = True
                except (ValueError, IndexError, OSError):
                    pass

            schedule_entry = {
                "title": title,
                "owners": owners,
                "end_time": end_display if end_display else "",
                "status": "expired" if is_expired else "active",
                "source": pname,
            }
            all_schedules.append(schedule_entry)

            for owner in owners:
                if not owner:
                    continue
                if owner not in person_tasks:
                    person_tasks[owner] = {"active": 0, "expired": 0, "total": 0}
                person_tasks[owner]["total"] += 1
                if is_expired:
                    person_tasks[owner]["expired"] += 1
                else:
                    person_tasks[owner]["active"] += 1

    total_schedules = len(all_schedules)
    active_schedules = sum(1 for s in all_schedules if s["status"] == "active")
    expired_schedules = sum(1 for s in all_schedules if s["status"] == "expired")

    # Project breakdown
    project_stats = sorted(
        [
            {
                "name": name,
                "meeting_count": count,
                "schedule_count": sum(
                    1 for s in all_schedules if s["source"] == name
                ),
                "last_meeting": project_last.get(name),
            }
            for name, count in project_meetings.items()
        ],
        key=lambda x: x["meeting_count"],
        reverse=True,
    )

    # Person breakdown
    person_stats = sorted(
        [
            {"name": name, **counts}
            for name, counts in person_tasks.items()
        ],
        key=lambda x: x["total"],
        reverse=True,
    )

    return {
        "overview": {
            "total_meetings": total_meetings,
            "total_projects": len(project_set),
            "total_schedules": total_schedules,
            "active_schedules": active_schedules,
            "expired_schedules": expired_schedules,
        },
        "project_stats": project_stats,
        "person_stats": person_stats,
        "schedules": all_schedules,
    }


def _decode_task_row(row: Dict[str, Any]) -> Dict[str, Any]:
    row["payload_json"] = json.loads(row["payload_json"])
    return row
