#!/usr/bin/env python3
import json
import time
import urllib.parse
import urllib.request

BASE = "http://100.101.206.14:8788"
RUN = str(int(time.time()))


def post(sender, conv, message, n):
    payload = {
        "message": message,
        "sender_id": sender,
        "sender_name": None,
        "provider_message_id": f"v3-regression-{RUN}-{sender}-{n}",
        "conversation_id": conv,
        "channel": "test_webhook",
    }
    req = urllib.request.Request(
        BASE + "/v1/ui/send",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode())


def traces(conv):
    url = BASE + "/v1/staff/planner-traces/" + urllib.parse.quote(conv, safe="")
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode())


def planner_reply(conv):
    events = traces(conv).get("planner_events", [])
    if not events:
        return ""
    output = events[-1].get("planner_output")
    if isinstance(output, str):
        output = json.loads(output)
    return output.get("reply", "")


def check(name, condition, failures):
    if not condition:
        failures.append(name)


def main():
    failures = []

    sender = f"v3-regression-hello-{RUN}"
    conv = f"{sender}-conv"
    response = post(sender, conv, "Hello there", 1)
    check("hello stays faq", response.get("route") == "faq", failures)
    check("hello creates no workflow", not any(response.get(k) for k in ("job_id", "quote_request_id", "appointment_id", "handoff_id")), failures)
    check("hello reply is planner-owned", response.get("reply") == planner_reply(conv), failures)

    sender = f"v3-regression-intake-{RUN}"
    conv = f"{sender}-conv"
    response = post(sender, conv, "I need a quote for hedge trimming please", 1)
    check("intake reply is planner-owned", response.get("reply") == planner_reply(conv), failures)
    check("legacy address prompt absent", "Thanks. What’s the job address and postcode?" not in response.get("reply", ""), failures)

    sender = f"v3-regression-loft-{RUN}"
    conv = f"{sender}-conv"
    post(sender, conv, "Hello there", 1)
    response = post(sender, conv, "I want my loft converted into a living space, can you quote?", 2)
    check("loft is faq", response.get("route") == "faq", failures)
    check("loft creates no workflow", not any(response.get(k) for k in ("job_id", "quote_request_id", "appointment_id", "handoff_id", "handoff_required")), failures)
    check("loft reply is planner-owned", response.get("reply") == planner_reply(conv), failures)
    check("loft makes no tool calls", not traces(conv).get("tool_calls"), failures)

    sender = f"v3-regression-quote-{RUN}"
    conv = f"{sender}-conv"
    response = post(sender, conv, "My name is V Three, my number is 07123 955101 and the address is 11 Planner Road DE23 8HJ. I need a quote for lawn mowing, about 80m2.", 1)
    check("valid quote creates quote", response.get("route") == "quote" and response.get("job_id") and response.get("quote_request_id"), failures)
    check("valid quote reply is planner-owned", response.get("reply") == planner_reply(conv), failures)

    result = {"ok": not failures, "failures": failures}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if not failures else 1)


if __name__ == "__main__":
    main()
