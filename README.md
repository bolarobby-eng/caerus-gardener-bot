# Caerus Gardener Bot — Secure Webhook MVP

Webhook-first Caerus Gardener Bot MVP running on the VPS.

## Runtime

- Test UI: `http://100.101.206.14:8788/chat`
- Staff dashboard: `http://100.101.206.14:8788/staff`
- API health: `GET http://100.101.206.14:8788/health`
- API service: Docker Compose in `/home/robby/caerus-gardener-bot`
- Database: Postgres 16 Docker volume `caerus-gardener-bot_postgres_data`
- n8n public-channel workflow: not connected yet. Use `/v1/ui/send` and the browser test chat for MVP testing.

## Test payload

```json
{
  "message": "Can you come next Monday morning to mow my lawn in DE22 3AB?",
  "sender_id": "test-customer-001",
  "sender_name": "Robby",
  "provider_message_id": "unique-message-id"
}
```

## MVP behaviour

- Browser chat UI lets testers send/receive messages without curl/Postman.
- Staff dashboard shows metrics, conversations, appointment requests, quote requests, handoff cases, and audit events.
- Staff dashboard can update appointment, quote, and handoff statuses.
- FAQ replies via Anthropic Claude Haiku.
- Booking requests are staff-confirmed and stored in Postgres with status `requested`.
- Quote requests are stored in Postgres with status `new`.
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
```
