# Pond Automation System

_Handoff note: this is written for the next person who has to run, deploy, or maintain Pond._

Pond is an approval-first sales operations workspace for two workflows:

1. **Warm Signal** finds public buying-intent signals, scores them, and prepares outreach for human review.
2. **Deal Debrief** turns call notes into evidence-backed debriefs, next steps, reminders, and Gmail draft proposals.

The system never sends outreach or email automatically. It stores proposals and waits for an explicit human decision.

## Start here

| You are… | Read this first |
|---|---|
| An operator using Pond | [Operator guide](docs/OPERATOR_GUIDE.md) |
| Deploying the system | [Deployment runbook](docs/DEPLOYMENT.md) |
| Connecting Google/X/LinkedIn/OpenAI | [Integration guide](docs/INTEGRATIONS.md) |
| Taking over the codebase | [Architecture](docs/ARCHITECTURE.md) |
| Running or supporting it | [Operations](docs/OPERATIONS.md) |
| Reviewing security | [Security notes](docs/SECURITY.md) |

## Choose a run mode

### Local development — no external accounts required

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/>. Local mode uses SQLite and manual inputs so a new developer can exercise the workflows immediately.

### Container deployment — PostgreSQL, Redis, API, worker, and scheduler

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

Then open <http://127.0.0.1:8000/> and follow the integration setup cards. See [Deployment](docs/DEPLOYMENT.md) for production requirements.

## What is implemented

- Warm Signal normalization, scoring, dedupe, evidence, draft validation, approval, skip, and do-not-contact policies.
- Deal Debrief notes intake, evidence capture, next-step extraction, stage safeguards, retry metadata, and action proposals.
- Operator settings, integration health, audit events, idempotency records, and a review dashboard.
- Integration setup cards, Google OAuth handoff, queue filtering, and lead CSV export.
- Docker Compose service topology and PostgreSQL schema reference.
- Optional OpenAI agent boundary; deterministic backend services remain responsible for validation and writes.

## What still requires account setup

Google OAuth and APIs, X search, LinkedIn read-only access, OpenAI model execution, and production authentication require credentials and permissions owned by the deploying organization. The app reports these as `needs_setup` until configured; clicking a setup button does not make a provider look connected.

## Verification

```powershell
python -m pytest -q
python -m compileall -q app
node --check frontend/app.js
node --check frontend/integrations.js
```

Expected result: all tests pass. Docker validation requires Docker Desktop or Docker Engine.
# pond-automation-system
