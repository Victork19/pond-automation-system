# Deployment runbook

## Responsibility split

**Deployer:** host, DNS/TLS, environment secrets, database, Redis, containers, OAuth callback URLs, backups, monitoring, and release verification.

**Operator:** provider account authorization, ICP/offer settings, review decisions, and manual sending from native tools.

The deployment is not finished when the containers are healthy. The operator still needs to connect approved accounts and complete one test run for each enabled workflow.

## Prerequisites

- Docker Engine or Docker Desktop with Compose
- A persistent host or managed container platform
- A persistent PostgreSQL volume or managed PostgreSQL instance
- A persistent Redis instance
- A DNS name and TLS termination for production
- Provider credentials documented in [Integrations](INTEGRATIONS.md)

## Local container launch

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
docker compose logs -f api
```

Open the API at port `8000`. Do not expose the local Compose stack directly to the public internet.

## Production checklist

- [ ] Replace all local PostgreSQL credentials.
- [ ] Set `APP_ENV=production`.
- [ ] Use a managed secret store; do not commit `.env`.
- [ ] Set `DATABASE_URL` to PostgreSQL.
- [ ] Set `REDIS_URL` to managed Redis.
- [ ] Set a real `OPERATOR_TIMEZONE`.
- [ ] Configure TLS and reverse proxy headers.
- [ ] Restrict CORS to the real frontend origin.
- [ ] Configure OAuth redirect URLs exactly.
- [ ] Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI` before using the Google setup button.
- [x] Compose runs the one-shot migration service before API, worker, and beat.
- [x] Compose starts API, worker, and beat only after migration and Redis health checks pass.
- [x] Compose health-checks API, PostgreSQL, and Redis.
- [ ] Configure daily encrypted backups and test restoration.
- [ ] Verify pause-all and integration-disable controls.
- [ ] Run the acceptance checklist before enabling scheduled runs.

## Release sequence

1. Build and tag the image.
2. `docker compose up --build -d` runs the migration service and starts the dependent services.
3. Verify `/api/health` and `docker compose ps` show healthy services.
4. Confirm the bootstrap admin can sign in and rotate its password.
5. Verify the dashboard loads and integrations show expected states.
6. Open integration setup and confirm every enabled provider has the expected status.
7. Run one manual Warm Signal fixture run.
8. Run one manual Deal Debrief fixture.
9. Download a lead CSV and verify the contents.
10. Confirm no provider send operation was called.
11. Enable the weekday schedule only after the operator signs off.

## Current migration note

Local SQLite uses SQLAlchemy `create_all` for convenience. Production PostgreSQL must apply `migrations/versions/0001_initial.sql` and `0002_production_auth_and_entities.sql` with a controlled migration job. Set `SESSION_SECRET`, `GOOGLE_TOKEN_ENCRYPTION_KEY`, and bootstrap admin credentials in the secret manager before startup. Verify login, session expiry, CSRF rejection, and logout from the production hostname.
