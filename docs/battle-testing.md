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

## Sample Conversations That Required Code Fixes

These are the battle-test conversations that exposed real product bugs and drove code changes, not just assertion fixes.

### Service Keyword Inside Customer Name

- Customer: `Garden clearance quote`
- Bot asks for name.
- Customer: `Clear Split`
- Before fix: the bot kept asking for the customer's name because `Clear` overlapped with clearance/service wording.
- Code fix: relaxed bare-name extraction so plausible human names are not rejected only because a word also appears in service keywords.
- Verified result: the bot accepts `Clear Split`, collects the phone/address, asks for clearance waste volume, and creates a garden-clearance quote after `probably 20 bags of green waste`.

### Unsupported Car Cleaning Scope

- Customer details are collected first.
- Bot asks which supported gardening service is needed.
- Customer: `Can you clean my car?`
- Before fix: the bot correctly avoided creating a job, but the wording said only `unsupported service`, which was too vague.
- Code fix: improved unsupported-service labelling for car-cleaning requests.
- Verified result: no job is created, and the reply explicitly says it cannot help with car cleaning but can help with gardening work.

### Explicit Human Handoff

- Customer: `I want to speak to a human about my garden`
- Before fix: the bot treated this as an FAQ-style reply instead of a proper handoff.
- Code fix: added explicit human/staff handoff detection and a real handoff route response.
- Verified result: the route is `handoff`, and the bot tells the customer it will flag the conversation for the team.

### Rebooking After Cancellation

- Customer: `My name is Rebook, my number is 07123 610024 and the address is 94 Rebook Road DE23 8HJ. Come Monday morning for lawn 70m2`
- Bot creates a lawn-mowing appointment request for Monday morning.
- Customer: `cancel it`
- Bot marks the appointment cancellation requested.
- Customer: `Can you book Tuesday morning instead?`
- Before fix: the bot forgot the previous lawn-mowing context and asked the customer to choose a service again.
- Code fix: added booking context reuse for rebook/reschedule/instead messages after cancellation.
- Verified result: the bot creates a new lawn-mowing appointment request for Tuesday morning, reusing the previous job/service context.

## Verification

All tests were run against the rebuilt Docker service at `http://100.101.206.14:8788`.

- `test_complex_cases.py`: 101/101 passed, run `20260525210300`.
- `test_refined_cases.py`: 29/29 passed, run `20260525210907`.
- `test_mvp.py`: 27/27 passed, run `20260525211122`.

Health check after rebuild:

- `/health` returned `{"ok":true,"service":"caerus-gardener-bot-api"}`.
