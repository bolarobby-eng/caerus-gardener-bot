#!/usr/bin/env python3
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


BASE = "http://100.101.206.14:8788"
RUN = str(int(time.time()))


def post(sender, conv, message, n):
    payload = {
        "message": message,
        "sender_id": sender,
        "sender_name": None,
        "provider_message_id": f"focus-{RUN}-{n}",
        "conversation_id": conv,
        "channel": "test_webhook",
    }
    req = urllib.request.Request(
        BASE + "/v1/ui/send",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode())


def traces(conv):
    url = BASE + "/v1/staff/planner-traces/" + urllib.parse.quote(conv, safe="")
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode())


def actions_for(tr, provider_message_id):
    return [
        call for call in tr.get("tool_calls", [])
        if call.get("provider_message_id") == provider_message_id
    ]


def fail(name, failures):
    if failures:
        print(json.dumps({"ok": False, "name": name, "failures": failures}, indent=2))
        raise SystemExit(1)


def future_saturday_label(days_ahead=14):
    day = datetime.now(timezone.utc).date() + timedelta(days=days_ahead)
    while day.weekday() != 5:
        day += timedelta(days=1)
    return day.strftime("%A %d %B")


def main():
    failures = []

    sender = f"focus-robert-{RUN}"
    conv = sender + "-conv"
    messages = [
        "hello",
        "i've got a lawn that is full of weeds that needs sorting",
        "name is robert johnson. 07815654345 and address is 8 Muirfield Drive, Nottingham, de45gh",
        "i don't need it mowing, i just need the weeds sorting. it's about 10m x 10m",
        "saturday morning in two weeks would be best pls",
    ]
    responses = [post(sender, conv, message, n) for n, message in enumerate(messages, 1)]
    tr = traces(conv)
    profile_actions = actions_for(tr, f"focus-{RUN}-3")
    profile_changed = [
        call.get("arguments", {}).get("changed_fields", {})
        for call in profile_actions
        if call.get("tool_name") == "upsert_customer_profile"
    ]
    if not any(changes.get("name") == "Robert Johnson" for changes in profile_changed):
        failures.append("name is Robert Johnson was not logged on first profile turn")

    project_actions = actions_for(tr, f"focus-{RUN}-4")
    project_services = [
        call.get("arguments", {}).get("service_key")
        for call in project_actions
        if call.get("tool_name") in {"add_project_job", "update_project_job"}
    ]
    if "weeding" not in project_services:
        failures.append("weeding job was not created/updated after 10m x 10m scope")
    if "lawn_mowing" in project_services:
        failures.append("lawn_mowing was created/updated after explicit customer exclusion")
    if not responses[3].get("project_id"):
        failures.append("project was not created once name, location, weeding service, and 10m x 10m scope were known")
    scope_reply = responses[3].get("reply", "")
    if not re.search(r"\b(when|date|time|slot|available|availability|free|suit|weekday|saturday|morning|afternoon)\b", scope_reply, re.I):
        failures.append("scope-complete reply did not ask for appointment availability immediately")
    if re.search(r"\b(i'?ll|i will|we'?ll|we will)\s+ask\b.{0,40}\b(later|once|after|next)\b", scope_reply, re.I):
        failures.append("scope-complete reply deferred appointment question to a future automatic follow-up")

    latest_plan = tr.get("planner_events", [])[-1].get("planner_output", {})
    latest_services = latest_plan.get("services") or []
    latest_missing = latest_plan.get("missing_fields") or []
    latest_reply = responses[-1].get("reply", "")
    if "lawn_mowing" in latest_services:
        failures.append("latest planner output still carries lawn_mowing")
    if any(str(item).startswith("lawn_mowing.") for item in latest_missing):
        failures.append("latest planner output still asks for lawn_mowing scope")
    if re.search(r"\blawn\s*mow", latest_reply, re.I):
        failures.append("latest customer reply still asks about lawn mowing")

    sender = f"focus-bob-{RUN}"
    conv = sender + "-conv"
    valid_saturday = future_saturday_label()
    messages = [
        "hello",
        "i'd like to have all my hedges trimmed please",
        "name is bob jones, phone num 0800 18765432 and postcode is de11sd",
        "roughly speaking it is about 20m in length and 5m high. i want it cutting down to about 4m",
        "lets do saturday at 4pm pls",
        f"lets do {valid_saturday} at 1.30pm",
    ]
    responses = [post(sender, conv, message, n + 20) for n, message in enumerate(messages, 1)]
    tr = traces(conv)

    blocked_reply = responses[4].get("reply", "")
    if re.search(r"\bsaturday\b.{0,30}\b(works?\s+(well|for)|is\s+available|confirmed|booked|scheduled)\b", blocked_reply, re.I):
        failures.append("blocked Saturday 4pm reply incorrectly implied the slot worked")
    if not re.search(r"\b(10:00|14:00|10am|2pm|weekday|alternative|instead|not available|outside|limited)\b", blocked_reply, re.I):
        failures.append("blocked Saturday 4pm reply did not explain valid alternatives")

    valid_reply = responses[5].get("reply", "")
    if re.search(r"\b(let me check|checking availability|i'?ll check)\b", valid_reply, re.I):
        failures.append("valid Saturday 1:30pm reply left customer waiting on availability check")
    if not re.search(r"\b30[- ]?(minute|minutes|min)\b", valid_reply, re.I):
        failures.append("confirmed hedge consultation reply did not advise appointment length")
    if not responses[5].get("appointment_id"):
        failures.append("valid Saturday 1:30pm appointment was not created")
    final_actions = actions_for(tr, f"focus-{RUN}-26")
    final_names = [call.get("tool_name") for call in final_actions]
    for expected in ("get_project_appointments", "check_appointment_availability", "create_appointment"):
        if expected not in final_names:
            failures.append(f"valid appointment turn did not execute {expected}")
    create_calls = [call for call in final_actions if call.get("tool_name") == "create_appointment"]
    if create_calls and create_calls[0].get("arguments", {}).get("duration_minutes") != 30:
        failures.append("hedge initial consultation did not use 30-minute business-pack duration")

    lawn_response = post(sender, conv, "ok i also want to have my lawns done at the same time", 27)
    tr = traces(conv)
    lawn_actions = actions_for(tr, f"focus-{RUN}-27")
    lawn_job_actions = [
        call for call in lawn_actions
        if call.get("tool_name") in {"add_project_job", "update_project_job"}
        and call.get("arguments", {}).get("service_key") == "lawn_mowing"
    ]
    if lawn_job_actions:
        failures.append("lawn_mowing job was created from invented lawn scope")
    lawn_reply = lawn_response.get("reply", "")
    if re.search(r"\bmedium-sized\b|\bgood condition\b", lawn_reply, re.I):
        failures.append("lawn_mowing reply invented medium/good-condition scope")
    if not re.search(r"\b(size|area|condition|how big|small|medium|large|m2|m²)\b", lawn_reply, re.I):
        failures.append("lawn_mowing reply did not ask for missing lawn scope")

    fail("Focused v4 regressions", failures)
    print(json.dumps({"ok": True, "case_count": 3, "conversation_ids": [f"focus-robert-{RUN}-conv", conv]}, indent=2))


if __name__ == "__main__":
    main()
