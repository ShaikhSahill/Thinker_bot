from __future__ import annotations

from typing import Any, Dict, Optional

from app.infrastructure.llm.gemini_client import GeminiClient
from app.tools.tool_registry import ToolRegistry


class LlmAgent:
    """Extract intent/entities and select one allowed tool."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def select_tool(self, message: str) -> Optional[Dict[str, Any]]:
        try:
            client = GeminiClient()
        except Exception:
            # Gemini not configured; caller can still answer via rules/tools.
            return {"intent": None, "tool": None, "entities": {}}

        specs = self._registry.list_specs()
        tool_block = "\n".join(
            [
                f"- {s.name}: {s.description} parameters={s.parameters}"
                for s in specs
            ]
        )

        prompt = f"""
You are an enterprise org chatbot router.
Your job: choose EXACTLY ONE tool from the allowed list to answer the user.

Allowed tools:
{tool_block}

Rules:
- Only output JSON.
- If the user asks for something not supported by these tools, output JSON with tool=null and intent=null.
- Extract entities needed for the chosen tool.
- Use keys: intent, tool, entities.
- intent should be one of: list_projects, list_ongoing_projects, project_lookup, project_progress, project_members, project_tasks, project_tasks_status, department_members, domain_members, total_members.

User message:
{message}

Output JSON schema:
{{
  "intent": string|null,
  "tool": string|null,
  "entities": object
}}
""".strip()

        try:
            data = client.generate_json(prompt)
        except Exception:
            # Gemini call failed (missing/invalid key, network, permission, etc).
            return {"intent": None, "tool": None, "entities": {}}
        tool = data.get("tool")
        if tool is None:
            return {"intent": None, "tool": None, "entities": {}}

        if tool not in self._registry.list_names():
            return {"intent": None, "tool": None, "entities": {}}

        entities = data.get("entities") or {}
        if not isinstance(entities, dict):
            entities = {}

        return {"intent": data.get("intent"), "tool": tool, "entities": entities}
