# Migrations

The application currently creates tables automatically for the local SQLite prototype. Production deployments should use Alembic against PostgreSQL before starting the API. This directory records the first schema boundary and is intentionally kept separate from runtime `create_all` behavior.

Recommended production command sequence:

```powershell
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
