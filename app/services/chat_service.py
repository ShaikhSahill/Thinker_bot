from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from typing import Optional
from uuid import uuid4

from app.RAGX_layer.intent_classifier import IntentClassifier
from app.agents.llm_agent import LlmAgent
from app.agents.msg_formatter_agent import MsgFormatterAgent
from app.schemas.chat_request import ChatRequest
from app.schemas.chat_response import ChatResponse, ResponseCard, SourceRef
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
        return self._to_chat_response(
            query_id=req.queryId,
            user_journey_id=req.userJourneyId or req.sessionId,
            user_message=req.message,
            result=result,
        )

    async def handle_socket(self, message: str, tenant_id: Optional[str] = None) -> dict[str, Any]:
        result = await self._handle(message=message, tenant_id=tenant_id)
        resp = self._to_chat_response(
            query_id=None,
            user_journey_id=None,
            user_message=message,
            result=result,
        )
        return resp.model_dump(mode="json")

    def _to_chat_response(
        self,
        *,
        query_id: Optional[str],
        user_journey_id: Optional[str],
        user_message: str,
        result: dict[str, Any],
    ) -> ChatResponse:
        now = datetime.now(timezone.utc)
        query_id = query_id or f"q-{uuid4().hex[:12]}"
        user_journey_id = user_journey_id or f"uj-{now.strftime('%Y%m%d')}-{uuid4().hex[:8]}"

        reply = (result or {}).get("reply") or ""
        intent = (result or {}).get("intent")
        tool = (result or {}).get("tool")
        entities = (result or {}).get("entities") or {}
        data = (result or {}).get("data")

        responses: list[ResponseCard] = []

        # Primary card: formatted text/HTML
        open_ai_answers: dict[str, Any] = {
            "answer_response": self._to_html(reply),
        }

        sources = self._build_sources(intent=intent, data=data)
        if sources:
            open_ai_answers["sources"] = [s.model_dump(mode="json") for s in sources]
        if tool:
            open_ai_answers["reason"] = f"Generated from tool '{tool}'."

        responses.append(ResponseCard(card_type="OPEN_AI", answers=open_ai_answers))

        # Optional: structured table card for list-like results.
        table_card = self._build_table_card(intent=intent, entities=entities, data=data)
        if table_card is not None:
            responses.append(table_card)

        return ChatResponse(
            queryId=query_id,
            userJourneyId=user_journey_id,
            role="bot",
            responses=responses,
            createdAt=now,
        )

    def _to_html(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "<p></p>"
        # If it already looks like HTML, pass through.
        if "<" in text and ">" in text:
            return text
        parts = [p.strip() for p in text.split("\n") if p.strip()]
        if not parts:
            return "<p></p>"
        if len(parts) == 1:
            return f"<p>{parts[0]}</p>"
        return "<p>" + "<br/>".join(parts) + "</p>"

    def _build_sources(self, *, intent: Any, data: Any) -> list[SourceRef]:
        sources: list[SourceRef] = []
        if not data:
            return sources
        if isinstance(data, dict) and data.get("error"):
            return sources

        if intent in ("project_tasks", "project_tasks_status") and isinstance(data, dict):
            for t in (data.get("tasks") or [])[:25]:
                issue_key = t.get("issueKey")
                summary = t.get("summary")
                link = t.get("link") or t.get("url")
                if issue_key and summary:
                    sources.append(SourceRef(type="task", id=str(issue_key), title=str(summary), link=link))
            return sources

        if intent in ("list_projects", "list_ongoing_projects") and isinstance(data, list):
            for p in data[:25]:
                name = p.get("name")
                project_code = p.get("projectCode")
                link = p.get("link") or p.get("url")
                if name:
                    sources.append(SourceRef(type="project", id=str(project_code or name), title=str(name), link=link))
            return sources

        if intent in ("project_members", "project_domain_members") and isinstance(data, dict):
            for m in (data.get("members") or [])[:25]:
                user_id = m.get("userId")
                user = m.get("user") or {}
                title = user.get("name") or user.get("displayName") or user_id
                link = user.get("link") or user.get("url")
                if user_id:
                    sources.append(SourceRef(type="member", id=str(user_id), title=str(title or user_id), link=link))
            return sources

        if intent in ("department_members", "domain_members") and isinstance(data, dict):
            for u in (data.get("members") or [])[:25]:
                user_id = u.get("userId") or u.get("email") or u.get("name")
                title = u.get("name") or u.get("displayName") or user_id
                link = u.get("link") or u.get("url")
                if user_id:
                    sources.append(SourceRef(type="member", id=str(user_id), title=str(title or user_id), link=link))
            return sources

        return sources

    def _build_table_card(self, *, intent: Any, entities: dict, data: Any) -> Optional[ResponseCard]:
        if not data:
            return None
        if isinstance(data, dict) and data.get("error"):
            return None

        if intent in ("project_tasks", "project_tasks_status") and isinstance(data, dict) and "tasks" in data:
            tasks = data.get("tasks") or []
            columns = ["Issue Key", "Summary", "Status"]
            rows = []
            for t in tasks[:100]:
                rows.append([
                    str(t.get("issueKey") or ""),
                    str(t.get("summary") or ""),
                    str(t.get("status") or ""),
                ])
            return ResponseCard(
                card_type="TABLE",
                answers={
                    "columns": columns,
                    "rows": rows,
                    "reason": "Task-service generated table",
                },
            )

        if intent in ("list_projects", "list_ongoing_projects") and isinstance(data, list):
            columns = ["Project", "Status"]
            rows = []
            for p in data[:100]:
                rows.append([str(p.get("name") or ""), str(p.get("status") or "")])
            return ResponseCard(
                card_type="TABLE",
                answers={
                    "columns": columns,
                    "rows": rows,
                    "reason": "Project-service generated table",
                },
            )

        if intent in ("project_members", "project_domain_members") and isinstance(data, dict):
            members = data.get("members") or []
            columns = ["User ID", "Name", "Role"]
            rows = []
            for m in members[:100]:
                user = m.get("user") or {}
                rows.append([
                    str(m.get("userId") or ""),
                    str(user.get("name") or user.get("displayName") or ""),
                    str(m.get("role") or ""),
                ])
            return ResponseCard(
                card_type="TABLE",
                answers={
                    "columns": columns,
                    "rows": rows,
                    "reason": "Member-service generated table",
                },
            )

        if intent in ("department_members", "domain_members") and isinstance(data, dict):
            members = data.get("members") or []
            columns = ["User ID", "Name"]
            rows = []
            for u in members[:100]:
                rows.append([
                    str(u.get("userId") or ""),
                    str(u.get("name") or u.get("displayName") or ""),
                ])
            return ResponseCard(
                card_type="TABLE",
                answers={
                    "columns": columns,
                    "rows": rows,
                    "reason": "Org-service generated table",
                },
            )

        return None

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

        # Robustness: if the user clearly asked for a domain within a project,
        # force the domain-filtered tool even if selection picked generic project members.
        inferred_domain = self._infer_domain_from_message(message)
        if (
            tool == "get_project_members"
            and inferred_domain
            and isinstance(entities, dict)
            and entities.get("project")
        ):
            entities["domain"] = inferred_domain
            intent = "project_domain_members"
            tool = "get_project_members_by_domain"

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

    def _infer_domain_from_message(self, message: str) -> Optional[str]:
        lowered = (message or "").lower()
        if "front" in lowered:
            return "frontend"
        if "back" in lowered:
            return "backend"
        if "ui" in lowered and "ux" in lowered:
            return "uiux"
        if "ui" in lowered:
            return "ui"
        if "ux" in lowered:
            return "ux"
        if "qa" in lowered or "tester" in lowered or "quality" in lowered:
            return "qa"
        return None

    def _intent_to_tool(self, intent: str):
        mapping = {
            "project_progress": "get_project_progress",
            "project_members": "get_project_members",
            "project_domain_members": "get_project_members_by_domain",
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
