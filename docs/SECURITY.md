# Security notes

## Required controls before production

- Database-backed authentication, secure sessions, CSRF protection, and owner/reviewer authorization
- Secret-manager-backed credentials
- HTTPS only
- Restricted CORS
- OAuth state and callback validation
- Provider scopes limited to the documented minimum
- Rate limiting and request size limits
- Audit log retention and access controls
- Redaction of transcript text and sensitive model traces
- Dependency and container vulnerability scanning
- Database backups and restoration tests

Production requires `APP_ENV=production`; this disables the local development authentication bypass. Set `COOKIE_SECURE=true`, use HTTPS, and rotate the bootstrap password after first login.

## Data handling

Call notes and CRM data can contain personal and commercial information. Keep raw transcripts out of logs, retain only the evidence needed for the workflow, and define deletion/retention rules with the operator.

## Approval boundary

The operator must review social outreach, Gmail drafts, stage changes, reminders, and any CRM projection that could affect customer-facing work. A model response is never sufficient authorization for an external action.
