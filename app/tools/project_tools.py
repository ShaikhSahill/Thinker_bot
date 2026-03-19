from typing import Optional

import re

from app.infrastructure.database.mongo_connection import get_db


async def _find_project(db, project: str, tenant_id: Optional[str]):
    project = re.sub(r"\s+", " ", (project or "").strip())
    # Case-insensitive exact match for name or projectCode.
    query_exact = {
        "$or": [
            {"name": {"$regex": f"^{re.escape(project)}$", "$options": "i"}},
            {"projectCode": {"$regex": f"^{re.escape(project)}$", "$options": "i"}},
        ]
    }
    if tenant_id:
        query_exact["tenantId"] = tenant_id

    proj = await db.projects.find_one(query_exact)
    if proj:
        return proj

    # Fallback: contains match (helps when the user types partial name).
    query_contains = {
        "$or": [
            {"name": {"$regex": re.escape(project), "$options": "i"}},
            {"projectCode": {"$regex": re.escape(project), "$options": "i"}},
        ]
    }
    if tenant_id:
        query_contains["tenantId"] = tenant_id
    return await db.projects.find_one(query_contains)


async def find_project(project: str, tenant_id: Optional[str] = None):
    """Find a project by name or projectCode and return its id."""

    db = get_db()
    proj = await _find_project(db, project, tenant_id)
    if not proj:
        return {"found": False, "project": project}

    return {
        "found": True,
        "_id": str(proj.get("_id")),
        "projectCode": proj.get("projectCode"),
        "name": proj.get("name"),
        "status": proj.get("status"),
        "tenantId": proj.get("tenantId"),
    }


async def get_project_progress(project: str, tenant_id: Optional[str] = None):
    db = get_db()
    proj = await _find_project(db, project, tenant_id)
    if not proj:
        return {"error": f"Project '{project}' not found"}

    project_id_str = str(proj["_id"])
    # Be tolerant: `tasks.projectId` might be stored as string or ObjectId.
    match = {"projectId": {"$in": [project_id_str, proj["_id"]]}}
    if tenant_id:
        match["tenantId"] = tenant_id

    total = await db.tasks.count_documents(match)
    done = await db.tasks.count_documents({**match, "status": {"$in": ["COMPLETED", "DONE"]}})

    progress = 0 if total == 0 else round((done / total) * 100)
    return {
        "project": proj.get("name"),
        "projectCode": proj.get("projectCode"),
        "status": proj.get("status"),
        "tasks": {"total": total, "done": done},
        "progressPercent": progress,
    }


async def get_project_tasks(project: str, tenant_id: Optional[str] = None):
    db = get_db()
    proj = await _find_project(db, project, tenant_id)
    if not proj:
        return {"error": f"Project '{project}' not found"}

    project_id_str = str(proj["_id"])
    match = {"projectId": {"$in": [project_id_str, proj["_id"]]}}
    if tenant_id:
        match["tenantId"] = tenant_id

    cursor = db.tasks.find(match, {"_id": 0}).sort("issueKey", 1)
    tasks = [doc async for doc in cursor]
    return {
        "project": proj.get("name"),
        "projectCode": proj.get("projectCode"),
        "count": len(tasks),
        "tasks": tasks,
    }


async def get_project_tasks_by_status(project: str, status: str, tenant_id: Optional[str] = None):
    db = get_db()
    proj = await _find_project(db, project, tenant_id)
    if not proj:
        return {"error": f"Project '{project}' not found"}

    project_id_str = str(proj["_id"])
    match = {"projectId": {"$in": [project_id_str, proj["_id"]]}, "status": status}
    if tenant_id:
        match["tenantId"] = tenant_id

    cursor = db.tasks.find(match, {"_id": 0}).sort("issueKey", 1)
    tasks = [doc async for doc in cursor]
    return {
        "project": proj.get("name"),
        "projectCode": proj.get("projectCode"),
        "status": status,
        "count": len(tasks),
        "tasks": tasks,
    }


async def get_project_members(project: str, tenant_id: Optional[str] = None):
    db = get_db()
    proj = await _find_project(db, project, tenant_id)
    if not proj and tenant_id:
        # Helpful fallback: project exists but caller sent the wrong tenantId.
        proj_global = await _find_project(db, project, None)
        if proj_global:
            actual_tenant = proj_global.get("tenantId")
            return {
                "error": (
                    f"Project '{proj_global.get('name')}' exists, but it belongs to tenantId '{actual_tenant}'. "
                    f"Your request used tenantId '{tenant_id}'. "
                    "Use the correct tenantId (or omit tenantId to search globally)."
                )
            }

    if not proj:
        return {"error": f"Project '{project}' not found"}

    project_id_str = str(proj["_id"])
    match = {"projectId": {"$in": [project_id_str, proj["_id"]]}}

    collections = await db.list_collection_names()
    member_collection_name = None
    for candidate in ("project_member", "projects_member", "project_members", "projects_members"):
        if candidate in collections:
            member_collection_name = candidate
            break
    if member_collection_name is None:
        return {
            "error": "No project members collection found. Expected one of: project_member, projects_member, project_members, projects_members."
        }

    cursor = db[member_collection_name].find(match, {"_id": 0}).sort("userId", 1)
    members = [doc async for doc in cursor]

    # If a users collection exists, enrich.
    user_ids = [m.get("userId") for m in members if m.get("userId")]
    users_by_id = {}
    if user_ids:
        users_cursor = db.users.find({"userId": {"$in": user_ids}}, {"_id": 0})
        users_by_id = {u["userId"]: u async for u in users_cursor}

    enriched = []
    for m in members:
        u = users_by_id.get(m.get("userId"))
        if u:
            enriched.append({**m, "user": u})
        else:
            enriched.append(m)

    return {
        "project": proj.get("name"),
        "projectCode": proj.get("projectCode"),
        "count": len(enriched),
        "members": enriched,
    }


async def list_projects(tenant_id: Optional[str] = None):
    db = get_db()
    query = {}
    if tenant_id:
        query["tenantId"] = tenant_id

    cursor = db.projects.find(query, {"_id": 0}).sort("name", 1)
    return [doc async for doc in cursor]


async def list_ongoing_projects(tenant_id: Optional[str] = None):
    db = get_db()
    query = {
        "status": {"$nin": ["COMPLETED", "DONE", "CLOSED", "CANCELLED", "CANCELED"]}
    }
    if tenant_id:
        query["tenantId"] = tenant_id

    cursor = db.projects.find(query, {"_id": 0}).sort("name", 1)
    return [doc async for doc in cursor]
