# Operator guide

This is for the person who owns the sales workflow and the connected accounts. If you are deploying the server, use the [deployment runbook](DEPLOYMENT.md).

## First-time setup

1. Ask the deployer for the Pond URL and your operator login/credentials.
2. Open **Integration health** on the dashboard.
3. Configure integrations in this order:
   - OpenAI, if model-assisted scoring/drafting is enabled.
   - Google Workspace for Calendar, Drive, Gmail drafts, and Sheets.
   - X search, if an approved provider is available.
   - LinkedIn only after account permission and Terms of Service review.
4. Open settings and enter the operator timezone, ICP, offer name, proof points, and exclusions.
5. Use the setup card for each integration. For Google, select **Connect Google account** if the deployer has configured OAuth; otherwise follow the server setup instructions shown in the card.
6. Run a manual Warm Signal test with a small fixture set.
7. Paste one consented test call into Deal Debrief.
8. Confirm that drafts and reminders are proposals only and that no message was sent.

## Daily Warm Signal review

1. Open the Warm Signal queue. Use search and status filters when the queue is large.
2. Open each source link and compare the quoted evidence to the generated message.
3. Choose one action:
   - **Approve** — marks the proposal ready for manual sending.
   - **Skip 90 days** — suppresses the lead temporarily.
   - **Do not contact** — permanently suppresses the lead until manually changed.
4. Send approved social or email messages yourself from the native provider application.
5. Use the lead CSV export when you need a copy for review or handoff.
6. Record meaningful outcomes in the CRM view.

The system should never be used as permission to send a message that has not been reviewed.

## Daily Deal Debrief review

1. Confirm the event and account are correct.
2. Review the summary, evidence, stage, and every next step.
3. Correct any owner or date that is uncertain. Unknown values should remain unknown.
4. Approve the debrief.
5. Use **Prepare actions** to create a reminder/draft proposal.
6. Open Gmail and Calendar, review the proposed content, and perform the final human action there.

No-show calls should not receive a follow-up email draft. Missing transcripts should remain visible as awaiting notes.

## What to do when an integration says `needs_setup`

Open the integration card, follow its setup instructions, then return to the card and select **I’ve configured this**. If the status does not change, give the deployer the provider name, timestamp, and visible error; never paste secrets into a ticket or chat.
