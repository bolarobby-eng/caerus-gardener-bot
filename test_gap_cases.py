#!/usr/bin/env python3
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WEBHOOK = os.getenv("GARDENER_WEBHOOK", "http://100.101.206.14:8788/v1/ui/send")
SUMMARY = os.getenv("GARDENER_SUMMARY", "http://100.101.206.14:8788/v1/debug/summary")

SECRET = None
for line in open("/home/robby/caerus-gardener-bot/.env"):
    if line.startswith("TEST_WEBHOOK_SECRET="):
        SECRET = line.strip().split("=", 1)[1]

RUN = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
BASE = f"gap-{RUN}"


def post(payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(WEBHOOK, data=data, headers={"content-type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body
    except Exception as e:
        return 0, {"error": repr(e)}


def summary():
    req = urllib.request.Request(SUMMARY, headers={"x-gardener-test-secret": SECRET})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def text(obj):
    return json.dumps(obj, ensure_ascii=False).lower().replace("’", "'")


def has(obj, *needles):
    haystack = text(obj)
    return all(n.lower().replace("’", "'") in haystack for n in needles)


def ok_http(resp):
    return resp[0] == 200 and isinstance(resp[1], dict)


def mk(sender, message, n, conv=None, name=None, channel="test_webhook", provider_id=None):
    return {
        "message": message,
        "sender_id": sender,
        "sender_name": name,
        "provider_message_id": provider_id or f"{sender}-{n}",
        "conversation_id": conv or f"{sender}-conv",
        "channel": channel,
    }


def passfail(condition, reason):
    return (True, []) if condition else (False, [reason])


def final_body(rs):
    return rs[-1][1] if rs and ok_http(rs[-1]) else {}


def quote_created(*needles):
    def validate(rs):
        body = final_body(rs)
        ok = (
            body.get("route") in ("quote", "quote_update")
            and body.get("job_id")
            and body.get("quote_request_id")
            and has(body, "quote request", "initial consultation", *needles)
        )
        return passfail(ok, f"quote was not created with expected text {needles}")

    return validate


def booking_created(*needles):
    def validate(rs):
        body = final_body(rs)
        ok = (
            body.get("route") == "booking"
            and body.get("job_id")
            and body.get("appointment_id")
            and has(body, "confirm", *needles)
        )
        return passfail(ok, f"booking was not created with expected text {needles}")

    return validate


def no_work(*needles):
    def validate(rs):
        body = final_body(rs)
        ok = (
            ok_http(rs[-1])
            and not body.get("job_id")
            and not body.get("quote_request_id")
            and not body.get("appointment_id")
            and has(body, *needles)
        )
        return passfail(ok, f"response created work or missed {needles}")

    return validate


def handoff(*needles):
    def validate(rs):
        body = final_body(rs)
        ok = body.get("route") == "handoff" and body.get("handoff_required") and has(body, *needles)
        return passfail(ok, f"handoff missing expected text {needles}")

    return validate


def run_steps(index, name, steps, validate):
    sender = f"{BASE}-{index:03d}-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:38]}"
    conv = f"{sender}-conv"
    responses = []
    for n, step in enumerate(steps, 1):
        if isinstance(step, str):
            payload = mk(sender, step, n, conv=conv, name=None)
        else:
            payload = dict(step)
            payload.setdefault("sender_id", sender)
            payload.setdefault("sender_name", None)
            payload.setdefault("conversation_id", conv)
            payload.setdefault("provider_message_id", f"{sender}-{n}")
            payload.setdefault("channel", "test_webhook")
        resp = post(payload)
        responses.append({"step": n, "request": payload, "status": resp[0], "body": resp[1]})
    try:
        ok, reasons = validate([(r["status"], r["body"]) for r in responses])
    except Exception as e:
        ok, reasons = False, [f"validator exception: {e!r}"]
    return {"name": name, "ok": bool(ok), "reasons": reasons, "responses": responses}


def case(name, steps, validator):
    cases.append((name, steps, validator))


cases = []

case(
    "WhatsApp sender phone satisfies contact number",
    [
        mk(
            f"whatsapp:+447911{RUN[-6:]}",
            "My address is 12 Channel Road DE23 8HJ. Lawn mowing 75m2 please.",
            1,
            name="Channel Person",
            channel="whatsapp",
        )
    ],
    quote_created("lawn mowing"),
)

case(
    "Quoted phone sender without explicit number satisfies contact number",
    [
        mk(
            "+447911123457",
            "Address is 13 Phone Sender Road DE23 8HJ. Hedges about 11m long.",
            1,
            name="Phone Sender",
            channel="whatsapp",
        )
    ],
    quote_created("hedge trimming"),
)

case(
    "Quote with future window but explicit do not book",
    [
        "My name is No Booking, my number is 07123 900001 and the address is 14 No Book Road DE23 8HJ. Lawn 80m2. Friday morning might work later but do not book anything yet, I only want a quote."
    ],
    lambda rs: passfail(
        ok_http(rs[-1])
        and rs[-1][1].get("route") == "quote"
        and rs[-1][1].get("quote_request_id")
        and not rs[-1][1].get("appointment_id"),
        "explicit quote-only request created an appointment or failed quote",
    ),
)

case(
    "Next Friday evening appointment is rejected",
    [
        "My name is Evening Window, my number is 07123 900002 and the address is 15 Evening Road DE23 8HJ. Can you come next Friday at 7pm for lawn mowing 50m2?",
        "Friday morning then",
    ],
    booking_created("lawn mowing"),
)

case(
    "Saturday late afternoon appointment is rejected",
    [
        "My name is Late Saturday, my number is 07123 900003 and the address is 16 Saturday Road DE23 8HJ. Can you come Saturday at 4pm for hedges 10m long?",
        "Saturday morning is fine",
    ],
    booking_created("hedge trimming"),
)

case(
    "Reschedule without cancellation preserves appointment context",
    [
        "My name is Move Slot, my number is 07123 900004 and the address is 17 Move Road DE23 8HJ. Come Monday morning for lawn 60m2.",
        "Can we move that to Thursday afternoon?",
    ],
    lambda rs: passfail(
        ok_http(rs[-1])
        and rs[0][1].get("appointment_id")
        and rs[-1][1].get("route") == "booking"
        and rs[-1][1].get("appointment_id")
        and rs[-1][1].get("job_id") == rs[0][1].get("job_id"),
        "reschedule did not preserve job context and create/update appointment",
    ),
)

case(
    "Cancel quote request does not pretend appointment cancellation",
    [
        "My name is Quote Cancel, my number is 07123 900005 and the address is 18 Quote Cancel Road DE23 8HJ. Lawn mowing 90m2 quote please.",
        "Actually cancel that quote request please.",
    ],
    lambda rs: passfail(
        ok_http(rs[-1])
        and rs[0][1].get("quote_request_id")
        and not rs[-1][1].get("appointment_id")
        and rs[-1][1].get("quote_request_id") == rs[0][1].get("quote_request_id"),
        "quote cancellation was handled as appointment cancellation",
    ),
)

case(
    "Latest quote summary returns newest separate quote",
    [
        "My name is Two Summary, my number is 07123 900006 and the address is 19 Summary Road DE23 8HJ. Lawn mowing 50m2 quote please.",
        "I need a separate quote for hedge trimming, hedges are 12m long.",
        "What is in my quote?",
    ],
    lambda rs: passfail(
        ok_http(rs[-1])
        and rs[0][1].get("quote_request_id")
        and rs[1][1].get("quote_request_id")
        and rs[0][1].get("quote_request_id") != rs[1][1].get("quote_request_id")
        and has(rs[-1][1], "hedge trimming")
        and "lawn mowing" not in text(rs[-1][1]),
        "quote summary did not return latest separate quote",
    ),
)

case(
    "Tree surgery unsupported after profile",
    ["Hello", "Terry Tree", "07123 900007", "20 Tree Road DE23 8HJ", "Can you take down a tall tree near my garage?"],
    no_work("tree"),
)

case(
    "Fence repair unsupported after profile",
    ["Hi", "Fiona Fence", "07123 900008", "21 Fence Road DE23 8HJ", "Can you repair my broken garden fence?"],
    no_work("fence"),
)

case(
    "Pressure washing unsupported after profile",
    ["Hi", "Paula Pressure", "07123 900009", "22 Pressure Road DE23 8HJ", "Can you pressure wash the driveway?"],
    no_work("pressure"),
)

case(
    "Pest control unsupported after profile",
    ["Hello", "Peter Pest", "07123 900010", "23 Pest Road DE23 8HJ", "Can you get rid of rats in the garden?"],
    no_work("pest"),
)

case(
    "Mixed valid gardening and pressure washing still quotes valid work",
    [
        "My name is Mixed Pressure, my number is 07123 900011 and the address is 24 Mixed Road DE23 8HJ. Lawn mowing 65m2 please, and can you pressure wash the patio too?"
    ],
    quote_created("lawn mowing"),
)

case(
    "Customer asks to delete their data routes to handoff",
    ["Please delete all my data from your system."],
    handoff("team"),
)

case(
    "Customer asks for GDPR data copy routes to handoff",
    ["Can you send me a copy of all data you hold about me?"],
    handoff("team"),
)

case(
    "Customer refuses phone and asks human",
    ["I need a hedge quote.", "I do not want to give a phone number, can a human deal with this?"],
    handoff("team"),
)

case(
    "Approximate relative date with evening is rejected",
    [
        "My name is Tomorrow Night, my number is 07123 900012 and the address is 25 Tomorrow Road DE23 8HJ. Can you come tomorrow evening for lawn mowing 50m2?",
        "Tomorrow morning then",
    ],
    booking_created("lawn mowing"),
)

case(
    "Status for quote without appointment does not invent appointment",
    [
        "My name is Quote Status, my number is 07123 900013 and the address is 26 Quote Status Road DE23 8HJ. Lawn mowing 50m2 quote please.",
        "What is the status of my quote?",
    ],
    lambda rs: passfail(
        ok_http(rs[-1])
        and rs[0][1].get("quote_request_id")
        and not rs[-1][1].get("appointment_id")
        and "appointment" not in text(rs[-1][1]),
        "quote status was handled as appointment status",
    ),
)

case(
    "Address containing Status Road does not trigger status",
    [
        "My name is Safe Status, my number is 07123 900014 and the address is 27 Status Road DE23 8HJ. Garden clearance about 9 bags."
    ],
    quote_created("garden clearance"),
)

case(
    "Address containing Cancel Road does not trigger cancel",
    [
        "My name is Safe Cancel, my number is 07123 900015 and the address is 28 Cancel Road DE23 8HJ. Hedge trimming about 8m long."
    ],
    quote_created("hedge trimming"),
)

case(
    "User corrects postcode after pending quote",
    [
        "My name is Postcode Fix, my number is 07123 900016 and the address is 29 Wrong Road DE23 8HJ. Lawn mowing 60m2 quote please.",
        "Sorry, postcode is actually DE24 8AA.",
        "What is in my quote?",
    ],
    lambda rs: passfail(
        ok_http(rs[-1]) and has(rs[-1][1], "DE24 8AA"),
        "postcode correction was not reflected in quote summary",
    ),
)

case(
    "User says no hedges after multi-service quote and summary omits hedge",
    [
        "My name is Remove Hedge, my number is 07123 900017 and the address is 30 Remove Road DE23 8HJ. Lawn mowing 70m2 and hedges.",
        "Actually I do not have any hedges.",
        "What is in my quote?",
    ],
    lambda rs: passfail(
        ok_http(rs[-1])
        and has(rs[-1][1], "lawn mowing")
        and "hedge trimming" not in text(rs[-1][1]),
        "negated hedge remained in quote summary",
    ),
)


results = []
start = summary()
for idx, (name, steps, validator) in enumerate(cases, 1):
    results.append(run_steps(idx, name, steps, validator))
end = summary()

report = {
    "run_id": RUN,
    "suite": "gap",
    "total": len(results),
    "passed": sum(1 for r in results if r["ok"]),
    "failed": sum(1 for r in results if not r["ok"]),
    "started_summary": start,
    "ended_summary": end,
    "results": results,
}

Path(f"/home/robby/caerus-gardener-bot/gap-test-results-{RUN}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
Path("/home/robby/caerus-gardener-bot/latest-gap-test-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({
    "run_id": RUN,
    "suite": "gap",
    "total": report["total"],
    "passed": report["passed"],
    "failed": report["failed"],
    "failed_names": [{"name": r["name"], "reasons": r["reasons"]} for r in results if not r["ok"]],
}, indent=2))
sys.exit(1 if report["failed"] else 0)
