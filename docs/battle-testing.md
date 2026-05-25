# Battle Testing - 2026-05-25

## Scope

Expanded the live regression coverage from 62 complex conversations to 101 battle-test conversations. The suite covers:

- Quote requests across lawn mowing, hedge trimming, weeding, garden clearance, planting, and garden design.
- Multi-service quotes and quote updates.
- Appointment booking, quote-to-consultation handoff, status, cancellation, and rebooking.
- Messy multi-turn intake with missing name, phone, address, postcode, service, dimensions, and availability.
- Unsupported requests mixed with valid gardening work.
- Bogus personal-grooming requests using gardening tools.
- Prompt injection, customer-data exfiltration, SQL/API-key/system-prompt requests, and third-party appointment queries.
- Duplicate/idempotent webhook behaviour.
- Existing customer profile reuse and active quote updates.

## Failures Found

The expanded run initially passed 93/101 and exposed these real issues:

- Name capture rejected bare names containing service-like words, such as `Clear Split`, because `clear` matched garden clearance keywords.
- Unsupported car-cleaning requests were described generically, which made the scope boundary less clear.
- Explicit requests to speak to a human were handled as FAQ-style text rather than a staff handoff.
- Rebooking after cancellation with "instead" forgot the previous appointment service and asked the customer to choose a service again.

Four other failures were test expectation issues rather than product bugs:

- Cancel/status with no appointment returned the right safe reply, but the assertion was too brittle around the exact contraction.
- A same-conversation hedge follow-up correctly updated the active quote rather than creating a separate quote.
- A postcode-only reply correctly kept asking for the customer's name, but the assertion inspected hidden `missing_fields` rather than customer-visible text.
- An unsupported car-cleaning reply correctly avoided creating work, but the assertion expected the exact word `car`.

## Fixes Implemented

- Relaxed bare-name extraction so plausible names are not rejected solely because a word overlaps a service keyword.
- Improved unsupported service labelling for car-cleaning requests.
- Added explicit human/staff handoff detection and a real handoff route response.
- Added booking context reuse for rebook/reschedule/instead messages so the bot can carry forward the previous service, postcode, notes, and job.
- Tightened the battle-test assertions where they were checking implementation details instead of user-visible behaviour.

## Verification

All tests were run against the rebuilt Docker service at `http://100.101.206.14:8788`.

- `test_complex_cases.py`: 101/101 passed, run `20260525210300`.
- `test_refined_cases.py`: 29/29 passed, run `20260525210907`.
- `test_mvp.py`: 27/27 passed, run `20260525211122`.

Health check after rebuild:

- `/health` returned `{"ok":true,"service":"caerus-gardener-bot-api"}`.
