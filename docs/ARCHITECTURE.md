# Architecture

## Request path

```text
Browser
  -> FastAPI validation/API
  -> PostgreSQL transaction + audit event
  -> Celery/Redis job for long work
  -> bounded agent proposal or provider adapter
  -> deterministic validation
  -> human approval
  -> provider action proposal/execution
```

## Source of truth

PostgreSQL is canonical. Google Sheets is a projection and may lag or fail without invalidating the database record.

## Boundaries

- `app/main.py`: HTTP routes and approval boundary.
- `app/db.py`: operational data model.
- `app/workflows/`: deterministic Warm Signal and Deal Debrief logic.
- `app/policies.py`: suppression and stage-transition rules.
- `app/agents.py`: optional model proposal boundary.
- `app/integrations.py`: provider adapter boundary.
- `app/jobs.py`: asynchronous job boundary.
- `frontend/`: operator review surface.

## Safety rules

1. Agents propose structured results; they do not own writes.
2. Every external write needs an idempotency key.
3. Every factual extracted item needs evidence.
4. Gmail remains draft-only in the MVP.
5. LinkedIn remains disabled until explicit review.
6. Unknown dates, owners, budgets, and commitments remain unknown.
