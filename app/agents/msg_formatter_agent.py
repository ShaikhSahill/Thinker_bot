from __future__ import annotations

from typing import Any

from app.infrastructure.llm.gemini_client import GeminiClient
from app.settings import Settings


class MsgFormatterAgent:
    def __init__(self) -> None:
        self._settings = Settings()

    def format(self, *, user_message: str, intent: Any, entities: dict, tool: Any, data: Any) -> str:
        lowered = (user_message or "").lower()
        wants_count = "how many" in lowered or "count" in lowered or "number of" in lowered
        wants_list = any(
            k in lowered
            for k in [
                "who",
                "list",
                "show",
                "which",
                "what are",
                "what tasks",
                "tasks in",
                "members in",
                "projects in",
            ]
        )

        # Deterministic for intents where accuracy matters and LLM often drops fields.
        if intent in ("project_lookup", "project_members", "project_domain_members", "total_members"):
            return self._format_deterministic(user_message=user_message, intent=intent, entities=entities, tool=tool, data=data)

        # If the user explicitly asks for a count or a list, keep it deterministic.
        if wants_count or wants_list:
            if intent in ("list_projects", "list_ongoing_projects", "project_tasks", "project_tasks_status"):
                return self._format_deterministic(user_message=user_message, intent=intent, entities=entities, tool=tool, data=data)

        if self._settings.use_llm_formatter:
            return self._format_with_llm(user_message=user_message, intent=intent, entities=entities, tool=tool, data=data)
        return self._format_deterministic(user_message=user_message, intent=intent, entities=entities, tool=tool, data=data)

    def _format_deterministic(self, *, user_message: str, intent: Any, entities: dict, tool: Any, data: Any) -> str:
        lowered = (user_message or "").lower()
        wants_count = "how many" in lowered or "count" in lowered or "number of" in lowered
        wants_list = any(
            k in lowered
            for k in [
                "who",
                "list",
                "show",
                "which",
                "what are",
                "what tasks",
                "tasks in",
                "members in",
                "projects in",
            ]
        )

        if isinstance(data, dict) and data.get("error"):
            return str(data["error"])

        if intent == "project_progress" and isinstance(data, dict):
            return (
                f"Project: {data.get('project')}\n"
                f"Status: {data.get('status')}\n"
                f"Progress: {data.get('progressPercent')}% ({data.get('tasks', {}).get('done')}/{data.get('tasks', {}).get('total')} tasks done)"
            )

        if intent in ("project_members", "project_domain_members") and isinstance(data, dict):
            project_name = data.get("project")
            domain = data.get("domain") if intent == "project_domain_members" else None
            count = data.get("count")
            members = data.get("members") or []
            if wants_count and not wants_list:
                if count == 0:
                    suffix = f" (domain: {domain})" if domain else ""
                    return f"Project: {project_name}{suffix}\nMembers: 0 (no members assigned yet)"
                suffix = f" (domain: {domain})" if domain else ""
                return f"Project: {project_name}{suffix}\nMembers: {count}"
            # Default: show list (trimmed)
            header = f"Project: {project_name}" + (f" (domain: {domain})" if domain else "")
            lines = [header, f"Members: {count}"]
            if count == 0:
                lines.append("No members are assigned to this project yet.")
            if isinstance(members, list) and members:
                preview = []
                for m in members[:25]:
                    user_id = m.get("userId")
                    role = m.get("role")
                    user = m.get("user") or {}
                    name = user.get("name") or user.get("displayName")
                    if user_id and role:
                        preview.append(f"{user_id}{' - ' + str(name) if name else ''} ({role})")
                    elif user_id:
                        preview.append(f"{user_id}{' - ' + str(name) if name else ''}")
                if preview:
                    lines.append("- " + ", ".join(preview))
                if len(members) > 25:
                    lines.append(f"...and {len(members) - 25} more")
            return "\n".join(lines)

        if intent in ("project_tasks", "project_tasks_status"):
            # New shape: dict with metadata
            if isinstance(data, dict) and "tasks" in data:
                tasks = data.get("tasks") or []
                project_name = data.get("project")
                project_code = data.get("projectCode")
                status = data.get("status")
                count = data.get("count", len(tasks))

                if wants_count and not wants_list:
                    suffix = f" (status: {status})" if status else ""
                    if count == 0:
                        return f"Project: {project_name} ({project_code})\nTasks: 0{suffix}"
                    return f"Project: {project_name} ({project_code})\nTasks: {count}{suffix}"

                if not tasks:
                    suffix = f" with status {status}" if status else ""
                    return f"Project: {project_name} ({project_code})\nNo tasks found{suffix}."

                title = "Tasks:" if not status else f"Tasks (status: {status}):"
                lines = [f"Project: {project_name} ({project_code})", title]
                for t in tasks[:25]:
                    lines.append(f"- {t.get('issueKey')}: {t.get('summary')} ({t.get('status')})")
                if len(tasks) > 25:
                    lines.append(f"...and {len(tasks) - 25} more")
                return "\n".join(lines)

            # Backward compatibility: old shape was list
            if isinstance(data, list):
                if not data:
                    return "No tasks found."
                if wants_count and not wants_list:
                    return f"Tasks found: {len(data)}"
                lines = ["Tasks:"]
                for t in data[:25]:
                    lines.append(f"- {t.get('issueKey')}: {t.get('summary')} ({t.get('status')})")
                if len(data) > 25:
                    lines.append(f"...and {len(data) - 25} more")
                return "\n".join(lines)

        if intent == "department_members" and isinstance(data, dict):
            if "count" in data:
                return f"Department '{data.get('department')}': {data.get('count')} members"

        if intent == "domain_members" and isinstance(data, dict):
            if "count" in data:
                return f"Domain '{data.get('domain')}': {data.get('count')} members"

        if intent == "total_members" and isinstance(data, dict):
            return f"Total members: {data.get('count')} (source: {data.get('source')})"

        if intent == "project_lookup" and isinstance(data, dict):
            if data.get("found") is True:
                return (
                    "Project found:\n"
                    f"- name: {data.get('name')}\n"
                    f"- projectCode: {data.get('projectCode')}\n"
                    f"- _id: {data.get('_id')}\n"
                    f"- status: {data.get('status')}"
                )
            if data.get("found") is False:
                return f"No project found with name/code '{data.get('project')}'."

        if intent in ("list_projects", "list_ongoing_projects") and isinstance(data, list):
            if not data:
                return "No projects found."
            if wants_count and not wants_list:
                return f"Projects found: {len(data)}"
            title = "Ongoing projects" if intent == "list_ongoing_projects" else "All projects"
            lines = [f"{title}:"]
            for p in data[:25]:
                lines.append(f"- {p.get('name')} ({p.get('status')})")
            if len(data) > 25:
                lines.append(f"...and {len(data) - 25} more")
            return "\n".join(lines)

        return "Here are the results." if data is not None else "I couldn't find an answer for that."

    def _format_with_llm(self, *, user_message: str, intent: Any, entities: dict, tool: Any, data: Any) -> str:
        try:
            client = GeminiClient()
        except Exception:
            return self._format_deterministic(user_message=user_message, intent=intent, entities=entities, tool=tool, data=data)

        prompt = (
            "You are a response-writer for an organization chatbot.\n"
            "Write a short, clear answer for a business user.\n\n"
            "User request:\n"
            f"{user_message}\n\n"
            "Context:\n"
            f"- intent: {intent}\n"
            f"- tool: {tool}\n"
            f"- entities: {entities}\n"
            f"- data: {data}\n\n"
            "Rules:\n"
            "- If data contains an error, explain it briefly and suggest what to provide.\n"
            "- If user asks 'how many', prioritize a count. If user asks 'who/list/show', include key items.\n"
            "- Keep the answer under 6 lines.\n"
        )
        return client.generate_text(prompt)
