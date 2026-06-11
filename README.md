# Caerus Gardener Bot — Generic Bot v4 Runtime

Webhook-first Caerus Gardener Bot rebuild running on the VPS.

## Runtime

- Test UI: `http://100.101.206.14:8788/chat`
- Staff dashboard: `http://100.101.206.14:8788/staff`
- API health: `GET http://100.101.206.14:8788/health`
- API version: `1.0.0-v4`
- API service: Docker Compose in `/home/robby/caerus-gardener-bot`
- Database: Postgres 16 Docker volume `caerus-gardener-bot_postgres_data`
- n8n public-channel workflow: not connected yet. Use `/v1/ui/send` and the browser test chat for v4 testing.

## Test payload

```json
{
  "message": "Can you come next Monday morning to mow my lawn in DE22 3AB?",
  "sender_id": "test-customer-001",
  "sender_name": "Robby",
  "provider_message_id": "unique-message-id"
}
```

## v4 behaviour

- The LLM planner owns every normal customer turn: route selection, workflow readiness, requested backend tool actions, and the customer-facing reply.
- The backend does not run keyword-led normal routing or fixed intake/reply templates. It only loads context, validates the planner plan, applies hard safety/privacy/schema/booking guards, executes requested canonical actions, and persists traces.
- Browser chat UI lets testers send/receive messages without curl/Postman.
- Staff dashboard shows customers, projects, jobs, indicative estimates, appointments, handoff cases, conversations, tool calls, planner traces, and audit events.
- Runtime uses the canonical Generic Bot route enum only: `identify_customer`, `new_project`, `existing_project`, `appointment_management`, `customer_update`, `faq`, `out_of_scope`, `hard_invariant`.
- Backend work uses the canonical 17 tool actions and schema version 4 conversation state.
- Tenant-specific service, FAQ, pricing, and booking rules come from the embedded `2026-06-11.mock-1` gardener business pack.
- Appointment creation/rescheduling runs `check_appointment_availability` before mutation and stores the `availability_check_id`.
- Pure FAQ and out-of-scope turns use exact no-action wire format: `tool_actions: []`.
- Unsafe/prompt-injection/customer-data requests are refused, audited, and create handoff cases.
- The direct test UI calls the secure API. A future public-channel workflow should call the same API boundary; the API owns data access, validation, audit logging, and persistence.

## Files

- API/UI/dashboard code: `/home/robby/caerus-gardener-bot/app/main.py`
- Secrets/env: `/home/robby/caerus-gardener-bot/.env` (`0600`, do not commit/share)

## Commands

```bash
cd /home/robby/caerus-gardener-bot
docker compose ps
docker compose logs -f api
docker compose up -d --build api
python3 test_gardener_bot_canonical.py
python3 test_gardener_bot_battle.py
```
