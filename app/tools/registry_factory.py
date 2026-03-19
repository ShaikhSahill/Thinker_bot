from __future__ import annotations

from app.tools.org_tools import get_department_members, get_domain_members, get_total_members
from app.tools.project_tools import (
    find_project,
    get_project_members,
    get_project_progress,
    get_project_tasks,
    get_project_tasks_by_status,
    list_ongoing_projects,
    list_projects,
)
from app.tools.tool_registry import ToolRegistry, ToolSpec


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        ToolSpec(
            name="get_project_progress",
            description="Get overall progress for a project based on task completion.",
            parameters={
                "type": "object",
                "properties": {"project": {"type": "string"}, "tenant_id": {"type": "string"}},
                "required": ["project"],
            },
        ),
        get_project_progress,
    )

    registry.register(
        ToolSpec(
            name="get_project_members",
            description="List members assigned to a project.",
            parameters={
                "type": "object",
                "properties": {"project": {"type": "string"}, "tenant_id": {"type": "string"}},
                "required": ["project"],
            },
        ),
        get_project_members,
    )

    registry.register(
        ToolSpec(
            name="get_project_tasks",
            description="List tasks under a project.",
            parameters={
                "type": "object",
                "properties": {"project": {"type": "string"}, "tenant_id": {"type": "string"}},
                "required": ["project"],
            },
        ),
        get_project_tasks,
    )

    registry.register(
        ToolSpec(
            name="get_project_tasks_by_status",
            description="List tasks under a project filtered by status (TODO/IN_PROGRESS/COMPLETED).",
            parameters={
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "status": {"type": "string"},
                    "tenant_id": {"type": "string"},
                },
                "required": ["project", "status"],
            },
        ),
        get_project_tasks_by_status,
    )

    registry.register(
        ToolSpec(
            name="get_department_members",
            description="List members in a department (requires users collection with department field).",
            parameters={
                "type": "object",
                "properties": {"department": {"type": "string"}, "tenant_id": {"type": "string"}},
                "required": ["department"],
            },
        ),
        get_department_members,
    )

    registry.register(
        ToolSpec(
            name="get_domain_members",
            description="List members in a domain like frontend/backend/ui/ux/qa (requires users collection with domain field).",
            parameters={
                "type": "object",
                "properties": {"domain": {"type": "string"}, "tenant_id": {"type": "string"}},
                "required": ["domain"],
            },
        ),
        get_domain_members,
    )

    registry.register(
        ToolSpec(
            name="get_total_members",
            description="Get total member count (uses users collection if present; else distinct from projects_member).",
            parameters={
                "type": "object",
                "properties": {"tenant_id": {"type": "string"}},
                "required": [],
            },
        ),
        get_total_members,
    )

    registry.register(
        ToolSpec(
            name="list_projects",
            description="List all projects.",
            parameters={
                "type": "object",
                "properties": {"tenant_id": {"type": "string"}},
                "required": [],
            },
        ),
        list_projects,
    )

    registry.register(
        ToolSpec(
            name="list_ongoing_projects",
            description="List ongoing/active projects (status not completed/done/closed/cancelled).",
            parameters={
                "type": "object",
                "properties": {"tenant_id": {"type": "string"}},
                "required": [],
            },
        ),
        list_ongoing_projects,
    )

    registry.register(
        ToolSpec(
            name="find_project",
            description="Find a project by name or projectCode and return its _id.",
            parameters={
                "type": "object",
                "properties": {"project": {"type": "string"}, "tenant_id": {"type": "string"}},
                "required": ["project"],
            },
        ),
        find_project,
    )

    return registry
