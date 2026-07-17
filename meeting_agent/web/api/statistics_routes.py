"""项目管理 & 数据统计 API 路由"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from meeting_agent.web.auth import get_current_user
from meeting_agent.web.models import (
    create_project,
    delete_project,
    get_statistics,
    list_projects,
    update_project,
)

router = APIRouter(prefix="/api")


# ═══════════════════════════════════════════════════════════════════════
#  Project CRUD
# ═══════════════════════════════════════════════════════════════════════

class ProjectCreateBody(BaseModel):
    name: str
    description: str = ""


class ProjectUpdateBody(BaseModel):
    name: str
    description: str = ""


@router.get("/projects")
def api_list_projects(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """列出当前用户的项目."""
    return list_projects(web_user_id=current_user["id"])


@router.post("/projects")
def api_create_project(
    body: ProjectCreateBody,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """创建新项目."""
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "项目名称不能为空")
    try:
        return create_project(name, body.description.strip(), current_user["id"])
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.put("/projects/{project_id}")
def api_update_project(
    project_id: int,
    body: ProjectUpdateBody,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """更新项目（仅项目归属用户可修改）."""
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "项目名称不能为空")
    if current_user.get("role") != "admin":
        projects = list_projects(web_user_id=current_user["id"])
        if not any(p["id"] == project_id for p in projects):
            raise HTTPException(403, "无权修改此项目")
    try:
        return update_project(project_id, name, body.description.strip())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.delete("/projects/{project_id}")
def api_delete_project(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """删除项目（关联的会议结果 project_id 自动置 NULL）."""
    if current_user.get("role") != "admin":
        projects = list_projects(web_user_id=current_user["id"])
        if not any(p["id"] == project_id for p in projects):
            raise HTTPException(403, "无权删除此项目")
    ok = delete_project(project_id)
    if not ok:
        raise HTTPException(404, "项目不存在")
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════════
#  Statistics
# ═══════════════════════════════════════════════════════════════════════

@router.get("/statistics")
def api_get_statistics(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取数据统计（普通用户看自己的，管理员看全局）."""
    is_admin = current_user.get("role") == "admin"
    web_user_id = current_user["id"] if not is_admin else None
    return get_statistics(web_user_id=web_user_id, is_admin=is_admin)


@router.get("/statistics/project/{project_id}")
def api_get_project_statistics(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取单个项目的详细统计."""
    is_admin = current_user.get("role") == "admin"
    web_user_id = current_user["id"] if not is_admin else None
    full_stats = get_statistics(web_user_id=web_user_id, is_admin=is_admin)

    # Find project name from project_id
    projects = list_projects(web_user_id=current_user["id"])
    target_name = ""
    for p in projects:
        if p["id"] == project_id:
            target_name = p["name"]
            break

    if not target_name and is_admin:
        # Admin: project may belong to any user, query all users' projects
        from meeting_agent.web.database import get_connection
        conn = get_connection()
        try:
            row = conn.execute("SELECT name FROM projects WHERE id = %s", (project_id,)).fetchone()
            if row:
                target_name = row["name"]
        finally:
            conn.close()

    if not target_name:
        raise HTTPException(404, "项目不存在")

    proj_schedules = [s for s in full_stats["schedules"] if s["source"] == target_name]
    proj_overview = next((p for p in full_stats["project_stats"] if p["name"] == target_name), None)

    return {
        "project_name": target_name,
        "project_id": project_id,
        "overview": proj_overview or {"name": target_name, "meeting_count": 0, "schedule_count": 0},
        "schedules": proj_schedules,
    }
