# Project Structure Guide (Folders + Files)

This document explains what each folder/file in this repo is for.

## Top-level

- `.env`
  - Local runtime configuration (secrets/URLs). Loaded by `pydantic-settings` via `app/settings.py`.
  - Not meant to be committed (contains secrets).

- `.env.example`
  - Example template of environment variables you should set in `.env`.

- `.venv/`
  - Local Python virtual environment.
  - Not used as source code; safe to ignore in git.

- `__pycache__/`
  - Python bytecode cache created automatically.
  - Safe to delete; it will be regenerated.

- `requirements.txt`
  - Python dependencies used by the app (FastAPI, Motor/Mongo, Socket.IO, Gemini, etc.).

- `main.py`
  - Uvicorn entrypoint.
  - Imports `create_app()` from `app/main.py` and exposes `app = create_app()`.
  - Run example: `python -m uvicorn main:app`.

- `README.md`
  - Intended to be project documentation.
  - Note: in this workspace it currently contains Python code (looks like it was overwritten). Consider restoring it to documentation.

- `scripts/`
  - One-off utilities / developer scripts (not part of the runtime API).
  - Example: `scripts/db_inspect.py` connects to Mongo and prints/inspects collections.

- `app/`
  - The application package (all runtime code).

## app/

### app/main.py
- Creates the FastAPI app (`create_app`).
- Registers API routes and mounts Socket.IO.
- Also exposes `/health`.

### app/settings.py
- Central settings object (`Settings`) using `pydantic-settings`.
- Reads values from `.env` (Mongo URI/DB, Gemini key/model, host/port, etc.).

### app/api/
- FastAPI route definitions.

#### app/api/v1/chat_routes.py
- `POST /api/v1/chat`
- Accepts `ChatRequest` and returns `ChatResponse`.
- Delegates main logic to `ChatService`.

### app/schemas/
- Pydantic models for request/response payloads.

#### app/schemas/chat_request.py
- Defines the incoming request for chat.
- Fields:
  - `message` (required)
  - `queryId`, `userJourneyId` (optional tracking)
  - `tenantId`, `sessionId` (optional context)

#### app/schemas/chat_response.py
- Defines the outgoing chat response.
- High-level shape:
  - `queryId`, `userJourneyId`, `role`, `responses[]`, `createdAt`
- `responses[]` is a list of cards (`ResponseCard`) with:
  - `card_type`: string
  - `answers`: free-form dict (supports HTML via `answer_response`, tables via `columns/rows`, actions, etc.)

### app/services/
- Business logic layer (orchestration).

#### app/services/chat_service.py
- Core orchestrator for chat.
- Responsibilities:
  - Classifies intent/entities (rules layer first, then LLM fallback).
  - Maps intent → tool.
  - Executes allowlisted tools via the registry.
  - Formats the reply.
  - Builds structured card-based `ChatResponse` (e.g., `OPEN_AI` card + optional `TABLE` card).

### app/RAGX_layer/
- Lightweight rules-based intent/entity extraction.

#### app/RAGX_layer/intent_classifier.py
- `IntentClassifier` tries to match supported intents quickly using regex/string rules.
- Avoids calling the LLM when it can.

### app/agents/
- “Agent” wrappers for LLM routing/formatting.

#### app/agents/llm_agent.py
- If rules don’t match, asks Gemini to choose one allowed tool and extract entities.
- Should fail-safe when Gemini is unavailable.

#### app/agents/msg_formatter_agent.py
- Converts tool results into a human-friendly string.
- Can be deterministic or LLM-based (controlled by `Settings.use_llm_formatter`).

### app/tools/
- Implementations of the allowlisted “tools” the chatbot can call.

#### app/tools/registry_factory.py
- Registers tool specs (name/description/parameters) + functions into `ToolRegistry`.
- This is the allowlist the LLM/router must obey.

#### app/tools/tool_registry.py
- Simple registry that maps tool-name → spec/function.

#### app/tools/project_tools.py
- Mongo-backed project tools: find project, list projects, project tasks, members, progress.

#### app/tools/org_tools.py
- Mongo-backed org tools: department/domain members, total members.

### app/infrastructure/
- External integrations (DB, LLM, realtime transport).

#### app/infrastructure/database/mongo_connection.py
- Creates/returns a Motor (async) MongoDB client and database handle.

#### app/infrastructure/llm/gemini_client.py
- Gemini wrapper that can generate text or JSON.
- Reads API key + model from `Settings`.

#### app/infrastructure/socketio/server.py
- Socket.IO server mounted at `/ws`.
- Emits/handles `chat` events and returns chat results.

## What is safe to ignore/remove?

- Safe to delete anytime:
  - `__pycache__/` folders

- Safe to keep out of git (but keep locally if you use them):
  - `.venv/`
  - `.env`

- Optional utilities (not required for app runtime):
  - `scripts/` (e.g., `scripts/db_inspect.py`)

