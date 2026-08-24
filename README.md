# NAVI

**Your AI guide through the U.S. healthcare system.**

NAVI is a privacy-first, agentic healthcare navigation platform. It converts unstructured
requests — *"my doctor ordered an MRI"* — into personalized workflows spanning insurance
coverage, prior authorization, in-network provider discovery, cost estimation, and
scheduling.

## Architecture

```
                         ┌──────────────┐
   member request  ───▶  │  supervisor   │  classifies intent, builds an agent plan
                         └──────┬───────┘
                                │
          ┌─────────────┬──────┴──────┬────────────────┐
          ▼             ▼             ▼                ▼
    ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────────┐
    │ insurance │ │ provider  │ │   cost    │ │  authorization    │
    │  agent    │ │  agent    │ │  agent    │ │     agent         │
    └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────────┬─────────┘
          │             │             │                 │
          └─────────────┴──────┬──────┴─────────────────┘
                                ▼
                        ┌───────────────┐
                        │ safety agent  │  hallucination / groundedness /
                        │ (human-in-loop)│  sensitive-data / medical-risk checks
                        └───────┬───────┘
                                ▼
                         member-facing reply
                    (or escalation to a human)
```

Each specialist agent is scoped to only the health context it needs (see
[`app/rag/retriever.py`](backend/app/rag/retriever.py)) — the cost agent never sees
medication history, the safety agent never sees raw insurance IDs it doesn't need —
and calls domain tools (provider search, cost estimation, prior-auth rules) via
LLM tool calling. The **safety agent is a mandatory final checkpoint**: it screens
every result for hallucination, missing groundedness, sensitive-data exposure, and
medical risk, and explicitly escalates to a human instead of answering when it isn't
confident. No autonomous clinical decision-making.

## Stack

| Layer | Technology |
|---|---|
| Agent orchestration | Python, LangGraph, LangChain |
| LLM | Claude (Anthropic) |
| API | FastAPI |
| Data | PostgreSQL + pgvector, SQLAlchemy, Alembic |
| Document intelligence | OCR (Tesseract), layout-aware parsing, FHIR R4 |
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS |

## Project layout

```
backend/
  app/
    agents/       # LangGraph graph, prompts, domain tools, shared state
    api/routes/    # auth, chat, care journeys, document upload
    models/        # SQLAlchemy models (users, policies, claims, journeys, ...)
    rag/           # scoped health-context retriever + embeddings
    services/      # document intelligence (OCR/extraction), FHIR builders
  alembic/         # database migrations
frontend/
  app/             # Next.js routes (chat, login, dashboard)
  components/      # ChatInterface, CareJourneyTimeline
  lib/api.ts       # typed API client
```

## Running locally

### With Docker

```bash
cp backend/.env.example backend/.env   # add your ANTHROPIC_API_KEY
docker compose up --build
```

Frontend: http://localhost:3000 · Backend: http://localhost:8000/api/health

### Without Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY and a running Postgres URL
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

## Privacy

Insurance documents, claims, EOBs, medications, and visits live in a user-owned
Postgres schema. Agents retrieve only the narrow slice of that data their task
requires (`app/rag/retriever.py`'s `SCOPE_PERMISSIONS`), and every agent action —
including safety escalations — is written to an append-only audit log
(`app/models/audit.py`).

## Status

Early-stage engineering project. The provider directory, cost estimator, and prior-auth
checker in `app/agents/domain_tools.py` are currently deterministic mocks with the real
integration point documented inline (payer eligibility APIs, NPI registry, fee
schedules) — swapping them for live integrations doesn't require touching the agent
graph.

## License

[MIT](LICENSE)
