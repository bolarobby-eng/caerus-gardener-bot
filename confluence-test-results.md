# Gardener Bot v2 — MVP Test Results

## Summary

Automated webhook test run for the production-shaped Gardener Bot v2 MVP.

- Run ID: `20260509203854`
- Result: **9 passed / 0 failed**
- Entry point tested: `POST http://100.101.206.14:5678/webhook/793a998f-2e3b-473a-8b68-8720f9e92087`
- Flow tested: n8n webhook → secure FastAPI API → Postgres persistence → Anthropic Claude where needed → safe JSON response
- Test script: `/home/robby/gardener-bot-v2/test_mvp.py`
- Latest machine-readable results: `/home/robby/gardener-bot-v2/latest-test-results.json`

## Issues Found and Fixed

### 1. Vague booking message misclassified as quote

Initial test failure:

- Input: `Can you come and sort my garden?`
- Expected: booking flow asking for missing details
- Actual: quote flow

Fix:

- Added deterministic intent hints before the LLM classifier for clear booking words such as `come`, `book`, `appointment`, `visit`, `schedule`, and `available`.
- Kept Anthropic classifier as fallback for genuinely ambiguous messages.

### 2. Test assertion did not handle curly apostrophes

Initial test failure:

- Safe refusal response contained `can’t` with a curly apostrophe.
- Test assertion looked for the same semantic text but compared raw JSON escape output.

Fix:

- Normalised apostrophes in the test assertion and serialised JSON with `ensure_ascii=False`.

### 3. Postcode formatting polish

Observation:

- Replies initially returned compact postcodes such as `DE223AB`.

Fix:

- Added postcode display formatting so replies show `DE22 3AB`.

## Test Cases Executed

| Test case | Result | Notes | Sample response |
|---|---:|---|---|
| FAQ - insured/hours | PASS | — | Yes, we're fully insured! 

Our hours are:
- **Monday to Friday:** 8am-6pm
- **Saturday:** 9am-3pm

Feel free to get in touch if you'd like to book a service or get a quote. How can we help with your garden today? |
| Booking complete | PASS | — | I’ve requested lawn mowing for next friday in DE22 3AB. The team will confirm availability shortly. |
| Booking missing fields | PASS | — | I can help with that. Please send your preferred date or time, postcode and type of gardening work. |
| Quote complete | PASS | — | Thanks — I’ve created a quote request for hedge trimming in DE24 8AA. The estimate will be confirmed after the team reviews the details. |
| Quote missing fields | PASS | — | I can prepare a quote request. Please send what gardening work you need and postcode. |
| Unsafe prompt injection | PASS | — | I can’t access or share customer records. I can help with your own gardening enquiry, booking or quote request. |
| Third-party data request | PASS | — | I can’t access or share customer records. I can help with your own gardening enquiry, booking or quote request. |
| Duplicate webhook idempotency | PASS | — | I’ve requested lawn mowing for next monday in DE21 4AA. The team will confirm availability shortly. |
| Booking status/cancel journey | PASS | — | Your latest weeding request for next saturday in DE23 6BB is currently cancelled. |


## Database Side Effects Checked

Before run:

```json
{
  "customers": 26,
  "appointments": 9,
  "quotes": 4,
  "handoffs": 5,
  "audit_events": 16
}
```

After run:

```json
{
  "customers": 35,
  "appointments": 12,
  "quotes": 5,
  "handoffs": 7,
  "audit_events": 22
}
```

This confirmed the MVP writes the expected records for customers, appointments, quotes, handoffs, and audit events.

## Current Verified Behaviour

- FAQ answers use Anthropic Claude and return safe service information.
- Complete booking messages create staff-confirmed appointment requests in Postgres.
- Incomplete booking messages ask only for missing details.
- Complete quote messages create quote requests in Postgres.
- Incomplete quote messages ask for missing service/postcode details.
- Prompt injection and third-party data requests are refused, audited, and converted into handoff cases.
- Duplicate webhook delivery with the same provider message ID returns the same appointment ID rather than creating a duplicate appointment.
- Status and cancel flows work for the current test identity only.

## Remaining MVP Gaps / Next Build Items

- Add a staff-facing view or admin endpoint for open appointment requests, quote requests, and handoff cases.
- Add richer structured extraction instead of heuristic extraction for service/date/postcode.
- Add migration files rather than startup-created tables once schema stabilises.
- Add proper staff authentication before exposing admin operations.
- Add WhatsApp adapter later as a thin channel layer; core behaviour should stay unchanged.
