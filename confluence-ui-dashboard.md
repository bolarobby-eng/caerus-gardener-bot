# Gardener Bot v2 — Test UI and Staff Dashboard

## Overview

A browser-based test UI and staff dashboard have been added to the Gardener Bot v2 MVP so the prototype can be tested without curl/Postman and operated like a small production workflow.

## URLs

- Home: `http://100.101.206.14:8787/`
- Test chat UI: `http://100.101.206.14:8787/chat`
- Staff dashboard: `http://100.101.206.14:8787/staff`
- API health: `http://100.101.206.14:8787/health`
- n8n webhook remains: `POST http://100.101.206.14:5678/webhook/793a998f-2e3b-473a-8b68-8720f9e92087`

## Test Chat UI

The test chat page provides a simple customer-style chat interface.

It supports:

- sender/test identity selection
- new test conversations
- sending customer messages from the browser
- receiving bot replies in chat format
- showing route metadata such as `faq`, `booking`, `quote`, `handoff`, `status`, or `cancel`
- showing whether staff action is required

The chat UI calls the same secure API used by the n8n webhook. It is intended for quick manual testing and demos while WhatsApp is not connected.

## Staff Dashboard

The staff dashboard provides an operations view over the Postgres-backed MVP.

Current dashboard sections:

- summary metrics: customers, appointments, quotes, handoffs, audit events
- appointment requests
- quote requests
- handoff cases
- conversation list
- full inbound/outbound message view per conversation
- recent audit events

Current staff actions:

- update appointment status: `requested`, `proposed`, `confirmed`, `completed`, `cancelled`, `handoff_required`
- update quote status: `new`, `needs_info`, `quoted`, `accepted`, `rejected`, `archived`
- update handoff status: `open`, `assigned`, `resolved`, `archived`

Every staff status update writes an audit event.

## Verification Completed

Smoke tests completed successfully:

- home page returns HTTP 200
- chat page returns HTTP 200
- staff dashboard returns HTTP 200
- browser-style `/v1/ui/send` message creates a booking request and returns a bot reply
- staff overview API returns metrics, appointment records, and conversations
- appointment status update works
- quote status update works
- handoff status update works
- full automated MVP webhook suite still passes: 9 passed / 0 failed on run `20260509211059`

## Implementation Notes

- Code lives in `/home/robby/gardener-bot-v2/app/main.py`.
- README updated at `/home/robby/gardener-bot-v2/README.md`.
- The API now logs outbound bot replies into `message_events`, so dashboard conversations show both customer and bot messages.
- The dashboard is currently intended for Tailscale/VPS prototype access. Before wider exposure, add staff authentication and role-based access control.

## Next Improvements

- Add staff login/auth before exposing beyond the private tailnet.
- Add filters/search for date, status, sender, service type, and priority.
- Add staff notes and assignment fields.
- Add outbound staff reply capability from the dashboard.
- Add CSV export for operational reporting.
- Add richer structured extraction for date/time/service details.
