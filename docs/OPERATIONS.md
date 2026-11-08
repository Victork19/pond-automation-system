# Operations runbook

## Health checks

```powershell
Invoke-RestMethod http://localhost:8000/api/health
Invoke-RestMethod http://localhost:8000/api/integrations
Invoke-RestMethod http://localhost:8000/api/runs
```

## Safe pause procedure

1. Disable scheduled jobs in the deployment environment.
2. Leave the API available so the operator can review existing records.
3. Disable the affected integration from configuration.
4. Inspect the latest run, audit event, and provider error.
5. Resume only after a manual fixture run passes.

## Incident priorities

**P0:** unauthorized send, credential exposure, duplicate external writes, or data isolation failure. Disable the affected integration immediately and preserve audit logs.

**P1:** repeated failed runs, missing digest deadline, OAuth expiry, transcript retrieval failure, or database/Redis outage.

**P2:** stale Sheets projection, UI error, non-critical notification failure, or a single provider query failure.

## Backups

Back up PostgreSQL daily and before migrations. Keep backups encrypted, access-controlled, and off-host. Test restoration at least monthly. Redis does not replace database backups.

## Logs

Do not log access tokens, OAuth codes, full transcripts, or unnecessary personal data. Include run ID, task ID, provider, stage, attempt, duration, result, and safe error code.
