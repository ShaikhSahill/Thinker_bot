from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class IntentMatch:
    intent: str
    entities: dict


class IntentClassifier:
    """Lightweight rules layer to catch known intents fast.

    This is deliberately conservative: it only matches what we explicitly support.
    """

    _STATUS_RE = re.compile(r"\b(pending|todo|to\s*do|in\s*progress|in-progress|done|completed)\b", re.I)

    def classify(self, message: str):
        text = message.strip()
        if not text:
            return None

        lowered = text.lower()

        # list projects
        if ("list" in lowered or "show" in lowered) and ("projects" in lowered or "project" in lowered):
            if "ongoing" in lowered or "in progress" in lowered or "in-progress" in lowered or "active" in lowered:
                return IntentMatch(intent="list_ongoing_projects", entities={})
            if "all" in lowered:
                return IntentMatch(intent="list_projects", entities={})

        # project lookup (existence / id)
        if "project" in lowered and (
            "is there" in lowered
            or "any project" in lowered
            or "exists" in lowered
            or "with name" in lowered
            or "named" in lowered
        ):
            entities = self._extract_project_entities(text)
            if not entities.get("project") and "with name" in lowered:
                entities["project"] = self._extract_after_phrase(text, "with name") or ""
                entities["project"] = entities["project"].strip(" ?.!\"'")
                if not entities["project"]:
                    entities.pop("project", None)
            return IntentMatch(intent="project_lookup", entities=entities)

        # project progress
        if "progress" in lowered and "project" in lowered:
            entities = self._extract_project_entities(text)
            return IntentMatch(intent="project_progress", entities=entities)

        # project members
        if ("member" in lowered or "members" in lowered) and ("project" in lowered or "working on" in lowered):
            entities = self._extract_project_entities(text)
            # If the user omitted the word 'project', try extracting after 'working on'.
            if not entities.get("project") and "working on" in lowered:
                entities["project"] = self._extract_after_phrase(text, "working on") or ""
                entities["project"] = entities["project"].strip(" ?.!\"'")
                if not entities["project"]:
                    entities.pop("project", None)
            return IntentMatch(intent="project_members", entities=entities)

        # project tasks (optionally status)
        if ("task" in lowered or "tasks" in lowered) and "project" in lowered:
            entities = self._extract_project_entities(text)
            status = self._extract_status(text)
            if status:
                entities["status"] = status
                return IntentMatch(intent="project_tasks_status", entities=entities)
            return IntentMatch(intent="project_tasks", entities=entities)

        # department members
        if ("member" in lowered or "members" in lowered) and "department" in lowered:
            dept = self._extract_after_keyword(text, "department")
            if dept:
                return IntentMatch(intent="department_members", entities={"department": dept})

        # domain members
        if ("who" in lowered or "members" in lowered) and ("frontend" in lowered or "backend" in lowered or "ui" in lowered or "ux" in lowered or "qa" in lowered or "tester" in lowered):
            domain = self._extract_domain(lowered)
            if domain:
                return IntentMatch(intent="domain_members", entities={"domain": domain})

        return None

    def _extract_project_entities(self, text: str) -> dict:
        entities: dict = {}
        lowered = text.lower()
        idx = lowered.find("project")
        if idx == -1:
            return entities

        tail = text[idx + len("project") :].strip()
        tail = re.sub(r"^(of|named|named\s+as|called|with\s+name|with\s+name\s+as|name|name\s+as|as|:|-)+\s*", "", tail, flags=re.I)
        tail = tail.strip().strip('"').strip()

        # Split optional "under <department>".
        under_match = re.search(r"\bunder\b", tail, flags=re.I)
        if under_match:
            project_part = tail[: under_match.start()].strip()
            dept_part = tail[under_match.end() :].strip()
            dept_part = dept_part.strip(" ?.!\"'")
            if dept_part:
                entities["department"] = dept_part
        else:
            project_part = tail

        project_part = project_part.strip(" ?.!\"'")
        project_part = re.sub(r"^(as)\s+", "", project_part, flags=re.I)
        if project_part:
            entities["project"] = project_part

        return entities

    def _extract_status(self, text: str):
        m = self._STATUS_RE.search(text)
        if not m:
            return None
        word = m.group(1).lower().replace(" ", "")
        mapping = {
            "pending": "TODO",
            "todo": "TODO",
            "inprogress": "IN_PROGRESS",
            "in-progress": "IN_PROGRESS",
            "done": "COMPLETED",
            "completed": "COMPLETED",
        }
        return mapping.get(word)

    def _extract_after_keyword(self, text: str, keyword: str):
        # naive: "... in the tech department" or "department tech"
        lowered = text.lower()
        idx = lowered.find(keyword.lower())
        if idx == -1:
            return None
        tail = text[idx + len(keyword) :].strip(" ?")
        # strip leading prepositions
        tail = re.sub(r"^(in|of|for|the)\s+", "", tail, flags=re.I)
        return tail.strip() or None

    def _extract_after_phrase(self, text: str, phrase: str):
        lowered = text.lower()
        idx = lowered.find(phrase.lower())
        if idx == -1:
            return None
        tail = text[idx + len(phrase) :].strip()
        tail = re.sub(r"^(in|of|for|the)\s+", "", tail, flags=re.I)
        tail = re.sub(r"^(as)\s+", "", tail, flags=re.I)
        return tail.strip() or None

    def _extract_domain(self, lowered: str):
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
