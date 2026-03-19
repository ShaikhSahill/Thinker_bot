from app.infrastructure.database.mongo_connection import get_db
from typing import Optional


async def get_department_members(department: str, tenant_id: Optional[str] = None):
    """Requires a `users` collection with a `department` field.

    If you don't have it yet, the tool returns an explanatory error.
    """

    db = get_db()
    # quick existence check
    collections = await db.list_collection_names()
    if "users" not in collections:
        return {
            "error": "Collection 'users' not found. Add a users collection with fields like userId, name, department, domain to support department/domain queries."
        }

    query = {"department": {"$regex": f"^{department}$", "$options": "i"}}
    if tenant_id:
        query["tenantId"] = tenant_id

    cursor = db.users.find(query, {"_id": 0}).sort("userId", 1)
    users = [u async for u in cursor]
    return {"department": department, "count": len(users), "members": users}


async def get_domain_members(domain: str, tenant_id: Optional[str] = None):
    db = get_db()
    collections = await db.list_collection_names()
    if "users" not in collections:
        return {
            "error": "Collection 'users' not found. Add a users collection with fields like userId, name, department, domain to support department/domain queries."
        }

    query = {"domain": {"$regex": f"^{domain}$", "$options": "i"}}
    if tenant_id:
        query["tenantId"] = tenant_id

    cursor = db.users.find(query, {"_id": 0}).sort("userId", 1)
    users = [u async for u in cursor]
    return {"domain": domain, "count": len(users), "members": users}


async def get_total_members(tenant_id: Optional[str] = None):
    db = get_db()
    collections = await db.list_collection_names()
    if "users" in collections:
        query = {}
        if tenant_id:
            query["tenantId"] = tenant_id
        count = await db.users.count_documents(query)
        return {"count": count, "source": "users"}

    # fallback: distinct users across projects_member
    query = {}
    if tenant_id:
        query["tenantId"] = tenant_id
    user_ids = await db.projects_member.distinct("userId", query)
    return {"count": len([u for u in user_ids if u]), "source": "projects_member"}
