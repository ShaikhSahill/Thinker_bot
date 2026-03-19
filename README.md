# Org ChatBot (FastAPI + MongoDB + Gemini)

Read-only org chatbot backend that answers questions about projects, tasks, and members from MongoDB.

## What’s implemented

Architecture matches your diagram:
- **RAGX layer**: rule-based intent matcher for supported queries
- **LLM agent (Gemini)**: fallback intent/entity extraction + tool selection (allowlisted)
- **Tools**: MongoDB query functions (no create/update routes)
- **Message formatter**: deterministic formatting by default, optional Gemini formatting
- **API**: `POST /api/v1/chat` for Postman
- **Socket.IO**: mounted at `/ws/socket.io`

## Setup

1) Create `.env` from `.env.example`

2) Install deps:

```bash
pip install -r requirements.txt
```

3) Run:

```bash
uvicorn main:app --reload
```

Health check:
- `GET http://localhost:8000/health`

## Postman

### Chat
- Method: `POST`
- URL: `http://localhost:8000/api/v1/chat`
- Body (JSON):

```json
{
  "message": "What is the progress of Inventory Management System?",
  "tenantId": "client-105"
}
```

### Supported query examples

- List all projects
  - `List all the projects`
- List ongoing projects
  - `List all the ongoing projects`

- Project progress
  - `What is the progress of project Inventory Management System?`
- Project members
  - `How many members are working on project Inventory Management System?`
- Project tasks
  - `What tasks are in project Inventory Management System?`
- Project tasks by status
  - `Show pending tasks in project Inventory Management System`
- Total members
  - `How many total members are there?`

Note: `department_members` and `domain_members` require a `users` collection with fields like `userId`, `name`, `department`, `domain`.
