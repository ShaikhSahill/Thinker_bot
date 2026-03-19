from __future__ import annotations

from typing import Any
from typing import Optional

from app.RAGX_layer.intent_classifier import IntentClassifier
from app.agents.llm_agent import LlmAgent
from app.agents.msg_formatter_agent import MsgFormatterAgent
from app.schemas.chat_request import ChatRequest
from app.schemas.chat_response import ChatResponse
from app.settings import Settings
from app.tools.registry_factory import build_default_registry


class ChatService:
    def __init__(self) -> None:
        self._settings = Settings()
        self._registry = build_default_registry()
        self._ragx = IntentClassifier()
        self._llm = LlmAgent(self._registry)
        self._formatter = MsgFormatterAgent()

    async def handle_http(self, req: ChatRequest) -> ChatResponse:
        result = await self._handle(message=req.message, tenant_id=req.tenantId)
        return ChatResponse(**result)

    async def handle_socket(self, message: str, tenant_id: Optional[str] = None) -> dict[str, Any]:
        return await self._handle(message=message, tenant_id=tenant_id)

    async def _handle(self, *, message: str, tenant_id: Optional[str]) -> dict[str, Any]:
        tenant_id = tenant_id or self._settings.default_tenant_id

        # RAGX: cheap supported-intent check + entity extraction.
        match = self._ragx.classify(message)
        if match is not None:
            intent = match.intent
            entities = match.entities
            tool = self._intent_to_tool(intent)
        else:
            # LLM fallback: still constrained to our allowlisted tools.
            selection = self._llm.select_tool(message)
            intent = selection.get("intent")
            tool = selection.get("tool")
            entities = selection.get("entities") or {}

        if tool is None:
            return {
                "reply": self._unsupported_message(),
                "intent": None,
                "tool": None,
                "entities": entities,
                "data": None,
            }

        # Validate minimal entities.
        missing = self._missing_required(tool, entities)
        if missing:
            return {
                "reply": f"I can help, but I need: {', '.join(missing)}.",
                "intent": intent,
                "tool": tool,
                "entities": entities,
                "data": None,
            }

        fn = self._registry.get_fn(tool)
        if fn is None:
            return {
                "reply": self._unsupported_message(),
                "intent": intent,
                "tool": tool,
                "entities": entities,
                "data": None,
            }

        # Execute tool (read-only queries).
        payload = dict(entities)
        global_tools = {"list_projects", "list_ongoing_projects", "find_project"}
        if tool not in global_tools:
            payload.setdefault("tenant_id", tenant_id)
        try:
            data = await fn(**payload)
        except Exception as e:
            data = {"error": f"Tool execution failed: {type(e).__name__}: {e}"}

        reply = self._formatter.format(user_message=message, intent=intent, entities=entities, tool=tool, data=data)
        return {"reply": reply, "intent": intent, "tool": tool, "entities": entities, "data": data}

    def _intent_to_tool(self, intent: str):
        mapping = {
            "project_progress": "get_project_progress",
            "project_members": "get_project_members",
            "project_tasks": "get_project_tasks",
            "project_tasks_status": "get_project_tasks_by_status",
            "department_members": "get_department_members",
            "domain_members": "get_domain_members",
            "total_members": "get_total_members",
            "list_projects": "list_projects",
            "list_ongoing_projects": "list_ongoing_projects",
            "project_lookup": "find_project",
        }
        return mapping.get(intent)

    def _missing_required(self, tool: str, entities: dict) -> list[str]:
        spec = self._registry.get_spec(tool)
        if spec is None:
            return []
        required = spec.parameters.get("required") or []
        missing = []
        for r in required:
            if entities.get(r) in (None, ""):
                missing.append(r)
        return missing

    def _unsupported_message(self) -> str:
        return (
            "An AI response is not available for that query yet.\n"
            "Try one of these: list projects, list ongoing projects, project progress, project members, project tasks (optionally by status), department members, domain members, total members."
        )
