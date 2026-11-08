# Integration guide

Pond uses narrow provider adapters. Agents do not receive unrestricted access to Google, X, LinkedIn, or Gmail.

## Google Workspace

Purpose: Calendar event detection, Drive transcript lookup, private reminders, Gmail drafts, and Sheets projection.

Operator authorization required:

- Calendar event read/write for private reminders
- Drive read for transcript lookup
- Gmail draft creation only
- Sheets read/write for the CRM projection

Deployer setup:

1. Create a Google Cloud project.
2. Enable only the APIs required for the current release.
3. Create an OAuth web application client.
4. Add the exact production callback URL.
5. Store client ID and secret in the deployment secret manager.
6. Complete any Google sensitive-scope review required by the account.
7. Sign in to Pond and select **Connect Google account**. OAuth state is single-use and provider tokens are encrypted at rest.
8. Run one test Calendar reminder and Gmail draft. Pond never calls a Gmail send endpoint.

The application requests Gmail compose scope only and never requests Gmail send scope or calls a send endpoint.

## OpenAI

Purpose: bounded scoring, drafting, extraction, next-step auditing, and traces.

Set `OPENAI_API_KEY` and an explicit allowlisted `OPENAI_MODEL` on the server. Never put the key in frontend code, browser storage, or committed files. Model output is a proposal; the backend validates evidence, character limits, status transitions, and approvals.

## X

Read-only search only. Configure an approved provider through `X_PROVIDER` and its secret reference. Posting, replies, likes, follows, and engagement are outside the product boundary.

## LinkedIn

Disabled by default. Enable only after the organization confirms account permissions and current platform terms. The adapter must stop on login walls, checkpoints, CAPTCHAs, or rate-limit warnings. It must never bypass them.

## Redis / Celery

Redis is the broker and short-lived lock/cache. PostgreSQL remains the source of truth. Set `CELERY_ENABLED=true`, configure `REDIS_URL`, then run the worker and beat services.

## Integration status meanings

- `connected`: required configuration is present and the provider health check succeeded.
- `needs_setup`: the system can describe the integration, but credentials or OAuth authorization are incomplete.
- `disabled`: the capability is intentionally off by policy.
- `error`: the last provider operation failed; inspect the audit event and integration detail before retrying.
