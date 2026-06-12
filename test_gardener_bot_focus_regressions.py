#!/usr/bin/env python3
import json
import re
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


def main():
    sender = f"focus-robert-{RUN}"
    conv = sender + "-conv"
    messages = [
        "hello",
        "i've got a lawn that is full of weeds that needs sorting",
        "name is robert johnson. 07815654345 and address is 8 Muirfield Drive, Nottingham, de45gh",
        "i don't need it mowing, i just need the weeds sorting. it's about 10m x 10m",
        "saturday morning would be best pls",
    ]
    responses = [post(sender, conv, message, n) for n, message in enumerate(messages, 1)]
    tr = traces(conv)
    failures = []

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

    fail("Robert name and explicit weeding-only context regression", failures)
    print(json.dumps({"ok": True, "case_count": 1, "conversation_id": conv}, indent=2))


if __name__ == "__main__":
    main()
