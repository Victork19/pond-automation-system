# Troubleshooting

## The page does not load

Check that the API is running and that `frontend/` exists in the application image. Then call `/api/health` directly.

## An integration remains `needs_setup`

Check the environment variables on the API container, not only on the local shell. Restart the API after changing environment values. Do not paste secrets into the dashboard or support messages.

## A lead is missing

Check the source lookback window, total score threshold, existing identity key, skip suppression, and do-not-contact status. The system intentionally does not pad the shortlist.

## A debrief has no email draft

Confirm that usable notes/transcript exist. No-show and missing-source cases intentionally do not create an email draft.

## Worker jobs are not moving

Check Redis reachability, `CELERY_ENABLED`, worker logs, beat logs, and the database job/run record. Redis is not the source of truth; inspect PostgreSQL for the persisted state.

## Docker cannot start

Confirm Docker is installed, ports are available, `.env` exists, and the host has persistent volume permissions. Run `docker compose config` before `docker compose up`.
