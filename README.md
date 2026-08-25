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

## Production hardening

This isn't just a demo scaffold — it's built to handle real PHI, with the caveats in
[Status](#status) below:

- **Encryption**: PHI columns (member IDs, claim numbers, visit notes, OCR'd document
  text) are encrypted at the field level with Fernet, on top of transport/disk
  encryption — see [`app/core/crypto.py`](backend/app/core/crypto.py).
- **Auth**: httpOnly/Secure session cookies (not localStorage), short-lived access
  tokens with rotating/revocable refresh tokens, bcrypt password hashing, and account
  lockout after repeated failed logins.
- **Real provider data**: provider search hits the live, public CMS NPI Registry — no
  contract required. Network status, cost estimates, and prior-auth checks go through
  a pluggable `EligibilityProvider` (mock by default) — see
  [`app/integrations/`](backend/app/integrations/). Every result is tagged
  `data_source`, and the safety agent forces a visible disclaimer into its reply
  whenever any figure shown to a member is simulated rather than real.
- **Defense in depth**: per-IP rate limiting, upload validation (type/size/filename
  sanitization), ownership checks on every resource, structured logs with automatic
  PHI redaction, an append-only audit log, and a right-to-deletion endpoint.
- **Ops**: GitHub Actions CI (lint, tests, build) on every push, a Render deployment
  blueprint ([`render.yaml`](render.yaml)), and a real pytest suite
  ([`backend/tests/`](backend/tests/)).
- **Compliance groundwork**: see [`SECURITY.md`](SECURITY.md),
  [`COMPLIANCE_CHECKLIST.md`](COMPLIANCE_CHECKLIST.md), and
  [`DEPLOYMENT.md`](DEPLOYMENT.md) for what's implemented vs. what still requires a
  signed BAA or legal review before this touches real customer data.

## Project layout

```
backend/
  app/
    agents/        # LangGraph graph, prompts, domain tools, shared state
    api/routes/    # auth, account, chat, care journeys, document upload
    core/          # config, crypto, security, logging, rate limiting, audit
    integrations/  # real NPI registry client, pluggable eligibility provider
    models/        # SQLAlchemy models (users, policies, claims, journeys, ...)
    rag/           # scoped health-context retriever + embeddings
    services/      # document intelligence (OCR/extraction), FHIR builders
  alembic/         # database migrations
  tests/           # pytest suite
frontend/
  app/             # Next.js routes (chat, login, dashboard)
  components/      # ChatInterface, CareJourneyTimeline
  lib/api.ts       # typed API client (cookie-based auth)
legal/             # draft ToS / Privacy Policy / medical disclaimer — NOT final, needs attorney review
```

## Running locally

### With Docker

```bash
cp backend/.env.example backend/.env
# edit backend/.env: set ANTHROPIC_API_KEY and FIELD_ENCRYPTION_KEYS (required — see
# the comment above it in .env.example for the one-liner that generates a key)
docker compose up --build
```

Frontend: http://localhost:3000 · Backend: http://localhost:8000/api/health

### Without Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY, FIELD_ENCRYPTION_KEYS, and a running Postgres URL
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

### Running tests

```bash
cd backend && source .venv/bin/activate
python -m pytest -q
ruff check app tests alembic
```

### Deploying

See [`DEPLOYMENT.md`](DEPLOYMENT.md) — includes the Render setup and, importantly,
which steps (BAAs, secrets) only a human with account access can do.

## Privacy

Insurance documents, claims, EOBs, medications, and visits live in a user-owned
Postgres schema. Agents retrieve only the narrow slice of that data their task
requires (`app/rag/retriever.py`'s `SCOPE_PERMISSIONS`), and every agent action —
including safety escalations — is written to an append-only audit log
(`app/models/audit.py`).

## Status

Provider *identity* search is real (CMS NPI Registry). Network status, cost estimates,
and prior-authorization checks are simulated by default — that data genuinely requires
a contracted clearinghouse relationship (e.g. Availity), not a public API — but the
integration point is a drop-in adapter (`app/integrations/eligibility.py`), every
simulated result is explicitly tagged, and the product visibly discloses it to members
rather than presenting fabricated coverage/cost data as real.

Before this handles real customer PHI: BAAs must be signed with every vendor that
touches data (hosting, Anthropic, any embeddings/clearinghouse provider — none of
these can be signed by an AI agent), and the organizational items in
[`COMPLIANCE_CHECKLIST.md`](COMPLIANCE_CHECKLIST.md) (risk assessment, designated
privacy/security officer, incident response plan) need to be completed. See
[`DEPLOYMENT.md`](DEPLOYMENT.md) for the full checklist.

## License

[MIT](LICENSE)
